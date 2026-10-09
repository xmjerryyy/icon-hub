# -*- coding: utf-8 -*-
"""
把 catalog/ 下的统一数据契约构建成本地 SQLite 数据库。

输入：catalog/<source>/source.json | categories.json | icons.jsonl
      catalog/<source>/zh.json        （可选，中文覆盖层，见 README）
输出：data/icon-hub.db

数据库为「派生产物」，可随时删掉重建；真源是 catalog/ 里的三份文件。

用法：
  python scripts/build_db.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
DB_PATH = ROOT / "data" / "icon-hub.db"

SCHEMA_VERSION = 1

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE meta (
  key   TEXT PRIMARY KEY,
  value TEXT
);

CREATE TABLE sources (
  key             TEXT PRIMARY KEY,
  name_en         TEXT NOT NULL,
  name_zh         TEXT,
  homepage        TEXT,
  repo            TEXT,
  license         TEXT,
  version         TEXT,
  snapshot         TEXT,
  fetched_at      TEXT,
  icon_count      INTEGER,
  category_count  INTEGER,
  alias_count     INTEGER,
  tag_vocab_size  INTEGER
);

CREATE TABLE categories (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  source_key          TEXT NOT NULL REFERENCES sources(key) ON DELETE CASCADE,
  key                 TEXT NOT NULL,
  title_en            TEXT NOT NULL,
  title_zh            TEXT,
  description_en      TEXT,
  description_zh      TEXT,
  representative_icon TEXT,
  sort_order          INTEGER,
  icon_count          INTEGER,
  UNIQUE (source_key, key)
);

CREATE TABLE icons (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  source_key   TEXT NOT NULL REFERENCES sources(key) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  primary_category TEXT,
  svg_path     TEXT NOT NULL,
  svg_bytes    INTEGER,
  deprecated   INTEGER NOT NULL DEFAULT 0,
  contributors TEXT,
  use_cases    TEXT,
  UNIQUE (source_key, name)
);

CREATE TABLE tags (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  key       TEXT NOT NULL UNIQUE,
  label_en  TEXT NOT NULL,
  label_zh  TEXT
);

CREATE TABLE icon_tags (
  icon_id INTEGER NOT NULL REFERENCES icons(id) ON DELETE CASCADE,
  tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY (icon_id, tag_id)
);

CREATE TABLE icon_categories (
  icon_id     INTEGER NOT NULL REFERENCES icons(id) ON DELETE CASCADE,
  category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  is_primary  INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (icon_id, category_id)
);

CREATE TABLE aliases (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  icon_id    INTEGER NOT NULL REFERENCES icons(id) ON DELETE CASCADE,
  name       TEXT NOT NULL,
  deprecated INTEGER NOT NULL DEFAULT 0,
  UNIQUE (icon_id, name)
);

CREATE INDEX idx_icons_name       ON icons(name);
CREATE INDEX idx_icons_source     ON icons(source_key);
CREATE INDEX idx_icons_primarycat ON icons(primary_category);
CREATE INDEX idx_ic_category      ON icon_categories(category_id);
CREATE INDEX idx_it_tag           ON icon_tags(tag_id);
CREATE INDEX idx_tags_key         ON tags(key);

CREATE VIEW v_icons AS
SELECT
  i.id,
  i.source_key,
  i.name,
  i.primary_category,
  i.svg_path,
  i.svg_bytes,
  i.deprecated,
  (SELECT group_concat(c.key, ',')  FROM icon_categories x JOIN categories c ON c.id = x.category_id WHERE x.icon_id = i.id) AS categories,
  (SELECT group_concat(t.key, ',')  FROM icon_tags x JOIN tags t ON t.id = x.tag_id WHERE x.icon_id = i.id) AS tags,
  (SELECT group_concat(a.name, ',') FROM aliases a WHERE a.icon_id = i.id) AS aliases
FROM icons i;

CREATE VIEW v_stats AS
SELECT
  (SELECT count(*) FROM icons)      AS icons,
  (SELECT count(*) FROM categories) AS categories,
  (SELECT count(*) FROM tags)       AS tags,
  (SELECT count(*) FROM aliases)    AS aliases,
  (SELECT count(*) FROM sources)    AS sources;
"""


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_zh_layer(source_dir: Path) -> dict:
    zh_file = source_dir / "zh.json"
    if not zh_file.exists():
        return {"source_name_zh": None, "categories": {}, "tags": {}}
    data = read_json(zh_file)
    return {
        "source_name_zh": data.get("source_name_zh"),
        "categories": data.get("categories") or {},
        "tags": data.get("tags") or {},
    }


