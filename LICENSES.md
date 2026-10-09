# 许可与版权 · Licenses & Credits

本仓库是**本地图标索引与浏览工具**，不拥有任何图标版权。
所有 SVG 图标的版权归各自上游项目所有，按各自许可使用与再分发。

---

## 1. 本仓库代码

`scripts/` 与 `web/` 下的脚本、界面代码采用 **MIT License**：

```
MIT License

Copyright (c) 2026 icon-hub contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

> 想换成别的许可（Apache-2.0 / 私有）就改这一节。

---

## 2. 图标数据

> ⚠️ **再分发本仓库（含 fork、打包、二次发布）时，必须保留本文件与 `licenses/` 下的许可原文。**
> 许可证本身就要求"版权声明与许可声明须随所有副本提供"。

| 源 key | 项目 | 许可 | 版权持有者 | 来源 |
|---|---|---|---|---|
| `lucide` | Lucide | ISC（其中 100+ 图标派生自 Feather，适用 MIT） | Lucide Contributors / Cole Bemis | [lucide.dev](https://lucide.dev) · [GitHub](https://github.com/lucide-icons/lucide) |

### lucide

- **许可**：ISC；部分图标派生自 Feather Icons，适用 MIT
- **许可原文**：[`licenses/lucide.txt`](licenses/lucide.txt)（含 Feather 派生图标清单与 MIT 原文）
- **覆盖范围**：`icons/lucide/*.svg`（1870 个图标）、`catalog/lucide/*`（元数据与中文译文）
- **义务**：保留版权声明与许可声明即可。ISC 与 MIT 均为宽松许可 —— 允许商用、修改、再分发，无 copyleft 传染
- **采集版本**：见 `catalog/lucide/source.json` 的 `snapshot` / `fetched_at` 字段

### 新增图标源时

1. `catalog/<源>/source.json` 里填好 `license` 字段
2. 把该源的许可原文拷到 `licenses/<源>.txt`
3. 在上面的表格加一行，并补一节说明义务

> ⚠️ 收录前先看许可类型。未来可能遇到 Apache-2.0、CC0、CC-BY、CC-BY-SA、GPL 等：
> **CC-BY / CC-BY-SA 有强制署名要求，GPL 有 copyleft 传染**，会限制本仓库的许可选择，需单独确认再收。

---

## 3. 免责

- 本仓库不含任何商业图标（如 Font Awesome Pro、Nucleo、Streamline 付费版等）的资源
- 图标名称与标识的商标权归各自所有者，本项目不主张任何商标权利
- 中文译文由本项目自行翻译，仅作检索辅助，不代表上游官方译法
