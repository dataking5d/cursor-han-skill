# Cursor 汉化助手（cursor-han-skill）

把 Cursor 的界面变成**简体中文**，而且**Cursor 自动更新后也不会变回英文**。

> 适用：Cursor 0.x ~ 3.x（Windows / macOS / Linux）
> 无需管理员权限，无需改注册表，不影响账号、设置、项目文件。

---

## 🚀 三步搞定

### 第 1 步：确认电脑上有 Python

打开终端（Windows 按 `Win + R` 输入 `cmd` 回车；macOS 打开「终端」），输入：

```bash
python --version
```

- 显示出 `Python 3.x.x` → 继续第 2 步
- 提示找不到命令 → 去 <https://www.python.org/downloads/> 下载安装，
  **安装时务必勾选 `Add Python to PATH`**，装完重开终端

### 第 2 步：运行汉化

在本目录下：

- **Windows**：双击 `一键汉化.bat`
- **macOS / Linux**：终端里执行 `bash install.sh`
- 手动执行也可以： `python scripts/cursor_han.py`

### 第 3 步：重启 Cursor

> ⚠️ **必须完全退出，不能只关窗口！**
>
> 点右上角的 ✕ 只是隐藏窗口，Cursor 还在后台跑，界面不会刷新。
>
> 正确做法：点屏幕右下角**任务栏托盘**里的 Cursor 图标 → 右键 → **退出**；
> 然后重新打开 Cursor。

完成。菜单、设置、智能体侧栏、插件市场都会变成中文。

---

## 📸 汉化前后

| | 英文 | 中文 |
|---|---|---|
| 顶部菜单 | `File Edit Selection View Go Terminal Help` | `文件 编辑 选择 查看 转到 终端 帮助` |
| 智能体侧栏 | `New Chat / Automations / Customize / Repositories` | `新对话 / 自动化 / 自定义 / 仓库` |
| Cursor 设置 | `Account / Models / Rules / Tools & MCP / Privacy` | `账户 / 模型 / 规则 / 工具与 MCP / 隐私` |
| 常用按钮 | `Show Terminal / Go to File / Add Repository` | `显示终端 / 转到文件 / 添加仓库` |
| 插件市场 | 插件名、简介、按钮全英文 | 全部中文 |

---

## 🔧 为什么需要这个工具（技术说明）

Cursor 是 VS Code 的「换皮版」，它的汉化分**两层**，缺一不可：

| 层 | 覆盖范围 | 谁负责 |
|---|---|---|
| **官方中文语言包** | VS Code 标准菜单、命令面板、内置扩展、通用设置 | VS Code 官方扩展 `Chinese (Simplified)` |
| **界面词典注入** | **Cursor 专有界面**：智能体侧栏、Cursor 设置、插件市场、欢迎页、通知弹窗、系统托盘菜单 | 本工具自动调用 [vibepm666/cursor-localization-zh](https://github.com/vibepm666/cursor-localization-zh) 完成 |

**只装语言包是不够的**——Cursor 自己新写的界面是硬编码英文，语言包管不到。
本工具把两层一起装好，并额外做了两件事：

1. **核心文案补漏**：上游 VS Code 改过模块命名，导致官方语言包对不上 Cursor 的模块划分，
   约 15% 的标准文案会漏翻。工具用 key 重合度自动推导别名补回，
   核心文案覆盖率从 **85.4% → 88.7%**。
2. **抗更新自愈**：Cursor 每次更新都会覆盖安装目录，汉化随之失效。
   装上计划任务后，系统每小时检查一次，**Cursor 一升级就自动重新汉化**。

---

## 📋 全部命令

```bash
python scripts/cursor_han.py              # 一键汉化（默认，第一次用就跑这个）
python scripts/cursor_han.py status       # 只看状态，不改任何东西
python scripts/cursor_han.py selftest     # 自检：逐项体检并给结论
python scripts/cursor_han.py guard        # 只在需要时自动修复（计划任务用）
python scripts/cursor_han.py restore      # 还原回英文
python scripts/cursor_han.py install-task # 注册每小时自动修复的计划任务
python scripts/cursor_han.py uninstall-task
python scripts/cursor_han.py tool-update  # 重新下载最新版汉化组件
```

---

## ❓ 遇到问题？

**先跑自检**：

```bash
python scripts/cursor_han.py selftest
```

它会逐项告诉你哪里有问题。常见情况见 [`references/faq.md`](references/faq.md)。

最常见的三种：

| 现象 | 原因 | 解决 |
|---|---|---|
| 还是英文 | 没完全退出 Cursor | 托盘图标 → 右键 → 退出，再打开 |
| 菜单中文但侧栏英文 | 界面词典没注入 | 重新跑一次 `python scripts/cursor_han.py` |
| 提示「安装已损坏」 | 校验值对不上 | 重新跑一次即可，工具会自动修正 |

---

## 🤖 给 AI 助手 / Agent 用

本目录同时是一个 **Agent Skill**（Claude Code / opencode / Codex / Cursor 等均支持）。

把它放到你的 skills 目录即可：

```powershell
# Claude Code / opencode / Codex 等
Copy-Item -Recurse cursor-han-skill <你的 skills 目录>\cursor-han
```

Skill 说明见 [`SKILL.md`](SKILL.md)，深度机制说明见 [`references/mechanism.md`](references/mechanism.md)。

触发词：`cursor汉化`、`Cursor改成中文`、`Cursor语言包`、`Cursor更新后变英文`、`cursor zh-cn`、
`Cursor界面翻译`、`恢复Cursor英文`。

---

## 📁 目录结构

```
cursor-han-skill/
├── README.md                  ← 你正在看的文件
├── SKILL.md                   ← Agent Skill 定义
├── LICENSE                    ← MIT
├── 一键汉化.bat                ← Windows：双击这个
├── install.sh                 ← macOS / Linux：执行这个
├── scripts/
│   └── cursor_han.py          ← 全部逻辑（纯标准库，无需 pip install）
├── references/
│   ├── faq.md                 ← 小白排错手册
│   └── mechanism.md           ← 底层机制逆向笔记
└── vendor/                    ← 运行时自动下载的汉化组件（不入库）
```

---

## 🙏 致谢与许可

- **汉化组件**：界面词典由 [vibepm666/cursor-localization-zh](https://github.com/vibepm666/cursor-localization-zh)
  提供（作者 VibeP.net）。本工具在**运行时**下载并调用它，**不复制、不分发**其代码，
  其著作权与许可归原作者所有，使用时请遵守上游项目的条款。
- **官方语言包**：`ms-ceintl.vscode-language-pack-zh-hans` © Microsoft Corporation，
  通过 Open VSX / Visual Studio Marketplace 官方渠道获取。
- **本仓库脚本**：MIT License，见 [LICENSE](LICENSE)。

本工具仅修改 Cursor 的界面显示，不修改任何业务逻辑，不上传任何数据。
