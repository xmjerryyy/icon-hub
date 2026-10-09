# -*- coding: utf-8 -*-
"""
采集 Tabler Icons 上游数据，产出与 Lucide 相同的统一数据契约。

输入：vendor/tabler-icons-main/     tabler-icons 仓库 main 分支快照
输出：
  catalog/tabler/source.json
  catalog/tabler/categories.json
  catalog/tabler/icons.jsonl
  catalog/tabler/i18n.todo.json
  icons/tabler/outline/*.svg
  icons/tabler/filled/*.svg

与 Lucide 的三处差异（本脚本已处理）：
  1. Tabler 把 category / tags / version / unicode 写在 SVG 文件开头的
     `<!-- ... -->` front-matter 注释里，不是独立 .json
  2. Tabler 的分类是**单数** `category`（一个图标只属一个分类）
  3. filled 那一套（1054 个）**完全没有 category 和 tags**，且与 outline 100% 同名 →
     处理方式：名字加 `-filled` 后缀（与 Tabler 官方 SDK 的 IconXxxFilled 命名一致），
     category / tags 从同名 outline 图标继承，并额外打上 `filled` 标签

用法：
  python scripts/fetch_tabler.py
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "tabler-icons-main"
OUT_CATALOG = ROOT / "catalog" / "tabler"
OUT_ICONS = ROOT / "icons" / "tabler"

SOURCE_META = {
    "key": "tabler",
    "name_en": "Tabler Icons",
    "name_zh": None,  # 中文待补
    "homepage": "https://tabler.io/icons",
    "repo": "https://github.com/tabler/tabler-icons",
    "license": "MIT",
    "snapshot": "github:tabler/tabler-icons@main",
}

FRONT_MATTER = re.compile(r"^<!--(.*?)-->", re.S)
SVG_BODY = re.compile(r"<svg.*</svg>", re.S)


def read_front_matter(path: Path) -> tuple[dict[str, str], str]:
    """拆出 front-matter 注释与纯 SVG 正文"""
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    m = FRONT_MATTER.match(text.lstrip())
    if m:
        for line in m.group(1).splitlines():
            key, sep, value = line.partition(":")
            if sep:
                meta[key.strip()] = value.strip()
    body = SVG_BODY.search(text)
    return meta, (body.group(0) if body else text)


def parse_tags(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if raw.startswith("["):
        raw = raw[1:]
    if raw.endswith("]"):
        raw = raw[:-1]
    return [t.strip() for t in raw.split(",") if t.strip()]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main() -> int:
    if not VENDOR.exists():
        print(f"[x] 找不到上游快照：{VENDOR}", file=sys.stderr)
        print("    curl -L -o vendor/tabler-main.tar.gz \\\n"
              "      https://codeload.github.com/tabler/tabler-icons/tar.gz/refs/heads/main",
              file=sys.stderr)
        return 1

    OUT_CATALOG.mkdir(parents=True, exist_ok=True)
    for style in ("outline", "filled"):
        (OUT_ICONS / style).mkdir(parents=True, exist_ok=True)

    # ---------- 1. 解析 outline（元数据齐全）----------
    outline_meta: dict[str, dict] = {}
    for path in sorted((VENDOR / "icons" / "outline").glob("*.svg")):
        meta, body = read_front_matter(path)
        category = (meta.get("category") or "").strip().strip('"')
        outline_meta[path.stem] = {
            "category": category,
            "tags": parse_tags(meta.get("tags", "")),
            "body": body,
        }

    # ---------- 2. 分类（按字母序）----------
    cat_titles = sorted({m["category"] for m in outline_meta.values() if m["category"]})
    categories = []
    for i, title in enumerate(cat_titles, start=1):
        categories.append({
            "key": slugify(title),
            "title_en": title,
            "title_zh": None,
            "description_en": "",   # Tabler 上游没有分类描述
            "description_zh": None,
            "representative_icon": "",
            "sort_order": i,
        })
    cat_key_of_title = {c["title_en"]: c["key"] for c in categories}
    write_json = lambda p, d: p.write_text(  # noqa: E731
        json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    write_json(OUT_CATALOG / "categories.json", categories)

    # ---------- 3. 别名（aliases.json: {style: {旧名: 新名}}）----------
    aliases_raw = json.loads((VENDOR / "aliases.json").read_text(encoding="utf-8"))
    alias_of: dict[tuple[str, str], list[str]] = {}
    for style, mapping in aliases_raw.items():
        for old, new in (mapping or {}).items():
            alias_of.setdefault((style, new), []).append(old)

    # ---------- 4. 图标 ----------
    icons = []
    used_names: set[str] = set()
    skipped: list[str] = []

    def add_icon(name: str, style: str, category: str, tags: list[str],
                 body: str, src: Path) -> None:
        if name in used_names:
            skipped.append(f"{style}/{src.name}（重名 {name}）")
            return
        used_names.add(name)
        dst = OUT_ICONS / style / f"{src.stem}.svg"
        dst.write_text(body.strip() + "\n", encoding="utf-8", newline="\n")
        icons.append({
            "name": name,
            "categories": [cat_key_of_title[category]] if category in cat_key_of_title else [],
            "tags": tags,
            "aliases": sorted(alias_of.get((style, src.stem), [])),
            "use_cases": [],
            "contributors": [],
            "deprecated": False,
            "svg_file": f"icons/tabler/{style}/{src.stem}.svg",
            "svg_bytes": dst.stat().st_size,
        })

    # outline 先入，保证 filled 撞名时以 outline 为准
    for name, m in outline_meta.items():
        add_icon(name, "outline", m["category"], m["tags"],
                 m["body"], VENDOR / "icons" / "outline" / f"{name}.svg")

    filled_inherited = 0
    for path in sorted((VENDOR / "icons" / "filled").glob("*.svg")):
        source = outline_meta.get(path.stem)
        if source:
            filled_inherited += 1
            category, tags = source["category"], list(source["tags"])
        else:
            category, tags = "", []
        tags = list(dict.fromkeys(tags + ["filled"]))
        _, body = read_front_matter(path)
        add_icon(f"{path.stem}-filled", "filled", category, tags, body, path)

    lines = [json.dumps(ic, ensure_ascii=False) for ic in icons]
    (OUT_CATALOG / "icons.jsonl").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )

    # ---------- 5. 源元信息 ----------
    version = json.loads((VENDOR / "package.json").read_text(encoding="utf-8")).get("version", "")
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    source = dict(SOURCE_META)
    source.update({
        "version": version,
        "fetched_at": now,
        "icon_count": len(icons),
        "category_count": len(categories),
        "alias_count": sum(len(ic["aliases"]) for ic in icons),
        "tag_vocabulary_size": len({t for ic in icons for t in ic["tags"]}),
        "uncategorized_icon_count": sum(1 for ic in icons if not ic["categories"]),
        "notes": (
            "outline 5184 个元数据完整；filled 1054 个上游无 category/tags，"
            "已按同名 outline 继承并加 `-filled` 后缀与 `filled` 标签"
        ),
    })
    write_json(OUT_CATALOG / "source.json", source)

    # ---------- 6. 待翻译清单 ----------
    write_json(OUT_CATALOG / "i18n.todo.json", {
        "source_key": "tabler",
        "generated_at": now,
        "categories": [{"key": c["key"], "title_en": c["title_en"], "title_zh": None}
                       for c in categories],
        "tags": [{"key": t, "label_en": t, "label_zh": None}
                 for t in sorted({t for ic in icons for t in ic["tags"]})],
    })

    # ---------- 7. 报告 ----------
    print(f"[ok] 图标        : {len(icons)}  （outline 5184 + filled 1054）")
    print(f"[ok] 分类        : {len(categories)}")
    print(f"[ok] 别名        : {source['alias_count']}")
    print(f"[ok] 标签词表    : {source['tag_vocabulary_size']}")
    print(f"[ok] filled 继承 : {filled_inherited} / 1054")
    print(f"[ok] SVG 体积    : {sum(ic['svg_bytes'] for ic in icons) / 1024:.0f} KB")
    if skipped:
        print(f"[!] 跳过重名     : {len(skipped)} -> {skipped[:5]}")
    if source["uncategorized_icon_count"]:
        print(f"[!] 无分类图标   : {source['uncategorized_icon_count']}")
    print(f"[ok] 输出目录    : {OUT_CATALOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
