# 小白排错手册

按顺序看，大部分问题在第 1 条就解决了。

---

## 0. 先跑这一条

```bash
python scripts/cursor_han.py selftest
```

它会逐项告诉你哪里好、哪里坏，最后给结论。把输出发给别人，对方就能直接判断问题。

---

## 1. 跑完了，界面还是英文

**99% 是这个原因：没有完全退出 Cursor。**

- ❌ 点窗口右上角的 `✕` —— 这只是隐藏窗口，Cursor 进程还在后台，界面不会重新加载
- ❌ 在 Cursor 里 `Ctrl+Shift+P` → `Developer: Reload Window` —— 也不行，
  因为界面文案是**主进程启动时**一次性注入的，重载窗口拿不到新的
- ✅ 任务栏右下角**托盘**（可能被藏在 `^` 箭头里）→ 找到 Cursor 图标 → **右键 → 退出**
  → 然后从开始菜单重新打开 Cursor

如果托盘里根本找不到 Cursor 图标：打开任务管理器 → 找到 `Cursor.exe` → 结束任务。

---

## 2. 菜单是中文了，但智能体侧栏 / Cursor 设置 / 插件市场还是英文

这是**正常现象的一半**——说明只装了语言包，界面词典没注入成功。

```bash
python scripts/cursor_han.py selftest
```

看「界面词典注入」那一段：

- 显示 `[失败] 未注入` → 重新跑一次一键汉化：
  ```bash
  python scripts/cursor_han.py
  ```
  脚本会自动发现注入不完整、恢复备份、重新注入。

- 显示 `[成功] 已注入` 但界面还是英文 → Cursor 没完全退出，回到第 1 条。

---

## 3. 弹窗提示 "Your Cursor installation appears to be corrupt"

因为汉化会修改 Cursor 安装目录里的文件，Cursor 自带的完整性校验对不上了。

**这不是真坏了**，重新跑一次一键汉化即可 —— 脚本会自动把 `product.json` 里的校验值同步更新。

```bash
python scripts/cursor_han.py
```

如果还弹：

```bash
# 先把界面词典撤掉
python scripts/cursor_han.py tool-restore
# 再重装
python scripts/cursor_han.py
```

---

## 4. 提示「没找到 Cursor 安装目录」

Cursor 装在了非常见位置。告诉脚本路径：

**Windows（cmd）**：
```cmd
set CURSOR_INSTALL_DIR=D:\Program Files\Cursor
python scripts\cursor_han.py
```

**Windows（PowerShell）**：
```powershell
$env:CURSOR_INSTALL_DIR = "D:\Program Files\Cursor"
python scripts\cursor_han.py
```

**macOS / Linux**：
```bash
export CURSOR_INSTALL_DIR="/Applications/Cursor.app"
python3 scripts/cursor_han.py
```

路径要指向**装着 `Cursor.exe`（或 `Cursor.app`）的那一层**。

---

## 5. 提示「没有找到 Python」

去 <https://www.python.org/downloads/> 下载安装。

**Windows 安装时最关键的一步**：勾上 **`Add python.exe to PATH`**，不然终端里还是找不到。

装完要**重开终端**（关掉再打开），再 `python --version` 确认。

---

## 6. 首次运行下载汉化组件失败

组件是从 GitHub 下载的。需要能访问 `github.com` / `codeload.github.com`。

手动下载也行：

1. 打开 <https://github.com/vibepm666/cursor-localization-zh>
2. `Code` → `Download ZIP`
3. 解压后，把里面**所有文件**放进本目录的 `vendor\` 文件夹
4. 再跑 `python scripts/cursor_han.py`

---

## 7. Cursor 更新之后又变英文了

这是最常见的长期痛点。装上自愈任务：

```bash
python scripts/cursor_han.py install-task
```

它会注册一个 Windows 计划任务，每小时检查一次。
Cursor 一升级、或汉化文件被覆盖，它就自动重新汉化，你什么都不用做。

想取消：

```bash
python scripts/cursor_han.py uninstall-task
```

---

## 8. 想彻底还原成英文

```bash
python scripts/cursor_han.py restore
```

这会撤销界面词典注入、还原被改过的文案、移除补漏文件。

**官方中文语言包会保留**，所以界面可能还是中文。要彻底变英文：
Cursor 设置 → 扩展 → 搜 `Chinese (Simplified)` → 卸载 → 完全退出重开。

---

## 9. 某些文案没汉化

词典里没收录的词条就是英文，属于正常情况。可以自己补：

1. 打开 `vendor\localization\Core_Dictionary.json`
2. 找到 `sections` 数组，往某个 section 的 `entries` 里加一行：
   ```json
   ["英文原文", "中文翻译"]
   ```
3. 保存，重新跑 `python scripts/cursor_han.py`，完全退出 Cursor 再重开

> 注意：中文里不要用全角引号 `“”`，否则生成的 JS 会报错导致整个汉化失效。

---

## 10. 还是不行？把日志发出来

日志在：

```
Windows: %LOCALAPPDATA%\cursor-han\cursor-han.log
macOS/Linux: ~/Library/Logs 或 /tmp/cursor-han/cursor-han.log
```

这个文件里有每一步的执行记录，包含组件的原始输出。发给懂行的人，一眼就能看出卡在哪。
