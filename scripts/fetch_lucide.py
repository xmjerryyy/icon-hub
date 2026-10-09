# -*- coding: utf-8 -*-
"""
采集 Lucide 上游数据，产出统一数据契约（统一的中间层格式）。

输入：vendor/lucide-main/            lucide 仓库 main 分支快照
输出：
  catalog/lucide/source.json         源元信息
  catalog/lucide/categories.json     分类（title_en 有值，title_zh 占位为 null）
  catalog/lucide/icons.jsonl         图标，每行一条记录
  catalog/lucide/i18n.todo.json      待翻译清单（中文）
  icons/lucide/<name>.svg            SVG 原文件（原样拷贝）

统一数据契约（新增图标源时，产出同样的文件即可让下游全部复用）：
  source.json    : key/name_en/name_zh/homepage/repo/license/version/snapshot/fetched_at/icon_count/category_count
  categories.json: [{ key, title_en, title_zh, description_en, description_zh, representative_icon, sort_order }]
  icons.jsonl    : { name, categories:[key], tags:[str], aliases:[str], use_cases:[str],
                     contributors:[str], deprecated:bool, svg_file, svg_bytes }

用法：
  python scripts/fetch_lucide.py
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "lucide-main"
OUT_CATALOG = ROOT / "catalog" / "lucide"
OUT_ICONS = ROOT / "icons" / "lucide"

SOURCE_META = {
    "key": "lucide",
    "name_en": "Lucide",
    "name_zh": None,  # 中文待补
    "homepage": "https://lucide.dev",
    "repo": "https://github.com/lucide-icons/lucide",
    "license": "ISC",
    "version": "main",
    "snapshot": "github:lucide-icons/lucide@main",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not VENDOR.exists():
        print(f"[x] 找不到上游快照：{VENDOR}", file=sys.stderr)
        print("    先执行：curl -L -o vendor/lucide-main.tar.gz "
              "https://codeload.github.com/lucide-icons/lucide/tar.gz/refs/heads/main",
              file=sys.stderr)
        return 1

    OUT_CATALOG.mkdir(parents=True, exist_ok=True)
    OUT_ICONS.mkdir(parents=True, exist_ok=True)

    # ---------- 1. 分类 ----------
    # 官网分类顺序取自 docs/.vitepress/data/categoriesData.json，缺失时退化为字典序
    order_hint: list[str] = []
    order_file = VENDOR / "docs" / ".vitepress" / "data" / "categoriesData.json"
    if order_file.exists():
        order_hint = [c["name"] for c in read_json(order_file)]

    categories = []
    for path in sorted((VENDOR / "categories").glob("*.json")):
        meta = read_json(path)
        categories.append(
            {
                "key": path.stem,
                "title_en": meta.get("title") or path.stem,
                "title_zh": None,  # 中文待补
                "description_en": meta.get("description") or "",
                "description_zh": None,  # 中文待补
                "representative_icon": meta.get("icon") or "",
            }
        )

    def sort_key(cat):
        key = cat["key"]
        return (order_hint.index(key) if key in order_hint else 10_000, key)

    categories.sort(key=sort_key)
    for i, cat in enumerate(categories, start=1):
        cat["sort_order"] = i

    write_json(OUT_CATALOG / "categories.json", categories)

    # ---------- 2. 图标 ----------
    icons = []
    for json_path in sorted((VENDOR / "icons").glob("*.json")):
        name = json_path.stem
        svg_src = VENDOR / "icons" / f"{name}.svg"
        if not svg_src.exists():
            print(f"[!] {name} 缺少 SVG，跳过")
            continue

        meta = read_json(json_path)
        svg_dst = OUT_ICONS / f"{name}.svg"
        shutil.copyfile(svg_src, svg_dst)

        icons.append(
            {
                "name": name,
                "categories": meta.get("categories") or [],
                "tags": meta.get("tags") or [],
                "aliases": [a["name"] for a in (meta.get("aliases") or [])],
                "use_cases": meta.get("use-cases") or [],
                "contributors": meta.get("contributors") or [],
                "deprecated": bool(meta.get("deprecated")),
                "svg_file": f"icons/lucide/{name}.svg",
                "svg_bytes": svg_dst.stat().st_size,
            }
        )

    lines = [json.dumps(ic, ensure_ascii=False) for ic in icons]
    (OUT_CATALOG / "icons.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------- 3. 源元信息 ----------
    category_keys = {c["key"] for c in categories}
    unknown = sorted({c for ic in icons for c in ic["categories"]} - category_keys)

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    source = dict(SOURCE_META)
    source.update(
        {
            "fetched_at": now,
            "icon_count": len(icons),
            "category_count": len(categories),
            "alias_count": sum(len(ic["aliases"]) for ic in icons),
            "tag_vocabulary_size": len({t for ic in icons for t in ic["tags"]}),
            "uncategorized_icon_count": sum(1 for ic in icons if not ic["categories"]),
        }
    )
    write_json(OUT_CATALOG / "source.json", source)

    # ---------- 4. 待翻译清单 ----------
    todo = {
        "source_key": "lucide",
        "generated_at": now,
        "categories": [
            {"key": c["key"], "title_en": c["title_en"], "title_zh": None}
            for c in categories
        ],
        "tags": [
            {"key": t, "label_en": t, "label_zh": None}
            for t in sorted({t for ic in icons for t in ic["tags"]})
        ],
    }
    write_json(OUT_CATALOG / "i18n.todo.json", todo)

    # ---------- 5. 报告 ----------
    print(f"[ok] 图标      : {len(icons)}")
    print(f"[ok] 分类      : {len(categories)}")
    print(f"[ok] 别名      : {source['alias_count']}")
    print(f"[ok] 标签词表  : {source['tag_vocabulary_size']}")
    print(f"[ok] SVG 体积  : {sum(ic['svg_bytes'] for ic in icons) / 1024:.0f} KB")
    if unknown:
        print(f"[!] 分类表里没有的归属：{unknown}")
    if source["uncategorized_icon_count"]:
        print(f"[!] 无分类图标：{source['uncategorized_icon_count']}（官网归入未分组）")
    print(f"[ok] 输出目录  : {OUT_CATALOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
