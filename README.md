# Icon Hub · 本地图标库

把分散在各处的开源图标库（Lucide、Tabler、Heroicons…）整合成**一份本地数据库 + 一个本地浏览界面**，
按官网的分类与标签体系组织，离线可用，不依赖任何在线服务。

当前已接入：**Lucide**（1870 个图标 / 42 个分类 / 4095 个标签 / 264 个别名，ISC 许可）。

```
图标上游 → catalog/（统一数据契约） → data/icon-hub.db（SQLite） → web/（本地浏览界面）
```

---

## 目录结构

| 路径 | 说明 |
|---|---|
| `catalog/<源>/source.json` | 源元信息：名称、主页、许可、版本、采集时间、统计 |
| `catalog/<源>/categories.json` | 分类（双语字段） |
| `catalog/<源>/icons.jsonl` | 图标，一行一条，含 tags / categories / aliases |
| `catalog/<源>/zh.json` | 中文译文层，存在则合并进数据库 |
| `catalog/<源>/_zh_work/` | 翻译工作区（分块清单 + 译文） |
| `icons/<源>/*.svg` | 原样 SVG 文件 |
| `data/icon-hub.db` | SQLite 数据库（派生产物，可随时删掉重建，**不入库**） |
| `scripts/` | 采集 / 建库 / 双语工作流，共 5 个脚本 |
| `web/` | 本地浏览界面（纯静态，无依赖） |
| `LICENSES.md` + `licenses/` | 代码许可 + 各图标源的许可原文与署名义务 |
| `vendor/` | 上游原始快照（120 M+，**不入库**，见下方「更新上游」重新下载） |
| `_verify/` | 界面验收截图（**不入库**） |

> 本仓库用 `.gitignore` 排除了 `vendor/`、`data/*.db`、`web/data/*` —— 它们都能从
> `catalog/` + 上游快照重建。**clone 之后必须先跑一次「更新上游」下载快照，再跑快速开始。**

---

## 快速开始

```bash
cd icon-hub                      # 换成你 clone 下来的位置

# 0. 首次运行前：下载上游快照（约 5.5 MB，解压出 vendor/lucide-main/）
mkdir -p vendor && cd vendor
curl -L -o lucide-main.tar.gz https://codeload.github.com/lucide-icons/lucide/tar.gz/refs/heads/main
tar -xzf lucide-main.tar.gz && cd ..

# 1. 采集上游数据 → catalog/
python scripts/fetch_lucide.py

# 2. 建数据库
python scripts/build_db.py

# 3. 导出前端数据
python scripts/export_web.py

# 4. 打开界面
#    直接双击 web/index.html 即可（file:// 能用）
#    或因浏览器限制改用本地服务：
python -m http.server 8765 --directory web
#    然后访问 http://127.0.0.1:8765/
```

> Windows 下若命令行输出中文乱码：先执行 `chcp 65001`。
> 脚本用任意 Python 3.10+ 均可（只用标准库，无需装包）。

---

## 界面功能

- **左侧分类栏**：43 项（全部 + 42 个分类），带图标计数，顺序与 lucide.dev 官网一致
- **搜索**：匹配 名称 / 别名 / 标签 / 分类，多关键词空格分隔（按 `/` 快速聚焦）；
  **中文界面下可直接输中文搜**——先用中文反查命中的中文标签/分类，再映射回图标（搜「关闭」能命中 `x`、`power-off` 等 36 个）
- **语言切换**：右上角 `EN / 中文`，切换即时生效并记住选择
- **Customizer 面板**：工具栏右侧按钮展开，仿 lucide.dev 的定制器，**控制整个网格**的外观
  - Color：色块取色 + `#hex` 文本框（支持 3 位缩写，失焦自动纠正）
  - Stroke width：0.5–4.0 px，右侧显示当前值
  - Size：16–96 px，右侧显示当前值
  - Non-scaling stroke：开关，开启后描边不随图标缩放（`vector-effect: non-scaling-stroke`）
  - 右上角一键重置；设置自动记住；点面板外或 `Esc` 收起
- **详情抽屉**：点任意图标 → 调尺寸 / 线宽 / 颜色，复制 SVG、复制 JSX、复制名称、下载 `.svg`
  （只影响这一个图标的预览与复制输出，与 Customizer 的全局外观互不干扰）
- **可分享链接**：`index.html?lang=zh&q=close&cat=account&icon=user` 直接还原界面状态；
  外观也能带：`?cz=1&size=40&stroke=1&color=%23e11d48&nonscaling=1`

---

## 双语标签机制

数据库里 **分类** 和 **标签** 都是双列结构：

```sql
categories(title_en, title_zh, description_en, description_zh)
tags(label_en, label_zh)
sources(name_en, name_zh)
```

- **英文与中文均已 100% 就绪**：42 个分类（含描述）+ 4095 个标签全部有中文
- 界面语言切换即时生效；任何字段缺译文时**自动回退英文**，不会出现空白
- 中文译文源文件是 `catalog/lucide/zh.json`（由 `_zh_work/` 下的逐块译文合并而来）
- 技术专有名词（`Wi-Fi`、`JSON`、`Git`、`CSS`、`QR`、`API` 等）保留英文原文，便于检索
- 纯符号与 emoji 标签（`$`、`÷`、`🌊`）原样保留

`catalog/lucide/zh.json` 格式：

