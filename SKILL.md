---
name: cursor-han
description: >-
  把 Cursor IDE 界面汉化成简体中文，并在 Cursor 自动更新后自动恢复中文。
  适用于"Cursor 汉化""Cursor 改成中文""Cursor 语言包""Cursor 更新后又变英文了"
  "Cursor 界面翻译""cursor zh-cn""cursor localization""恢复 Cursor 英文"
  "Cursor 装中文语言包""Cursor 菜单中文但侧栏还是英文"等场景。
  一键完成：官方简体中文语言包 + Cursor 专有界面词典注入 + 核心文案补漏，
  并可注册每小时自愈计划任务。
license: MIT
metadata:
  author: Lenovo
  version: 2.0.0
  created: 2026-10-19
  last_reviewed: 2026-10-19
  review_interval_days: 180
---

# Cursor 汉化助手

把 Cursor 变成中文界面，并让它在 Cursor 每次自动更新后自动恢复中文。

## 用户视角：只有三步

1. 确认有 Python 3.8+（`python --version`）
2. 运行 `python scripts/cursor_han.py`（Windows 用户也可双击 `一键汉化.bat`）
3. **完全退出** Cursor 再重开（托盘图标 → 右键 → 退出；只关窗口不算）

默认动作就是"一键汉化"，不需要记任何参数。

## Agent 该做什么

### 1) 用户说"Cursor 变英文了 / 要汉化"

**先跑自检**，再决定动作：

```powershell
python <skill>\scripts\cursor_han.py selftest
```

`selftest` 会逐项给出：官方语言包 / 语言包注册表 / 界面词典注入 / 核心文案补漏 是否正常。
它会直接给出结论和"没发现问题"或列出问题项。

**然后直接跑一键汉化**：

```powershell
python <skill>\scripts\cursor_han.py
```

脚本会：检查环境 → 定位 Cursor → 首次运行自动下载汉化组件 → 执行汉化 →
校验注入 → 补漏 → 自检并打印结论。

跑完**必须提醒用户完全退出 Cursor 再重开**（这是最容易漏的一步，
只重载窗口 / 只关窗口都不会生效，因为 NLS 文案是主进程启动时注入渲染端的）。

### 2) 全部命令

| 命令 | 作用 | 什么时候用 |
|---|---|---|
| （无参数） | 一键汉化 | 默认动作 |
| `status` | 只看状态，不改任何东西 | 用户只想知道现状 |
| `selftest` | 逐项体检 + 结论 | 排错第一步 |
| `guard` | 只在需要时修复 | 计划任务调用；也可手动跑 |
| `restore` | 还原回英文 | 用户想撤销 |
| `install-task` | 注册每小时自动修复计划任务 | 用户抱怨"更新后又变英文" |
| `uninstall-task` | 注销计划任务 | 撤销自愈 |
| `tool-update` | 重新下载最新版汉化组件 | 组件有 bug 或词典更新 |

### 3) 用户抱怨"更新后又变英文"

装上自愈任务即可：

```powershell
python <skill>\scripts\cursor_han.py install-task
```

注册 Windows 计划任务 `CursorHan-Guard`（每小时一次）。它只在两种情况下动手：
- `product.json` 的 `commit` 变了（Cursor 升级了）
- `workbench.html` 里的汉化脚本引用没了（注入被覆盖/损坏）

平时空跑，不打扰用户。

## 汉化是两层，不是一层（关键认知）

| 层 | 机制 | 覆盖 | 谁负责 |
|---|---|---|---|
| 官方语言包 | `languagepacks.json` + 语言包扩展 → 启动时生成中文文案表 | VS Code 标准菜单、命令面板、内置扩展、通用设置 | Cursor 内置机制，脚本负责保证版本匹配 |
| 界面词典注入 | 往 `workbench.html` 注入 `Cursor_Localization.js`，DOM 词典翻译 | **Cursor 专有界面**：智能体侧栏、Cursor 设置、插件市场、欢迎页、通知、托盘菜单 | 第三方组件 `vibepm666/cursor-localization-zh`（脚本运行时下载调用） |
| 核心文案补漏 | 上游 VS Code 改过模块名 → 语言包对不上 → 自动推导模块别名补回 | VS Code 核心文案额外约 3.3% | 本脚本 |

