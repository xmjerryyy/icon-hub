#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icon Hub 查询接口 —— 给 AI 助手用的图标检索工具。

数据来自本仓库的 SQLite（含全部 8108 个图标的 SVG），**完全离线**，只依赖 Python 标准库。

常用法：
  python query.py "关闭"                        # 中英文关键词搜索
  python query.py "delete" --source tabler      # 限定数据源
  python query.py --category brand --limit 50   # 按分类浏览
  python query.py --style filled "home"         # 只要实心（Tabler filled）
  python query.py "关闭" --svg                  # 结果里附带 SVG 源码
  python query.py --get x --source lucide --svg # 精确取单个图标的 SVG
  python query.py --list-categories             # 列出全部分类
  python query.py --list-sources --stats        # 数据概览

输出默认 JSON（便于程序处理），加 --format text 输出人类可读的文本。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "icon-hub.db"

LIKE_ESCAPE = "\\"


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        sys.exit(
            f"[x] 数据文件不存在：{DB_PATH}\n"
            f"    在项目根目录执行：python skill/scripts/install.py"
        )
    # 只读打开，避免误写
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def like(s: str) -> str:
    """转义 LIKE 通配符（用户输入里的 % 和 _ 不该被当通配符）"""
    return (
        s.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", LIKE_ESCAPE + "%")
        .replace("_", LIKE_ESCAPE + "_")
    )


# --------------------------------------------------------------------------- 检索

def match_ids(conn: sqlite3.Connection, word: str) -> set[int]:
    """一个关键词命中的全部图标 id —— 名称 / 别名 / 标签(中英) / 分类(中英) 都参与"""
    p = f"%{like(word)}%"
    esc = f"ESCAPE '{LIKE_ESCAPE}'"
    ids: set[int] = set()
    ids |= {r[0] for r in conn.execute(
        f"SELECT id FROM icons WHERE name LIKE ? {esc}", (p,))}
    ids |= {r[0] for r in conn.execute(
        f"SELECT icon_id FROM aliases WHERE name LIKE ? {esc}", (p,))}
    ids |= {r[0] for r in conn.execute(
        f"SELECT DISTINCT it.icon_id FROM icon_tags it JOIN tags t ON t.id = it.tag_id "
        f"WHERE t.label_en LIKE ? {esc} OR t.label_zh LIKE ? {esc}", (p, p))}
    ids |= {r[0] for r in conn.execute(
        f"SELECT DISTINCT ic.icon_id FROM icon_categories ic "
        f"JOIN categories c ON c.id = ic.category_id "
        f"WHERE c.title_en LIKE ? {esc} OR c.title_zh LIKE ? {esc}", (p, p))}
    return ids


def icon_detail(conn: sqlite3.Connection, icon_id: int) -> dict:
    """组装一个图标的完整信息"""
    row = conn.execute(
        "SELECT i.id, i.name, i.source_key, i.svg_path, i.svg_bytes, i.deprecated, "
        "       s.name_en AS source_name_en, s.name_zh AS source_name_zh "
        "FROM icons i JOIN sources s ON s.key = i.source_key WHERE i.id = ?",
        (icon_id,),
    ).fetchone()
    if row is None:
        return {}

    cats = conn.execute(
        "SELECT c.key, c.title_en, c.title_zh FROM icon_categories ic "
        "JOIN categories c ON c.id = ic.category_id WHERE ic.icon_id = ? "
        "ORDER BY c.sort_order",
        (icon_id,),
    ).fetchall()
    tags = conn.execute(
        "SELECT t.key, t.label_en, t.label_zh FROM icon_tags it "
        "JOIN tags t ON t.id = it.tag_id WHERE it.icon_id = ? ORDER BY t.key",
        (icon_id,),
    ).fetchall()
    aliases = [r[0] for r in conn.execute(
        "SELECT name FROM aliases WHERE icon_id = ? ORDER BY name", (icon_id,))]

    return {
        "name": row["name"],
        "source": row["source_key"],
        "source_name": row["source_name_zh"] or row["source_name_en"],
        "categories": [{"key": c["key"], "title": c["title_zh"] or c["title_en"]} for c in cats],
        "tags": [{"key": t["key"], "label": t["label_zh"] or t["label_en"]} for t in tags],
        "aliases": aliases,
        "svg_file": row["svg_path"],
        "svg_bytes": row["svg_bytes"],
        "deprecated": bool(row["deprecated"]),
    }


