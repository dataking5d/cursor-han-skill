# VS Code 1.128 / Cursor 3.25.x 的 NLS 汉化机制(逆向笔记)

> 目的: 以后再遇到 "Cursor 更新后变英文" 时**不用重新逆向**。
> 全部结论来自本机 Cursor 3.25.9 (VS Code 基线 1.128.0) 的实际代码与运行时产物, 已验证。

## 0. 结论速览

| 层 | 机制 | 谁负责 |
|---|---|---|
| 官方语言包 | `languagepacks.json` + 语言包扩展 → 启动时生成 clp 中文表 | Cursor 内置机制 |
| Cursor 专有界面 | 注入 `Cursor_Localization.js` 做 DOM 词典翻译 | 第三方工具 `vibepm666/cursor-localization-zh` |
| 官方包漏译的 VS Code 核心文案 | 模块改名导致对不上 → 模块别名补回 | 本 skill 的烘焙层 |

## 1. 代码位置

| 文件 | 作用 |
|---|---|
| `<install>\resources\app\out\main.js` | 主进程 bootstrap。计算 NLS 配置、合并生成中文表 |
| `<install>\resources\app\out\vs\code\electron-utility\sharedProcess\sharedProcessMain.js` | 重建 `languagepacks.json`、清理 `clp` 缓存 |
| `<install>\resources\app\out\vs\code\node\cliProcessMain.js` | 同上(CLI 进程版) |
| `<install>\resources\app\out\vs\code\electron-sandbox\workbench\workbench.js` | **渲染端入口**：`setupNLS(configuration)` 把 `configuration.nls.messages` 写进 `globalThis._VSCODE_NLS_MESSAGES` |
| `<install>\resources\app\out\vs\workbench\workbench.glass.main.js` | Cursor 3.x 的 glass UI 主 bundle（**实际运行的是这个**） |
| `<install>\resources\app\out\vs\workbench\workbench.desktop.main.js` | 传统 desktop UI bundle |

## 2. 数据结构

```
<install>\resources\app\out\nls.keys.json
    [ ["<module path>", ["<key1>", "<key2>"], ...], ... ]     # 1152 组 / 13533 个 key

<install>\resources\app\out\nls.messages.json
    [ "<en0>", "<en1>", ... ]                                  # 扁平数组, 与上面按顺序一一对应
```

语言包 `<pack>\translations\main.i18n.json`:
```json
{ "version": "1.0.0",
  "contents": { "<module path>": { "<key>": "<中文>", ... } } }
```

**合并算法**(`out/main.js`):
```js
for (const [module, keys] of nls.keys) {
    const mod = bundle.contents[module] || {};
    for (const key of keys) out.push(mod[key] || base[i++]);   // 取不到回退英文
}
```

**索引空间已验证对齐**：`workbench.glass.main.js` 里的 localize 调用索引范围 0–13529，
与 `nls.messages.json` 长度 13533 一致；实测 `orig[1770]=="File"` → 烘焙后 `[1770]=="文件"`。

## 3. 官方语言包链路

```
1) ~/.cursor/argv.json  "locale": "zh-cn"           (或 %APPDATA%\Cursor\User\locale.json)
        |  (userLocale = CLI --locale 优先, 其次 argv.json 的 locale;
        |   都没有则退回 Electron app.getLocale() = 操作系统语言)
        v
2) 启动时 out/main.js 的 g5e():
      a. 读 <userData>/languagepacks.json
      b. k_t(): 按 locale 前缀回退匹配(先 "zh-cn", 再 "zh")
      c. 校验: o.hash 是字符串 && o.translations.vscode 是路径 && 该路径文件存在
         —— 任一不满足 -> 直接 return R_() => 走英文, **不报错**
      d. 合并 base(nls.messages.json) + bundle(main.i18n.json)
      e. 写 <userData>/clp/<hash>.<locale>/<commit>/nls.messages.json
         同时写 <userData>/clp/<hash>.<locale>/tcf.json
      f. globalThis._VSCODE_NLS_MESSAGES = 该文件内容
        globalThis._VSCODE_NLS_LANGUAGE = resolvedLanguage
        |
3) 渲染端 setupNLS(configuration) 把 configuration.nls.messages 注入全局
        |
4) 渲染端 localize: Kpd(index, default) = globalThis._VSCODE_NLS_MESSAGES[index] ?? default
        |
5) shared process 每次启动重建 <userData>/languagepacks.json:
      从"已装且启用且与 VS Code 基线兼容"的扩展里,
      挑 manifest.contributes.localizations 非空的, 写进 languagepacks.json
      hash = md5(extensionId + version)
```

## 4. 静默回退英文的四种触发方式

1. `argv.json` / `User\locale.json` 的 `locale` 被改回 `en`
2. 语言包扩展的 `engines.vscode` 不满足 Cursor 的 `vscodeVersion`
   (语言包 `^1.128.0` + Cursor 基线 `1.129.0` **满足**;
   反过来语言包 `^1.129.0` + Cursor 基线 `1.128.0` **不满足** -> 回退)
3. `languagepacks.json` 里 `translations.vscode` 指向的路径不存在
   (扩展被卸载 / 换了版本目录名 / 扩展被禁用)
4. 语言包扩展被禁用或从扩展目录消失

共同特征: **全程无任何错误提示**, 界面就是英文。

## 5. 为什么"只装语言包"不够（实测结论）

语言包装好后：
- ✅ VS Code 核心文案是中文（`运行(R)` / `打开聊天` / `转到文件` / `显示终端` / `最大化聊天` / `添加仓库`）
- ❌ **Cursor 自研 React 界面全是硬编码英文**：`New Chat` / `Automations` / `Customize` /
  `Repositories` / `Cursor Settings` / `插件市场` / `Grok 4.6 Medium` / `Plan New Idea` …