**只装语言包是不够的**（本机实测）：语言包装好后 VS Code 核心文案是中文，
但 Cursor 自研的 React 界面全是硬编码英文。

**第三个坑**：第三方组件用 HTML 注释标记判断"是否已注入"。
标记在但 `<script>` 标签丢了时，它会认为无需注入而直接跳过 → **界面悄悄退回英文且不报错**。
本脚本跑完会二次校验，不一致就恢复 `workbench.html.bak` 再跑一次。

## 排错速查

| 现象 | 原因 | 处理 |
|---|---|---|
| 还是英文 | 没完全退出 Cursor | 托盘图标 → 右键 → 退出 |
| 菜单中文、侧栏英文 | 界面词典没注入 | 跑 `selftest` 看"界面词典注入"段；再跑一键汉化 |
| 提示"安装已损坏" | `product.json` 校验值对不上 | 重新跑一键汉化，脚本会自动修正 |
| 找不到 Cursor | 装在非常见路径 | 设 `CURSOR_INSTALL_DIR=D:\xxx` 后重跑 |
| 首次运行下载失败 | 网络问题 | 手动下载 <https://github.com/vibepm666/cursor-localization-zh> 解压到 `vendor/` 再跑 |
| 某处文案没翻 | 词典缺这条 | 编辑 `vendor/localization/Core_Dictionary.json` 加一条 → `tool-update` 不需要，直接重跑一键汉化 |
| Python 缺失 | — | 装 Python 3.8+，安装时勾 `Add Python to PATH` |

## 关键路径

```
Cursor 安装目录      从注册表 Uninstall 的 InstallLocation 取（勿硬编码）
product.json         <install>\resources\app\product.json  -> version / commit / vscodeVersion / checksums
workbench 目录       <install>\resources\app\out\vs\code\electron-sandbox\workbench\
NLS 基础             <install>\resources\app\out\nls.keys.json + nls.messages.json
用户数据             %APPDATA%\Cursor\  -> languagepacks.json / clp\ / User\locale.json
扩展目录             ~/.cursor/extensions/
argv.json            ~/.cursor/argv.json  -> locale
日志                 %LOCALAPPDATA%\cursor-han\cursor-han.log
```

深度机制见 `references\mechanism.md`，面向人的排错见 `references\faq.md`。

## 许可与致谢

- 本仓库脚本：MIT。
- 界面词典组件由 [vibepm666/cursor-localization-zh](https://github.com/vibepm666/cursor-localization-zh)
  （作者 VibeP.net）提供，**运行时下载调用、不做二次分发**，著作权归原作者。
- 官方语言包 `ms-ceintl.vscode-language-pack-zh-hans` © Microsoft Corporation。

## 本 skill 的上游仓库与目录关系

开源地址：**https://github.com/dataking5d/cursor-han-skill**

**本仓库工作副本就是唯一源**：

```
D:\all_my_projects\cursor-han-skill\      ← 唯一源（git 仓库，直接编辑这里）
        ↑
        │ junction
D:\.claude\skills\cursor-han\             ← 数据源目录（指向工作副本）
        ↑
        │ junction
C:\Users\Lenovo\.codex\skills\cursor-han
C:\Users\Lenovo\.cursor\skills\cursor-han
C:\Users\Lenovo\.agents\skills\cursor-han
C:\Users\Lenovo\Doubao\skills\cursor-han
C:\Users\Lenovo\DoubaoWork\skills\cursor-han
```

改完直接提交推送即可，各 agent 自动同步：

```powershell
cd D:\all_my_projects\cursor-han-skill
git add -A; git commit -m "..."; git push
```

注意 `vendor/`（第三方汉化组件）已被 `.gitignore` 排除，运行时自动下载。