def score(detail: dict, words: list[str]) -> int:
    """相关度打分：名称/别名精确 > 标签精确 > 标签包含 > 分类。

    标签分两档是刻意的 —— 「关闭」这类词会命中「关闭字幕」「关闭状态」等复合标签，
    如果不把精确匹配拉开差距，真正想要的图标会被淹没。
    """
    name = detail["name"].lower()
    total = 0
    for w in words:
        wl = w.lower()
        if name == wl:
            total += 100
        elif name.startswith(wl):
            total += 60
        elif wl in name:
            total += 40

        if any(a.lower() == wl for a in detail["aliases"]):
            total += 50
        elif any(wl in a.lower() for a in detail["aliases"]):
            total += 30

        if any(t["key"] == wl or t["label"] == w for t in detail["tags"]):
            total += 45
        elif any(wl in t["key"] or wl in t["label"].lower() for t in detail["tags"]):
            total += 12

        if any(c["key"] == wl or c["title"] == w for c in detail["categories"]):
            total += 20
        elif any(wl in c["key"] or wl in c["title"].lower() for c in detail["categories"]):
            total += 8
    return total


def browse(conn, source=None, category=None, style=None, limit=20):
    """没有关键词时：按 源 / 分类 / 风格 列出图标，按名称排序"""
    where, args = ["1=1"], []
    if source:
        where.append("i.source_key = ?")
        args.append(source)
    if category:
        where.append("c.key = ?")
        args.append(category)
    if style == "filled":
        where.append("i.name LIKE '%-filled'")
    elif style == "outline":
        where.append("i.name NOT LIKE '%-filled'")
    cond = " AND ".join(where)
    join = ("FROM icons i LEFT JOIN icon_categories ic ON ic.icon_id = i.id "
            "LEFT JOIN categories c ON c.id = ic.category_id")

    total = conn.execute(f"SELECT count(DISTINCT i.id) {join} WHERE {cond}", args).fetchone()[0]
    rows = conn.execute(
        f"SELECT DISTINCT i.id {join} WHERE {cond} ORDER BY i.name LIMIT ?",
        args + [limit]).fetchall()
    return [icon_detail(conn, r[0]) for r in rows], total


def search(conn, words, source=None, category=None, style=None, limit=20):
    """有关键词：多词取交集，按相关度排序。没有关键词：按筛选条件列出。"""
    if not words:
        return browse(conn, source, category, style, limit)

    id_sets = [match_ids(conn, w) for w in words]
    ids = set.intersection(*id_sets) if id_sets else set()

    results = []
    for icon_id in ids:
        d = icon_detail(conn, icon_id)
        if not d:
            continue
        if source and d["source"] != source:
            continue
        if category and not any(c["key"] == category for c in d["categories"]):
            continue
        if style == "filled" and not d["name"].endswith("-filled"):
            continue
        if style == "outline" and d["name"].endswith("-filled"):
            continue
        d["score"] = score(d, words)
        results.append(d)

    results.sort(key=lambda d: (-d["score"], len(d["name"]), d["name"]))
    return results[:limit], len(results)


def get_icon(conn, name, source=None):
    """精确按名称取单个图标（大小写不敏感）"""
    if ":" in name and not source:
        source, name = name.split(":", 1)
    sql = "SELECT id FROM icons WHERE lower(name) = lower(?)"
    args = [name]
    if source:
        sql += " AND source_key = ?"
        args.append(source)
    rows = conn.execute(sql, args).fetchall()
    if not rows:
        return None
    return icon_detail(conn, rows[0]["id"])


# --------------------------------------------------------------------------- 其它查询

def list_categories(conn, source=None):
    sql = ("SELECT c.source_key, c.key, c.title_en, c.title_zh, c.icon_count "
           "FROM categories c")
    args = []
    if source:
        sql += " WHERE c.source_key = ?"
        args.append(source)
    sql += " ORDER BY c.source_key, c.sort_order"
    return [
        {"source": r["source_key"], "key": r["key"],
         "title_en": r["title_en"], "title_zh": r["title_zh"],
         "count": r["icon_count"]}
        for r in conn.execute(sql, args)
    ]


def list_sources(conn):
    return [
        {"key": r["key"], "name_en": r["name_en"], "name_zh": r["name_zh"],
         "icons": r["icon_count"], "categories": r["category_count"],
         "license": r["license"], "homepage": r["homepage"]}
        for r in conn.execute(
            "SELECT key, name_en, name_zh, icon_count, category_count, license, homepage "
            "FROM sources ORDER BY key")
    ]


def stats(conn):
    one = lambda q: conn.execute(q).fetchone()[0]  # noqa: E731
    return {
        "sources": one("SELECT count(*) FROM sources"),
        "icons": one("SELECT count(*) FROM icons"),
        "categories": one("SELECT count(*) FROM categories"),
        "tags": one("SELECT count(*) FROM tags"),
        "aliases": one("SELECT count(*) FROM aliases"),
        "tags_translated": one(
            "SELECT count(*) FROM tags WHERE label_zh IS NOT NULL AND label_zh <> ''"),
        "built_at": one("SELECT value FROM meta WHERE key = 'built_at'")
        if conn.execute("SELECT count(*) FROM meta WHERE key='built_at'").fetchone()[0] else None,
    }


