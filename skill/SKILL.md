---
name: icon-hub
description: 从本地图标库（Lucide + Tabler，共 8108 个图标）按中英文关键词检索图标，返回图标名、分类、标签与可直接使用的 SVG 源码。当用户要找图标、选图标、给界面或文档配图标、问"有没有表示 XX 的图标"、需要某个图标的 SVG 代码、或想按分类浏览图标时使用。触发词：找图标、选图标、图标推荐、配图标、图标库、search icon、find icon、svg icon、icon 查询。
---

# Icon Hub — 本地图标检索

离线的图标库检索工具。**8,108 个图标**（Lucide 1,870 + Tabler 6,238）、83 个分类、9,321 个标签，
**中英双语完整**（分类与标签都有中英文），不联网、不需要安装任何依赖。

## 什么时候用

- 「帮我找个表示上传的图标」
- 「这个界面要配几个导航图标，选哪些好」
- 「有没有类似'删除'的图标」
- 「给我一个 close 图标的 SVG 代码」
- 「Tabler 里品牌类的图标有哪些」

## 什么时候不用

- 用户问的是本库**没有收录**的图标集（Font Awesome Pro、Nucleo 等商业库）
- 只是聊天里提到"图标"两个字，没有检索意图

---

## 用法

脚本位置：`scripts/query.py`（相对本 skill 目录）。纯 Python 标准库，无网络请求。

### 一、搜索图标

```bash
python scripts/query.py "关闭"                     # 中文关键词
python scripts/query.py "delete" --limit 10        # 英文关键词，限制条数
python scripts/query.py "arrow" "left"             # 多个词取交集
python scripts/query.py "上传" --source tabler      # 限定数据源
python scripts/query.py --category brand           # 按分类浏览
python scripts/query.py --style filled "home"      # 只要实心版（仅 Tabler 有）
python scripts/query.py "关闭" --format text        # 人类可读输出
```

匹配范围：**图标名 / 别名 / 标签（中英）/ 分类（中英）**，所以中文和英文关键词都能命中。

返回 JSON：

```json
{
  "query": "关闭",
  "total": 36,
  "returned": 5,
  "results": [
    {
      "name": "x",
      "source": "lucide",
      "source_name": "Lucide",
      "categories": [{"key": "alerts", "title": "提醒"}],
      "tags": [{"key": "close", "label": "关闭"}],
      "aliases": [],
      "svg_file": "icons/lucide/x.svg",
      "svg_bytes": 268,
      "score": 100
    }
  ]
}
```

- `total` 是全部命中数，`returned` 是本次返回数（默认上限 20）
- `score` 是相关度：名称精确 100 / 名称开头 60 / 名称包含 40 / 别名 30 / 标签 20 / 分类 10
- `name` + `source` 是图标的**唯一标识** —— 两个库存在同名图标（如 `user`）

### 二、取 SVG 源码

```bash
python scripts/query.py "关闭" --svg                    # 搜索结果里附带 SVG
python scripts/query.py --get x --source lucide --svg   # 按名称精确取单个
python scripts/query.py --get tabler:brand-github --svg # 也可写 源:名称
```

SVG 源码已内联在本地数据里，**不需要联网**。

### 三、探索数据

```bash
python scripts/query.py --stats             # 总量统计
python scripts/query.py --list-sources      # 有哪些图标源
python scripts/query.py --list-categories   # 全部分类（83 个，含中英文名）
```

---

## 给使用者的建议

1. **先搜后取**：先用较小的 `--limit` 搜候选（比如 5–8 个），选定后再 `--get` 取 SVG。
   一次性拉太多结果会淹没重点。
2. **中文直接问**：库里的中文标签是完整的（9,321 条全译），用户用中文就用中文关键词，
   不必先翻译成英文。
3. **同一个概念多给几个候选**：不同图标库的命名习惯不同（`trash` vs `delete` vs `x`），
   给 3–5 个选项让用户挑，比只给一个更实用。
4. **引用时带上数据源**：`lucide:x` 和 `tabler:x` 是两个不同的图标。
5. **Tabler 有两种风格**：`outline`（默认）与 `filled`（实心）。
   filled 版的名字带 `-filled` 后缀，可用 `--style filled` 筛选。
6. **分类是「源:key」的形式**：两库有同名分类（如都有 `brand`），
   用 `--list-categories` 看全称。

---

## 数据来源与许可

| 源 | 图标 | 分类 | 许可 |
|---|---:|---:|---|
| Lucide | 1,870 | 42 | ISC |
| Tabler Icons | 6,238 | 41 | MIT |

两者都是宽松许可，可商用、可修改、可再分发。图标版权归各自上游项目所有。

数据文件 `data/icon-hub.db` 由仓库的 `scripts/build_db.py` 生成，
再由 `skill/scripts/install.py` 内联 SVG 后打包，随 skill 一起分发。