def build() -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(DDL)

    source_dirs = sorted(p for p in CATALOG.iterdir() if (p / "source.json").exists())
    if not source_dirs:
        print("[x] catalog/ 下没有任何图标源", file=sys.stderr)
        return 1

    total_icons = total_tags = 0
    tag_ids: dict[str, int] = {}
    zh_conflicts: list[tuple[str, str, str]] = []

    def tag_id(raw: str, zh_tags: dict) -> int:
        """标签表是**跨源全局唯一**的：同名标签自动复用，两源共用同一条中文译文。

        这是刻意设计 —— Lucide 已翻译的 4095 个标签，Tabler 里同名的部分直接命中，
        不必重复翻译。先建者（Lucide）的译文优先，若后来的源给出不同译文则记录为冲突。
        """
        if raw in tag_ids:
            return tag_ids[raw]
        row = conn.execute("SELECT id, label_zh FROM tags WHERE key = ?", (raw,)).fetchone()
        if row:
            tid, old_zh = row[0], row[1]
            new_zh = zh_tags.get(raw)
            if new_zh and old_zh and new_zh != old_zh:
                zh_conflicts.append((raw, old_zh, new_zh))
            tag_ids[raw] = tid
            return tid
        cur = conn.execute(
            "INSERT INTO tags (key, label_en, label_zh) VALUES (?,?,?)",
            (raw, raw, zh_tags.get(raw)),
        )
        tag_ids[raw] = cur.lastrowid
        return cur.lastrowid

    for sdir in source_dirs:
        src = read_json(sdir / "source.json")
        zh = load_zh_layer(sdir)

        conn.execute(
            """INSERT INTO sources (key, name_en, name_zh, homepage, repo, license,
                                    version, snapshot, fetched_at, icon_count,
                                    category_count, alias_count, tag_vocab_size)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                src["key"], src["name_en"], zh["source_name_zh"] or src.get("name_zh"),
                src.get("homepage"), src.get("repo"), src.get("license"),
                src.get("version"), src.get("snapshot"), src.get("fetched_at"),
                src.get("icon_count"), src.get("category_count"),
                src.get("alias_count"), src.get("tag_vocabulary_size"),
            ),
        )

        # 分类
        cat_ids: dict[str, int] = {}
        for cat in read_json(sdir / "categories.json"):
            cur = conn.execute(
                """INSERT INTO categories (source_key, key, title_en, title_zh,
                                           description_en, description_zh,
                                           representative_icon, sort_order, icon_count)
                   VALUES (?,?,?,?,?,?,?,?,0)""",
                (
                    src["key"], cat["key"], cat["title_en"],
                    zh["categories"].get(cat["key"]) or cat.get("title_zh"),
                    cat.get("description_en"),
                    zh["categories"].get(cat["key"] + ".description") or cat.get("description_zh"),
                    cat.get("representative_icon"), cat.get("sort_order"),
                ),
            )
            cat_ids[cat["key"]] = cur.lastrowid

        # 标签词表：tag_id() 定义在源循环之外（跨源共享同一张表）

        # 图标
        lines = (sdir / "icons.jsonl").read_text(encoding="utf-8").splitlines()
        for line in lines:
            if not line.strip():
                continue
            ic = json.loads(line)
            cats = [c for c in ic.get("categories", []) if c in cat_ids]
            cur = conn.execute(
                """INSERT INTO icons (source_key, name, primary_category, svg_path,
                                      svg_bytes, deprecated, contributors, use_cases)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    src["key"], ic["name"], cats[0] if cats else None,
                    ic["svg_file"], ic.get("svg_bytes"), int(bool(ic.get("deprecated"))),
                    json.dumps(ic.get("contributors", []), ensure_ascii=False),
                    json.dumps(ic.get("use_cases", []), ensure_ascii=False),
                ),
            )
            icon_id = cur.lastrowid
            total_icons += 1

            for idx, ckey in enumerate(cats):
                conn.execute(
                    "INSERT INTO icon_categories (icon_id, category_id, is_primary) VALUES (?,?,?)",
                    (icon_id, cat_ids[ckey], 1 if idx == 0 else 0),
                )
                conn.execute(
                    "UPDATE categories SET icon_count = icon_count + 1 WHERE id = ?",
                    (cat_ids[ckey],),
                )

            for raw in dict.fromkeys(ic.get("tags", [])):
                tid = tag_id(raw, zh["tags"])
                total_tags += 1
                conn.execute(
                    "INSERT OR IGNORE INTO icon_tags (icon_id, tag_id) VALUES (?,?)",
                    (icon_id, tid),
                )

            for alias in ic.get("aliases", []):
                conn.execute(
                    "INSERT OR IGNORE INTO aliases (icon_id, name, deprecated) VALUES (?,?,0)",
                    (icon_id, alias),
                )

    # 全文检索（FTS5 不可用时静默跳过）
    try:
        conn.executescript(
            """
            CREATE VIRTUAL TABLE icons_fts USING fts5(
              name, aliases, tags, categories,
              tokenize = 'unicode61 remove_diacritics 2'
            );
            INSERT INTO icons_fts (name, aliases, tags, categories)
            SELECT name, ifnull(aliases,''), ifnull(tags,''), ifnull(categories,'') FROM v_icons;
            """
        )
        fts = "已启用"
    except sqlite3.OperationalError as exc:
        fts = f"未启用（{exc}）"

    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?,?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?,?)",
        ("built_at", datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")),
    )
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?,?)",
        ("language_default", "en"),
    )
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?,?)",
        ("language_supported", "en,zh"),
    )
    conn.commit()

    keys = ["icons", "categories", "tags", "aliases", "sources"]
    stats = dict(zip(keys, conn.execute("SELECT * FROM v_stats").fetchone()))
    top = conn.execute(
        """SELECT c.title_en, c.icon_count FROM categories c
           ORDER BY c.icon_count DESC LIMIT 5"""
    ).fetchall()
    conn.close()

    print(f"[ok] 数据库      : {DB_PATH}")
    print(f"[ok] 源 / 图标   : {stats['sources']} / {stats['icons']}")
    print(f"[ok] 分类 / 标签 : {stats['categories']} / {stats['tags']}")
    print(f"[ok] 别名        : {stats['aliases']}")
    print(f"[ok] 图标-标签关系: {total_tags}")
    print(f"[ok] 全文检索    : {fts}")
    if zh_conflicts:
        print(f"[!] 跨源译文冲突  : {len(zh_conflicts)} 条（保留先建者）→ {zh_conflicts[:3]}")
    print("[ok] 图标最多的分类: " + "、".join(f"{t}({n})" for t, n in top))
    print(f"[ok] 库文件大小  : {DB_PATH.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