- ❌ 菜单栏标题（`File/Edit/Selection/View/Go/Terminal/Help`）在 Cursor 的 build 里走的是
  `xt(index, default)` 返回的 `{value, original}`，**Cursor 的 menubar 渲染 `original`（英文默认串）**
  而不是 `value`（本地化值）→ 上游语言包对菜单栏无效。

⇒ 必须有第二层：注入 DOM 词典翻译脚本。第三方工具 `vibepm666/cursor-localization-zh` 就是干这个的。

## 6. 模块改名导致漏翻

上游 VS Code 与 Cursor 的 build 之间模块路径有改名（实测 193 个 app 模块在语言包里找不到）:

| Cursor 侧 | 上游语言包侧 |
|---|---|
| `vs/workbench/electron-sandbox/desktop.contribution` | `vs/workbench/electron-browser/desktop.contribution` |
| `vs/workbench/contrib/search/common/searchConfiguration` | `vs/workbench/contrib/search/browser/search.contribution` |
| `vs/workbench/contrib/debug/common/debugConfiguration` | `vs/workbench/contrib/debug/browser/debug.contribution` |
| `vs/workbench/contrib/markers/browser/markers.view.contribution` | `vs/workbench/contrib/markers/browser/markers.contribution` |
| `vs/workbench/contrib/scm/browser/scm.view.contribution` | `vs/workbench/contrib/scm/browser/scm.contribution` |

解法: 用 key 重合度自动推导别名（不写死映射表），核心文案覆盖率 85.4% -> 88.7%。

## 7. 语言包获取

- Open VSX: `https://open-vsx.org/api/MS-CEINTL/vscode-language-pack-zh-hans` -> JSON
  - `version`: 例如 `1.128.0`（与 VS Code 大版本对齐）
  - `files.download`: vsix 直链
- MS Marketplace 公开 API（第三方工具用的就是这个）:
  - 查询 `https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery`
  - 下载 `https://marketplace.visualstudio.com/_apis/public/gallery/publishers/MS-CEINTL/vsextensions/vscode-language-pack-zh-hans/{version}/vspackage`
- VSIX 是 zip，解开后内容在 `extension/` 前缀下，目标目录取 `extension/` 里面的部分。
- 装到 `~/.cursor/extensions/ms-ceintl.vscode-language-pack-zh-hans-<version>/`
  并写进 `~/.cursor/extensions/extensions.json` 才会被 VS Code 识别。

`extensions.json` 单条结构:
```json
{ "identifier": { "id": "ms-ceintl.vscode-language-pack-zh-hans" },
  "version": "1.128.0",
  "location": { "$mid": 1, "fsPath": "c:\\...\\ms-ceintl.vscode-language-pack-zh-hans-1.128.0",
                 "_sep": 1, "external": "file:///c%3A/...", "path": "/c:/...", "scheme": "file" },
  "relativeLocation": "ms-ceintl.vscode-language-pack-zh-hans-1.128.0",
  "metadata": { "isApplicationScoped": true, "isMachineScoped": false, "isBuiltin": false,
                "installedTimestamp": 1791469637890, "pinned": true, "source": "vsix" } }
```

## 8. 注入层改哪些文件（第三方工具）

| 文件 | 改动 | 会被 Cursor 更新覆盖 |
|---|---|---|
| `out/vs/code/electron-sandbox/workbench/workbench.html` | 插入 `<!-- CURSOR_LOCALIZATION_INJECTION -->` + `<script src="./Cursor_Localization.js">` | 会 |
| `out/vs/code/electron-sandbox/workbench/Cursor_Localization.js` | 生成的词典运行时（约 480 KB） | 会 |
| `out/main.js` | 系统托盘右键菜单 4 处固定文案 | 会 |
| `resources/app/product.json` | `checksums` 里 6 个值（含 workbench.html / workbench.js / workbench.desktop.main.js 等） | 会 |

`product.json` 的 checksums 键（本机 Cursor 3.25.9）:
```
vs/base/parts/sandbox/electron-sandbox/preload.js
vs/workbench/workbench.desktop.main.js
vs/workbench/workbench.desktop.main.css
vs/workbench/api/node/extensionHostProcess.js
vs/code/electron-sandbox/workbench/workbench.html
vs/code/electron-sandbox/workbench/workbench.js
```
⚠️ `out/nls.messages.json` **不在** checksums 里 → 烘焙它不会触发「安装已损坏」。

**工具的坑**: 用 HTML 注释标记判断"是否已注入"。标记在但 `<script>` 标签丢了时，
工具会认为无需注入而跳过 → 界面悄悄退回英文且不报错。跑完必须二次校验。

## 9. 本机实测数据(2026-10-19, Cursor 3.25.9 / VS Code 1.128.0)

- `nls.keys.json`: 1152 组 / 13533 key；`nls.messages.json`: 13533 条 —— 必须等长，否则烘焙会错位
- 语言包 `1.128.2026071013`(`engines: ^1.128.0`): 1855 个模块, 94 条 localization
- 烘焙后中文 12011 / 13533 = 88.7%（模块别名补回 33 个模块）
- 内置扩展 84 个写了 `package.nls.zh-cn.json`
- `languagepacks.json` 的 hash = `md5("ms-ceintl.vscode-language-pack-zh-hans" + "1.128.2026071013")`
  = `54412debd66804cdc213392595aa6d50`（与 VS Code 自己算的一致，说明算法复刻正确）
- 注入后主窗口菜单栏实测：`文件 | 编辑 | 选择 | 查看 | 转到 | 运行(R) | 终端 | 帮助`
