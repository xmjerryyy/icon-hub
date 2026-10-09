# -*- coding: utf-8 -*-
"""
生成中文翻译工作清单（分块、带序号），支持任意图标源。

用法：
  python scripts/make_zh_worklist.py --source lucide                 # 分类 + 标签
  python scripts/make_zh_worklist.py --source tabler --only tags      # 只做标签
  python scripts/make_zh_worklist.py --source tabler --include-translated

默认会跳过「数据库里已有中文」的标签 —— **标签表是跨源共享的**，
别的源译过同一个英文标签，这里就不必重复列出来。加 --include-translated 可强制全量生成。

输出（catalog/<源>/_zh_work/）：
  categories.in.txt / categories-desc.in.txt   序号 \t key \t 英文
  tags-NN.in.txt                               序号 \t 英文标签

译文回填：新建同名 *-NN.out.txt，每行「序号 \t 中文」，由 apply_zh.py 校验并合并。
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "icon-hub.db"
DEFAULT_CHUNK = 500


def translated_tag_keys() -> set[str]:
    """数据库里已经有中文译文的标签（跨源共享，可直接跳过）"""
    if not DB.exists():
        return set()
    conn = sqlite3.connect(DB)
    try:
        rows = conn.execute(
            "SELECT key FROM tags WHERE label_zh IS NOT NULL AND label_zh <> ''"
        )
        return {r[0] for r in rows}
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="lucide", help="源 key，对应 catalog/<source>/")
    ap.add_argument("--only", choices=["all", "tags", "categories"], default="all")
    ap.add_argument("--include-translated", action="store_true",
                    help="连已有中文的标签一起生成（默认跳过）")
    ap.add_argument("--chunk", type=int, default=DEFAULT_CHUNK, help="每块条数")
    args = ap.parse_args()

    src = ROOT / "catalog" / args.source
    if not (src / "i18n.todo.json").exists():
        print(f"[x] 找不到 {src / 'i18n.todo.json'}", file=sys.stderr)
        return 1
    out = src / "_zh_work"
    out.mkdir(parents=True, exist_ok=True)

    if args.only in ("all", "categories"):
        cats = json.loads((src / "categories.json").read_text(encoding="utf-8"))
        titles = [f"{i:02d}\t{c['key']}\t{c['title_en']}" for i, c in enumerate(cats, 1)]
        descs = [f"{i:02d}\t{c['key']}\t{c['description_en']}" for i, c in enumerate(cats, 1)]
        (out / "categories.in.txt").write_text(
            "\n".join(titles) + "\n", encoding="utf-8", newline="\n")
        (out / "categories-desc.in.txt").write_text(
            "\n".join(descs) + "\n", encoding="utf-8", newline="\n")
        print(f"[ok] 分类 {len(cats)} 条 -> categories.in.txt / categories-desc.in.txt")

    if args.only in ("all", "tags"):
        todo = json.loads((src / "i18n.todo.json").read_text(encoding="utf-8"))
        tags = [t["key"] for t in todo["tags"]]
        total = len(tags)
        if not args.include_translated:
            done = translated_tag_keys()
            tags = [t for t in tags if t not in done]
            if total - len(tags):
                print(f"[ok] 跳过 {total - len(tags)} 个已有中文的标签（跨源共享）")

        n = (len(tags) + args.chunk - 1) // args.chunk
        for ci in range(n):
            part = tags[ci * args.chunk:(ci + 1) * args.chunk]
            body = "\n".join(
                f"{ci * args.chunk + j + 1:04d}\t{t}" for j, t in enumerate(part)
            )
            (out / f"tags-{ci + 1:02d}.in.txt").write_text(
                body + "\n", encoding="utf-8", newline="\n")
        print(f"[ok] 标签 {len(tags)} 条 -> {n} 个分块（每块 {args.chunk}）")

    print(f"[ok] 工作目录 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