def read_svg(conn, detail):
    """取 SVG 源码：优先用安装时内联进数据库的副本，退回读仓库里的 .svg 文件"""
    if not detail:
        return None
    try:
        row = conn.execute(
            "SELECT svg FROM icons WHERE name = ? AND source_key = ?",
            (detail["name"], detail["source"]),
        ).fetchone()
        if row and row[0]:
            return row[0]
    except sqlite3.OperationalError:
        pass  # 旧数据没有内联列，走文件回退
    # 回退：仓库根/icons/<源>/xxx.svg（仅在项目目录内有效）
    path = Path(__file__).resolve().parents[2] / detail["svg_file"]
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


# --------------------------------------------------------------------------- 输出

def to_text(payload, mode):
    lines = []
    if mode == "search":
        label = f"查询「{payload['query']}」" if payload["query"] else "按条件浏览"
        lines.append(f"{label}：命中 {payload['total']} 个，"
                     f"返回 {len(payload['results'])} 个")
        for i, r in enumerate(payload["results"], 1):
            cats = " / ".join(c["title"] for c in r["categories"]) or "—"
            tags = ", ".join(t["label"] for t in r["tags"][:8]) or "—"
            lines.append(f"{i}. {r['name']}  [{r['source_name']}]")
            lines.append(f"   分类: {cats}")
            lines.append(f"   标签: {tags}")
            if r.get("svg"):
                lines.append(f"   SVG: {r['svg']}")
    elif mode == "icon":
        r = payload["icon"]
        lines.append(f"{r['name']}  [{r['source_name']}]")
        lines.append(f"文件: {r['svg_file']}  ({r['svg_bytes']} 字节)")
        lines.append(f"分类: " + (" / ".join(c["title"] for c in r["categories"]) or "—"))
        lines.append(f"标签: " + (", ".join(t["label"] for t in r["tags"]) or "—"))
        if r["aliases"]:
            lines.append(f"别名: {', '.join(r['aliases'])}")
        if r.get("svg"):
            lines.append("")
            lines.append(r["svg"])
    elif mode == "categories":
        cur = None
        for c in payload["categories"]:
            if c["source"] != cur:
                cur = c["source"]
                lines.append(f"\n[{cur}]")
            lines.append(f"  {c['key']:<22} {c['title_zh'] or ''}  {c['title_en']}  ({c['count']})")
    elif mode == "sources":
        for s in payload["sources"]:
            lines.append(f"{s['key']}: {s['name_zh'] or s['name_en']} — "
                         f"{s['icons']} 图标 / {s['categories']} 分类 / {s['license']}")
    elif mode == "stats":
        for k, v in payload["stats"].items():
            lines.append(f"{k}: {v}")
    return "\n".join(lines)


def emit(payload, args, mode):
    if args.format == "text":
        print(to_text(payload, mode))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Icon Hub 图标检索（离线，中英双语，8108 个图标）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("query", nargs="*", help="关键词，中英文均可；多个词取交集")
    ap.add_argument("--source", help="限定数据源：lucide / tabler")
    ap.add_argument("--category", help="限定分类 key（见 --list-categories）")
    ap.add_argument("--style", choices=["outline", "filled"],
                    help="按风格筛选（filled 仅 Tabler 有）")
    ap.add_argument("--limit", type=int, default=20, help="最多返回多少条（默认 20）")
    ap.add_argument("--svg", action="store_true", help="结果中附带 SVG 源码")
    ap.add_argument("--get", metavar="NAME",
                    help="按名称精确取一个图标（可写 tabler:brand-github）")
    ap.add_argument("--list-categories", action="store_true", help="列出全部分类")
    ap.add_argument("--list-sources", action="store_true", help="列出数据源")
    ap.add_argument("--stats", action="store_true", help="数据概览")
    ap.add_argument("--format", choices=["json", "text"], default="json")
    args = ap.parse_args()

    conn = connect()

    if args.stats:
        emit({"stats": stats(conn)}, args, "stats")
    elif args.list_sources:
        emit({"sources": list_sources(conn)}, args, "sources")
    elif args.list_categories:
        emit({"categories": list_categories(conn, args.source)}, args, "categories")
    elif args.get:
        d = get_icon(conn, args.get, args.source)
        if not d:
            print(json.dumps({"error": "not found", "name": args.get}, ensure_ascii=False))
            return 1
        if args.svg:
            d["svg"] = read_svg(conn, d)
        emit({"icon": d}, args, "icon")
    elif args.query or args.category or args.source or args.style:
        words = [w for w in args.query if w.strip()]
        results, total = search(conn, words, args.source, args.category,
                                args.style, args.limit)
        if args.svg:
            for r in results:
                r["svg"] = read_svg(conn, r)
        emit({"query": " ".join(words), "total": total,
              "returned": len(results), "results": results}, args, "search")
    else:
        ap.print_help()
        return 2

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