```json
{
  "source_name_zh": "Lucide",
  "categories": {
    "accessibility": "无障碍",
    "account.description": "用于用户资料、身份、设置、会员以及个人账户操作的图标。"
  },
  "tags": {
    "close": "关闭",
    "delete": "删除"
  }
}
```

- `categories` 的键是分类 key，加 `.description` 后缀则填描述
- `tags` 的键是标签原文（英文小写）

### 修改 / 重新翻译中文

| 场景 | 做法 |
|---|---|
| 改几条译文（最快） | 直接编辑 `catalog/lucide/zh.json`，再跑 `build_db.py` + `export_web.py` |
| 批量重译 | 改 `_zh_work/tags-NN.out.txt` → `python scripts/apply_zh.py` → 再建库导出 |
| 上游更新后要重译 | `make_zh_worklist.py` 重出清单（新标签会追加到末尾块）→ 补 `*.out.txt` → `apply_zh.py` |

`catalog/lucide/_zh_work/` 是翻译工作区，**`apply_zh.py` 靠序号对齐合并，会强校验错位/缺失/多余，对不上直接报错退出**：

- `*.in.txt` — 自动生成的原文清单（`序号 \t 英文`），由 `make_zh_worklist.py` 产出
- `*.out.txt` — 译文（`序号 \t 中文`），只需保证序号对应，不必重复写 key（避免手工敲错 key）

> 这个「序号对齐」设计是刻意的：4095 条标签手工搬运 key 极易错位，而错位会让译文张冠李戴且难以发现。
> 序号校验让错误在合并阶段就暴露。

---

## 数据库结构

```
sources            图标源（key / name_en / name_zh / license / version / 统计）
categories         分类（source_key / key / title_en / title_zh / sort_order / icon_count）
icons              图标（source_key / name / primary_category / svg_path / deprecated）
  └ aliases        别名（一个图标可有多个旧名，264 条）
tags               标签词表（key / label_en / label_zh，4095 条）
icon_categories    图标 ↔ 分类（is_primary 标记主分类，官网布局按它归类）
icon_tags          图标 ↔ 标签（15531 条）
meta               元信息（schema_version / built_at / 语言设置）
icons_fts          FTS5 全文索引（name / aliases / tags / categories）
v_icons            视图：一行拿到某个图标的分类、标签、别名的逗号串
v_stats            视图：各类总数
```

常用查询：

```sql
-- 找图标（含别名与标签命中）
SELECT name FROM icons_fts WHERE icons_fts MATCH 'close';

-- 某个分类下的图标
SELECT i.name FROM icons i
JOIN icon_categories ic ON ic.icon_id = i.id
JOIN categories c ON c.id = ic.category_id
WHERE c.key = 'account' ORDER BY i.name;

-- 给某个图标打上全部信息
SELECT * FROM v_icons WHERE name = 'user';
```

---

## 更新上游数据

Lucide 的真源是 GitHub 仓库快照（不是 npm 包——npm 包不含分类归属）：

```bash
cd D:/01/ku/icon-hub/vendor
curl -L -o lucide-main.tar.gz https://codeload.github.com/lucide-icons/lucide/tar.gz/refs/heads/main
tar -xzf lucide-main.tar.gz          # 解压出 lucide-main/
cd .. && python scripts/fetch_lucide.py && python scripts/build_db.py && python scripts/export_web.py
```

每次都从 `catalog/` 重新生成数据库和前端数据，所以**重建不会丢东西**——
前提是你补的中文写在 `catalog/<源>/zh.json` 里，而不是直接改数据库。

---

## 接入新的图标源

架构是「一个源 = 一个目录」，加源不需要改数据库和界面代码：

1. 把新源的数据抓下来（npm 包 / GitHub 快照 / 官方 JSON 都行）
2. 写一个 `scripts/fetch_<源>.py`，产出与 Lucide 相同的三份文件：
   `catalog/<源>/source.json`、`categories.json`、`icons.jsonl`，SVG 放 `icons/<源>/`
3. 跑 `build_db.py` + `export_web.py` —— 界面会自动多出这个源的分类和图标

`icons.jsonl` 每行的字段（字段名固定，下游全靠它）：

```json
{"name":"user","categories":["account"],"tags":["person","account"],
 "aliases":["user-round"],"use_cases":[],"contributors":["..."],
 "deprecated":false,"svg_file":"icons/lucide/user.svg","svg_bytes":299}
```

---

## 已知限制

- 中文为逐条人工校对翻译，个别冷门专业词做了保守处理（`mistwarp` 保留原文、`snake holder` 意译），发现不合适可直接改 `zh.json`
- 别名（264 个）在界面里只能从详情抽屉看到，没有独立卡片；点别名会当成搜索词
- 界面一次渲染全部结果（1870 个），首次加载约 0.3 秒；源变多后需要改成分页或虚拟滚动
- `web/data/catalog.js` 是 1.4 MB 的生成物，不要手工编辑

## 许可

- **本仓库代码**（`scripts/`、`web/`）：MIT
- **图标数据**：版权归各上游项目所有，本项目只做本地索引与浏览。Lucide 采用 ISC（其中 100+ 图标派生自 Feather Icons，适用 MIT）
- **再分发义务**：必须保留版权声明与许可原文 —— 完整清单见 [`LICENSES.md`](LICENSES.md)，原文在 [`licenses/`](licenses/)
