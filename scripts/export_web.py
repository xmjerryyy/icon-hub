# -*- coding: utf-8 -*-
"""
从 SQLite 导出前端数据文件（本地浏览界面用）。

输入：data/icon-hub.db + icons/**/*.svg
输出：
  web/data/catalog.js     window.ICON_HUB = {...}   给界面用
  web/data/catalog.json   同内容的纯 JSON           给外部程序用

用法：
  python scripts/export_web.py
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "icon-hub.db"
OUT_DIR = ROOT / "web" / "data"

WS_RE = re.compile(r">\s+<")


def squash(svg: str) -> str:
    """去掉标签之间的换行缩进，体积更小，渲染结果不变。"""
    svg = WS_RE.sub("><", svg.strip())
    return re.sub(r"\s{2,}", " ", svg)


def bilingual(en, zh):
    return {"en": en, "zh": zh} if zh else {"en": en}


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    meta = {r["key"]: r["value"] for r in conn.execute("SELECT * FROM meta")}

    sources = [
        {
            "key": r["key"],
            "name": bilingual(r["name_en"], r["name_zh"]),
            "homepage": r["homepage"],
            "repo": r["repo"],
            "license": r["license"],
            "version": r["version"],
            "iconCount": r["icon_count"],
            "categoryCount": r["category_count"],
        }
        for r in conn.execute("SELECT * FROM sources ORDER BY key")
    ]

    categories = [
        {
            "key": r["key"],
            "source": r["source_key"],
            "title": bilingual(r["title_en"], r["title_zh"]),
            "description": bilingual(r["description_en"], r["description_zh"]),
            "icon": r["representative_icon"],
            "order": r["sort_order"],
            "count": r["icon_count"],
        }
        for r in conn.execute("SELECT * FROM categories ORDER BY source_key, sort_order")
    ]

    tags = [
        {"key": r["key"], "label": bilingual(r["label_en"], r["label_zh"])}
        for r in conn.execute("SELECT * FROM tags ORDER BY key")
    ]

    icons = []
    for r in conn.execute("SELECT * FROM v_icons ORDER BY source_key, name"):
        svg_path = ROOT / r["svg_path"]
        if not svg_path.exists():
            print(f"[!] 缺少 SVG：{r['svg_path']}")
            continue
        icons.append(
            {
                "name": r["name"],
                "source": r["source_key"],
                "primaryCategory": r["primary_category"],
                "categories": (r["categories"] or "").split(",") if r["categories"] else [],
                "tags": (r["tags"] or "").split(",") if r["tags"] else [],
                "aliases": (r["aliases"] or "").split(",") if r["aliases"] else [],
                "deprecated": bool(r["deprecated"]),
                "bytes": r["svg_bytes"],
                "svg": squash(svg_path.read_text(encoding="utf-8")),
            }
        )

    payload = {
        "generatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "schemaVersion": int(meta.get("schema_version", 1)),
        "defaultLanguage": meta.get("language_default", "en"),
        "languages": [x for x in (meta.get("language_supported") or "en").split(",") if x],
        "stats": {
            "icons": len(icons),
            "categories": len(categories),
            "tags": len(tags),
            "sources": len(sources),
        },
        "sources": sources,
        "categories": categories,
        "tags": tags,
        "icons": icons,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    (OUT_DIR / "catalog.json").write_text(body, encoding="utf-8", newline="\n")
    (OUT_DIR / "catalog.js").write_text(
        "window.ICON_HUB = " + body + ";\n", encoding="utf-8", newline="\n"
    )

    size_kb = (OUT_DIR / "catalog.js").stat().st_size / 1024
    print(f"[ok] 图标 {len(icons)} / 分类 {len(categories)} / 标签 {len(tags)} / 源 {len(sources)}")
    print(f"[ok] 输出 {OUT_DIR / 'catalog.js'}（{size_kb:.0f} KB）")
    print(f"[ok] 输出 {OUT_DIR / 'catalog.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
