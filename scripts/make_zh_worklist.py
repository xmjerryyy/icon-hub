# -*- coding: utf-8 -*-
"""
生成中文翻译工作清单（分块、带序号，便于逐块翻译后回填）。

输入：catalog/lucide/i18n.todo.json（42 分类 + 4095 标签）
输出：catalog/lucide/_zh_work/
    categories.in.txt      序号\tkey\t英文标题
    categories-desc.in.txt 序号\tkey\t英文描述
    tags-NN.in.txt         序号\t英文标签

译文回填：新建同名 *-NN.out.txt，每行「序号\t中文」，由 apply_zh.py 校验并合并。
用法：python scripts/make_zh_worklist.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "catalog" / "lucide"
OUT = SRC / "_zh_work"
CHUNK = 500


def main() -> int:
    todo = json.loads((SRC / "i18n.todo.json").read_text(encoding="utf-8"))
    cats = json.loads((SRC / "categories.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    lines, desc_lines = [], []
    for i, c in enumerate(cats, start=1):
        lines.append(f"{i:02d}\t{c['key']}\t{c['title_en']}")
        desc_lines.append(f"{i:02d}\t{c['key']}\t{c['description_en']}")
    (OUT / "categories.in.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "categories-desc.in.txt").write_text("\n".join(desc_lines) + "\n", encoding="utf-8")

    tags = [t["key"] for t in todo["tags"]]
    n_chunks = (len(tags) + CHUNK - 1) // CHUNK
    for ci in range(n_chunks):
        part = tags[ci * CHUNK:(ci + 1) * CHUNK]
        body = "\n".join(f"{ci * CHUNK + j + 1:04d}\t{t}" for j, t in enumerate(part))
        (OUT / f"tags-{ci + 1:02d}.in.txt").write_text(body + "\n", encoding="utf-8")

    print(f"[ok] 分类 {len(cats)} 条 -> categories.in.txt / categories-desc.in.txt")
    print(f"[ok] 标签 {len(tags)} 条 -> {n_chunks} 个分块（每块 {CHUNK}）")
    print(f"[ok] 工作目录 {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
