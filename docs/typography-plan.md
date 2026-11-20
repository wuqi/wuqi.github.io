# 博客排版 / 代码高亮 / 字体改造方案

> 目标：改善 `diphda.info` 的中文阅读体验，统一代码块样式，引入霞鹜文楷。
>
> 决策：霞鹜文楷（LXGW WenKai Screen） + Hugo Chroma `github` 浅色 + 正文 17px。

## 一、现状问题

- 正文 `14px / line-height: 1.5`，偏挤；`h2` 仅 `1.28571em`，层级弱。
- 代码块使用正文字体（非等宽）；Hugo Chroma 已生成 class 但没有对应 CSS；同时加载 prettify，且 `pre.prettyprint` 设置了 `white-space: normal`，导致代码乱换行。
- 全站纯系统字体，没有中文排版优化。

## 二、中文排版

新建 `themes/jianshu/static/css/typography.css`，在配色 CSS 之后加载，只作用于正文、评论、标题，不动导航与侧栏。

核心规则：

- 正文 `font-size: 17px; line-height: 1.85; color: #2b2b2b;`
- `text-align: justify; text-justify: inter-ideograph;`
- `overflow-wrap: break-word;`
- 段落 `margin: 1.1em 0;`
- `h2: 1.5em`、`h3: 1.25em`，段前留白加大
- 引用块：浅灰底 + 左边框
- 列表、表格（细边框/斑马纹）、图片（居中/圆角）、`hr`、`::selection`
- 行内 `code`：浅灰底、小圆角、中性色
- 移动端 `16px / 1.8`
- 夜间模式 `.night-mode` 覆盖文字、引用、表格颜色
- `baseof.html` 的 `<html>` 补 `lang="zh-CN"`

## 三、代码高亮

- 弃用 prettify：删除 `head.html` 的 CSS 引用、`footer.html` 的 JS 与 `prettyPrint()` 调用。
- 使用 Hugo 内置 Chroma（构建期高亮，零 JS）：
  - `hugo.toml`：`style = "github"`、`lineNos = false`、`noClasses = false`
  - 生成 `themes/jianshu/static/css/chroma-light.css`
- 代码块样式：
  - 等宽栈：`ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace`
  - 背景 `#f6f8fa`、1px 边框、8px 圆角、`padding: 1em`
  - `overflow-x: auto`、`white-space: pre`
- 修正/清理 `pre.prettyprint` 的 `white-space: normal` 残留。

## 四、字体

- 使用 **LXGW WenKai Screen**（霞鹜文楷屏幕优化版，OFL 许可）。
- 自托管到 `themes/jianshu/static/fonts/lxgw-wenkai-screen/`，不依赖第三方 CDN；字体按 unicode-range 切片，浏览器按需加载。
- 应用于 `.post-content`、`.comment-content`、`.post-title` 及正文标题。
- UI（导航、元信息、按钮）保持系统无衬线；代码保持等宽。
- `font-display: swap`，字体目录附 `OFL.txt`。
- 字体若缺粗体，浏览器合成粗体，可接受。

## 五、改动文件

| 操作 | 文件 |
| --- | --- |
| 新增 | `themes/jianshu/static/css/typography.css` |
| 新增 | `themes/jianshu/static/css/chroma-light.css` |
| 新增 | `themes/jianshu/static/fonts/lxgw-wenkai-screen/**` |
| 新增 | `docs/typography-plan.md` |
| 修改 | `themes/jianshu/layouts/partials/head.html` |
| 修改 | `themes/jianshu/layouts/partials/footer.html` |
| 修改 | `themes/jianshu/layouts/_default/baseof.html` |
| 修改 | `hugo.toml` |
| 清理 | `themes/jianshu/static/css/default.css` 中 prettify 残留 |

6 套配色 CSS 本体不动，由 `typography.css` 统一覆盖。

## 六、验证

- 本地 `hugo server` 对比：长文、代码文、表格、引用、图片、移动端、夜间模式。
- 确认代码块横向滚动、不自动换行；字体分片正常加载、无布局抖动。
- 部署后抽 2–3 篇线上验证。

## 七、回滚

改动集中在独立文件与少量模板引用；回滚只需还原 `head.html`、`footer.html`、`baseof.html`、`hugo.toml`，并删除新增的 CSS / 字体文件。
