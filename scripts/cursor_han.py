#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor 汉化工具 —— 一键把 Cursor 界面变成简体中文

【小白用法】只需要在终端里运行这一句：
    python cursor_han.py

【给 Agent / 高级用户用的子命令】
    status          只看状态，不改任何东西
    selftest        自检：环境 / 语言包 / 注入 / 烘焙 逐项体检
    guard           只在 Cursor 升级或汉化失效时自动修复（计划任务用）
    restore         全部还原成英文
    install-task    注册每小时自动修复的计划任务
    uninstall-task  注销计划任务
    tool-update    重新下载最新版汉化组件
    help            看帮助

作者: Lenovo
汉化组件: vibepm666/cursor-localization-zh (https://github.com/vibepm666/cursor-localization-zh)
          该组件由第三方作者提供并拥有其著作权，本脚本仅在运行时下载调用，不做二次分发。
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime

# --------------------------------------------------------------------------- #
# 基本设置
# --------------------------------------------------------------------------- #

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

VERSION = "2.0.0"

# 官方中文语言包
PACK_ID = "ms-ceintl.vscode-language-pack-zh-hans"
PACK_PUBLISHER = "MS-CEINTL"
LOCALE = "zh-cn"

# 第三方汉化组件（运行时下载）
UPSTREAM_REPO = "vibepm666/cursor-localization-zh"
UPSTREAM_ZIP = "https://codeload.github.com/%s/zip/refs/heads/main" % UPSTREAM_REPO
UPSTREAM_HOME = "https://github.com/%s" % UPSTREAM_REPO

# Open VSX 语言包源
OPENVXS_API = "https://open-vsx.org/api/%s/vscode-language-pack-zh-hans" % PACK_PUBLISHER

# 注入标记
INJECT_JS_NAME = "Cursor_Localization.js"
WORKBENCH_HTML_NAME = "workbench.html"

# 目录
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_DIR = os.path.join(SKILL_DIR, "vendor")
VENDOR_TOOL = os.path.join(VENDOR_DIR, "Cursor_Localization_Tool.py")
TOOL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "cursor-han")
LOG_FILE = os.path.join(TOOL_DIR, "cursor-han.log")
TASK_NAME = "CursorHan-Guard"

STAMP_FILE_NAME = "nls.messages.json.han-stamp.json"
BASE_FILE_NAME = "nls.messages.json.en-base.json"
BAKED_MANIFEST = os.path.join(TOOL_DIR, "baked-files.json")

LINE = "=" * 58


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #


def log(msg):
    try:
        os.makedirs(TOOL_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:
        pass


def head(title):
    print()
    print(LINE)
    print("  " + title)
    print(LINE)


def step(n, total, msg):
    print()
    print("[%d/%d] %s" % (n, total, msg))


def ok(msg):
    print("      [成功] " + msg)


def warn(msg):
    print("      [注意] " + msg)


def bad(msg):
    print("      [失败] " + msg)


def info(msg):
    print("      " + msg)


def done(title, lines):
    print()
    print(LINE)
    print("  " + title)
    print(LINE)
    for x in lines:
        print("  " + x)
    print(LINE)


# --------------------------------------------------------------------------- #
# 通用工具
# --------------------------------------------------------------------------- #


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, obj, indent=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        if indent:
            json.dump(obj, f, ensure_ascii=False, indent=indent)
        else:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


def user_data_dir():
    return os.path.join(os.environ["APPDATA"], "Cursor")


def extensions_dir():
    return os.path.join(os.path.expanduser("~"), ".cursor", "extensions")


def argv_path():
    return os.path.join(os.path.expanduser("~"), ".cursor", "argv.json")


def languagepacks_path():
    return os.path.join(user_data_dir(), "languagepacks.json")


def app_out_dir(install):
    return os.path.join(install, "resources", "app", "out")


# --------------------------------------------------------------------------- #
# 找到 Cursor
# --------------------------------------------------------------------------- #


def _registry_candidates():
    out = []
    try:
        import winreg
    except ImportError:
        return out
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, sub in roots:
        try:
            key = winreg.OpenKey(hive, sub)
        except OSError:
            continue
        try:
            n = winreg.QueryInfoKey(key)[0]
            for i in range(n):
                try:
                    name = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, name) as sk:
                        try:
                            dn = winreg.QueryValueEx(sk, "DisplayName")[0]
                        except OSError:
                            continue
                        if not dn or "cursor" not in dn.lower():
                            continue
                        try:
                            loc = winreg.QueryValueEx(sk, "InstallLocation")[0]
                        except OSError:
                            loc = ""
                        if loc:
                            out.append(loc.rstrip("\\/"))
                except OSError:
                    continue
        finally:
            key.Close()
    return out


def _known_candidates():
    lad = os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local")
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    return [
        r"D:\Cursor",
        os.path.join(lad, "Programs", "cursor"),
        os.path.join(lad, "Programs", "Cursor"),
        os.path.join(pf, "Cursor"),
        os.path.join(pf86, "Cursor"),
    ]


def find_cursor():
    found, seen = [], set()
    for c in _registry_candidates() + _known_candidates():
        if not c:
            continue
        key = os.path.normcase(os.path.abspath(c))
        if key in seen:
            continue
        seen.add(key)
        if os.path.isfile(os.path.join(c, "resources", "app", "product.json")):
            found.append(c)
    return found


def pick_cursor():
    c = find_cursor()
    return c[0] if c else None


def read_product(install):
    p = read_json(os.path.join(install, "resources", "app", "product.json"), {}) or {}
    return {
        "nameLong": p.get("nameLong", "Cursor"),
        "version": p.get("version", "?"),
        "commit": p.get("commit", "?"),
        "vscodeVersion": p.get("vscodeVersion", "?"),
    }


# --------------------------------------------------------------------------- #
# 版本号判断
# --------------------------------------------------------------------------- #


def parse_ver(v):
    nums = [int(x) for x in re.findall(r"\d+", v or "")[:3]]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def _cmp(a, b):
    return (a > b) - (a < b)


def _satisfies_one(version, comp):
    comp = comp.strip()
    if not comp or comp == "*":
        return True
    m = re.match(r"^(\^|~|>=|<=|>|<|=)?\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", comp)
    if not m:
        return True
    op = m.group(1) or "="
    major = int(m.group(2))
    minor = int(m.group(3)) if m.group(3) is not None else None
    patch = int(m.group(4)) if m.group(4) is not None else None
    base = (major, minor if minor is not None else 0, patch if patch is not None else 0)
    if op == "^":
        if major > 0:
            upper = (major + 1, 0, 0)
        elif minor is not None and minor > 0:
            upper = (0, minor + 1, 0)
        else:
            upper = (0, 0, (patch or 0) + 1)
        return base <= version < upper
    if op == "~":
        upper = (major + 1, 0, 0) if minor is None else (major, minor + 1, 0)
        return base <= version < upper
    if op == ">=":
        return version >= base
    if op == "<=":
        return version <= base
    if op == ">":
        return version > base
    if op == "<":
        return version < base
    if minor is None:
        return version[0] == major
    if patch is None:
        return version[:2] == (major, minor)
    return version == base


def satisfies(version, rng):
    if not rng:
        return True
    v = parse_ver(version)
    for alt in str(rng).split("||"):
        parts = [p for p in re.split(r"\s+", alt.strip()) if p]
        if parts and all(_satisfies_one(v, p) for p in parts):
            return True
    return False


# --------------------------------------------------------------------------- #
# 官方中文语言包
# --------------------------------------------------------------------------- #


def list_pack_folders():
    base = extensions_dir()
    if not os.path.isdir(base):
        return []
    return [
        os.path.join(base, n)
        for n in os.listdir(base)
        if n.startswith(PACK_ID + "-")
    ]


def read_pack(folder):
    pj = read_json(os.path.join(folder, "package.json"))
    if not pj:
        return None
    return {
        "folder": folder,
        "name": pj.get("name"),
        "version": pj.get("version"),
        "engines": (pj.get("engines") or {}).get("vscode", ""),
        "localizations": ((pj.get("contributes") or {}).get("localizations") or []),
    }


def find_pack(cursor_vsc_version):
    packs = []
    for folder in list_pack_folders():
        p = read_pack(folder)
        if p:
            packs.append(p)
    packs.sort(key=lambda p: parse_ver(p["version"]), reverse=True)
    for p in packs:
        if satisfies(cursor_vsc_version, p["engines"]):
            return p, packs
    return None, packs


def openvsx_download(vscode_version, dest_dir):
    import urllib.request

    url = OPENVXS_API + "/" + vscode_version
    log("GET %s" % url)
    with urllib.request.urlopen(url, timeout=30) as r:
        meta = json.loads(r.read().decode("utf-8"))
    dl = (meta.get("files") or {}).get("download")
    if not dl:
        raise RuntimeError("Open VSX 未提供下载地址")
    version = meta.get("version") or vscode_version
    os.makedirs(dest_dir, exist_ok=True)
    vsix = os.path.join(dest_dir, "%s-%s.vsix" % (PACK_ID, version))
    log("GET %s" % dl)
    with urllib.request.urlopen(dl, timeout=120) as r, open(vsix, "wb") as f:
        shutil.copyfileobj(r, f)
    return vsix, version


def extract_vsix(vsix, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(vsix) as z:
        for member in z.namelist():
            if not member.startswith("extension/"):
                continue
            rel = member[len("extension/"):]
            if not rel:
                continue
            dest = os.path.join(target_dir, rel.replace("/", os.sep))
            if member.endswith("/"):
                os.makedirs(dest, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with z.open(member) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)


def register_extension(folder, version):
    ext_json = os.path.join(extensions_dir(), "extensions.json")
    data = read_json(ext_json, []) or []
    data = [e for e in data if (e.get("identifier") or {}).get("id") != PACK_ID]
    fs = os.path.abspath(folder)
    data.append(
        {
            "identifier": {"id": PACK_ID},
            "version": version,
            "location": {
                "$mid": 1,
                "fsPath": fs,
                "_sep": 1,
                "external": "file:///" + fs.replace("\\", "/").replace(":", "%3A", 1),
                "path": "/" + fs.replace("\\", "/"),
                "scheme": "file",
            },
            "relativeLocation": os.path.basename(fs),
            "metadata": {
                "isApplicationScoped": True,
                "isMachineScoped": False,
                "isBuiltin": False,
                "installedTimestamp": int(time.time() * 1000),
                "pinned": True,
                "source": "vsix",
            },
        }
    )
    write_json(ext_json, data, indent=2)


def remove_other_packs(keep_folder):
    removed = []
    for folder in list_pack_folders():
        if os.path.abspath(folder) == os.path.abspath(keep_folder):
            continue
        try:
            shutil.rmtree(folder)
            removed.append(folder)
        except Exception as e:
            log("remove pack failed %s: %s" % (folder, e))
    ext_json = os.path.join(extensions_dir(), "extensions.json")
    data = read_json(ext_json, []) or []
    kept = []
    changed = False
    for e in data:
        if (e.get("identifier") or {}).get("id") == PACK_ID and not str(
            e.get("relativeLocation", "")
        ).startswith(os.path.basename(keep_folder)):
            changed = True
            continue
        kept.append(e)
    if changed:
        write_json(ext_json, kept, indent=2)
    return removed


# --------------------------------------------------------------------------- #
# 官方语言包注册表
# --------------------------------------------------------------------------- #


def build_languagepacks(pack):
    locs = pack["localizations"]
    if not locs:
        return None
    loc = locs[0]
    translations = {}
    for t in loc.get("translations", []):
        translations[t["id"]] = os.path.join(pack["folder"], t["path"].replace("/", os.sep))
    md5 = hashlib.md5()
    md5.update((PACK_ID + pack["version"]).encode("utf-8"))
    return {
        loc.get("languageId", LOCALE): {
            "hash": md5.hexdigest(),
            "extensions": [{"extensionIdentifier": {"id": PACK_ID}, "version": pack["version"]}],
            "translations": translations,
            "label": loc.get("localizedLanguageName") or loc.get("languageName") or "中文(简体)",
        }
    }


def write_languagepacks(pack):
    data = build_languagepacks(pack)
    if not data:
        return None
    write_json(languagepacks_path(), data, indent=2)
    return data


# --------------------------------------------------------------------------- #
# 烘焙（补官方语言包因模块改名而漏翻的部分）
# --------------------------------------------------------------------------- #


def load_pack_contents(pack):
    main = os.path.join(pack["folder"], "translations", "main.i18n.json")
    if not os.path.isfile(main):
        return None, "语言包缺少 translations/main.i18n.json"
    try:
        with open(main, "r", encoding="utf-8") as f:
            return (json.load(f) or {}).get("contents") or {}, ""
    except Exception as e:
        return None, "解析 main.i18n.json 失败: %s" % e


def build_module_alias(app_keys, contents):
    """上游 VS Code 与 Cursor 的模块路径有改名，导致官方语言包对不上。
    这里用 key 重合度自动推导别名（不写死映射表），把漏翻的文案补回来。"""
    from collections import Counter

    key_index = {}
    for pm, entry in contents.items():
        if isinstance(entry, dict):
            for k in entry.keys():
                key_index.setdefault(k, []).append(pm)

    alias = {}
    for m, klist in app_keys.items():
        if m in contents or len(klist) < 3:
            continue
        scores = Counter()
        for k in klist:
            for pm in key_index.get(k, ()):
                scores[pm] += 1
        if not scores:
            continue
        pm, ov = scores.most_common(1)[0]
        size = len(contents.get(pm) or {})
        if ov >= max(3, int(len(klist) * 0.6)) and size and ov >= size * 0.6:
            alias[m] = pm
    return alias


def merge_messages(out_dir, contents, base, alias=None):
    keys = read_json(os.path.join(out_dir, "nls.keys.json"), []) or []
    app_keys = {}
    for entry in keys:
        if isinstance(entry, list) and len(entry) >= 2:
            app_keys[entry[0]] = entry[1]
    if alias is None:
        alias = build_module_alias(app_keys, contents)
    merged, idx, zh = [], 0, 0
    for module, klist in app_keys.items():
        mod = contents.get(module)
        if not mod and module in alias:
            mod = contents.get(alias[module]) or {}
        mod = mod or {}
        for k in klist:
            val = mod.get(k)
            if isinstance(val, str) and val:
                merged.append(val)
                zh += 1
            else:
                merged.append(base[idx] if idx < len(base) else None)
            idx += 1
    return merged, zh, alias


def _sha_of_array(arr):
    blob = json.dumps(arr, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def bake_core(install, pack, product):
    out = app_out_dir(install)
    keys_f = os.path.join(out, "nls.keys.json")
    msgs_f = os.path.join(out, "nls.messages.json")
    base_f = os.path.join(out, BASE_FILE_NAME)
    stamp_f = os.path.join(out, STAMP_FILE_NAME)
    if not (os.path.isfile(keys_f) and os.path.isfile(msgs_f)):
        return False, "找不到 nls.keys.json / nls.messages.json"

    stamp = read_json(stamp_f, {}) or {}
    cur = read_json(msgs_f, []) or []
    cur_sha = _sha_of_array(cur)
    is_our_output = bool(stamp.get("mergedSha256")) and stamp["mergedSha256"] == cur_sha
    same_build = stamp.get("commit") == product["commit"]

    if os.path.isfile(base_f) and (is_our_output or same_build):
        base = read_json(base_f, []) or []
    else:
        base = cur
        write_json(base_f, base)

    contents, err = load_pack_contents(pack)
    if contents is None:
        return False, err

    merged, zh, alias = merge_messages(out, contents, base)
    try:
        os.makedirs(TOOL_DIR, exist_ok=True)
        write_json(os.path.join(TOOL_DIR, "nls.messages.en-base.json"), base)
    except Exception:
        pass
    write_json(msgs_f, merged)
    write_json(
        stamp_f,
        {
            "cursorVersion": product["version"],
            "commit": product["commit"],
            "vscodeVersion": product["vscodeVersion"],
            "packVersion": pack["version"],
            "packEngines": pack["engines"],
            "appliedAt": datetime.now().isoformat(timespec="seconds"),
            "totalKeys": len(merged),
            "zhKeys": zh,
            "aliasModules": len(alias),
            "mergedSha256": _sha_of_array(merged),
            "baseSha256": _sha_of_array(base),
        },
        indent=2,
    )
    return True, "共 %d 条文案，其中 %d 条已汉化（模块别名补回 %d 个）" % (len(merged), zh, len(alias))


def bake_extensions(install, pack):
    ext_root = os.path.join(install, "resources", "app", "extensions")
    if not os.path.isdir(ext_root):
        return 0, []
    written = []
    for name in sorted(os.listdir(ext_root)):
        ext_dir = os.path.join(ext_root, name)
        if not os.path.isdir(ext_dir):
            continue
        if not os.path.isfile(os.path.join(ext_dir, "package.nls.json")):
            continue
        src = os.path.join(pack["folder"], "translations", "extensions", "vscode.%s.i18n.json" % name)
        if not os.path.isfile(src):
            continue
        try:
            with open(src, "r", encoding="utf-8") as f:
                pkg = (json.load(f) or {}).get("contents", {}).get("package")
        except Exception:
            continue
        if not isinstance(pkg, dict) or not pkg:
            continue
        dest = os.path.join(ext_dir, "package.nls.zh-cn.json")
        try:
            write_json(dest, pkg)
            written.append(dest)
        except Exception as e:
            log("bake ext failed %s: %s" % (dest, e))
    return len(written), written


# --------------------------------------------------------------------------- #
# clp 语言包缓存
# --------------------------------------------------------------------------- #


def ensure_clp_cache(install, pack, product):
    lp = read_json(languagepacks_path(), {}) or {}
    ent = lp.get(LOCALE) or {}
    pack_hash = ent.get("hash")
    if not pack_hash:
        return False, "languagepacks.json 缺少 hash"
    translations = ent.get("translations") or {}
    clp_root = os.path.join(user_data_dir(), "clp")
    holder = os.path.join(clp_root, "%s.%s" % (pack_hash, LOCALE))
    target = os.path.join(holder, product["commit"])
    os.makedirs(target, exist_ok=True)

    contents, err = load_pack_contents(pack)
    if contents is None:
        return False, err
    out = app_out_dir(install)
    stamp = read_json(os.path.join(out, STAMP_FILE_NAME), {}) or {}
    base = read_json(os.path.join(out, BASE_FILE_NAME), None)
    if not (isinstance(base, list) and base):
        base = read_json(os.path.join(out, "nls.messages.json"), []) or []
    elif stamp.get("baseSha256") and stamp["baseSha256"] != _sha_of_array(base):
        base = read_json(os.path.join(out, "nls.messages.json"), []) or []
    merged, zh, _a = merge_messages(out, contents, base)
    write_json(os.path.join(target, "nls.messages.json"), merged)
    write_json(os.path.join(holder, "tcf.json"), translations)

    removed = 0
    if os.path.isdir(clp_root):
        for name in os.listdir(clp_root):
            p = os.path.join(clp_root, name)
            if os.path.abspath(p) == os.path.abspath(holder):
                continue
            try:
                shutil.rmtree(p)
                removed += 1
            except Exception:
                pass
    return True, "已生成中文文案表（%d 条），清理旧缓存 %d 个" % (len(merged), removed)


# --------------------------------------------------------------------------- #
# 第三方汉化组件（下载 / 调用 / 注入校验）
# --------------------------------------------------------------------------- #


def vendor_present():
    return os.path.isfile(VENDOR_TOOL)


def update_vendor_tool():
    """下载最新版汉化组件到 vendor/。"""
    import urllib.request

    tmp = os.path.join(TOOL_DIR, "vendor-dl")
    os.makedirs(tmp, exist_ok=True)
    zipf = os.path.join(tmp, "repo.zip")
    log("GET %s" % UPSTREAM_ZIP)
    try:
        with urllib.request.urlopen(UPSTREAM_ZIP, timeout=120) as r, open(zipf, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:
        return False, "下载失败：%s\n         请检查网络，或手动下载 %s 解压后放到 vendor 目录" % (e, UPSTREAM_HOME)
    try:
        with zipfile.ZipFile(zipf) as z:
            z.extractall(tmp)
    except Exception as e:
        return False, "解压失败：%s" % e
    root = None
    for name in os.listdir(tmp):
        p = os.path.join(tmp, name)
        if os.path.isdir(p) and os.path.isfile(os.path.join(p, "Cursor_Localization_Tool.py")):
            root = p
            break
    if not root:
        return False, "压缩包里没找到汉化组件"
    os.makedirs(VENDOR_DIR, exist_ok=True)
    for name in os.listdir(root):
        s = os.path.join(root, name)
        d = os.path.join(VENDOR_DIR, name)
        if os.path.isdir(s):
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
    shutil.rmtree(tmp, ignore_errors=True)
    return True, "已更新到 %s" % VENDOR_DIR


def workbench_dir(install):
    base = os.path.join(app_out_dir(install), "vs", "code")
    for sub in ("electron-sandbox", "electron-browser"):
        d = os.path.join(base, sub, "workbench")
        if os.path.isdir(d):
            return d
    return None


def injection_status(install):
    d = workbench_dir(install)
    if not d:
        return {"dir": None, "injected": False, "reason": "找不到 workbench 目录"}
    html = os.path.join(d, WORKBENCH_HTML_NAME)
    js = os.path.join(d, INJECT_JS_NAME)
    injected = False
    if os.path.isfile(html):
        try:
            with open(html, "r", encoding="utf-8", errors="replace") as f:
                injected = INJECT_JS_NAME in f.read()
        except Exception:
            injected = False
    return {
        "dir": d,
        "html": html,
        "js": js,
        "js_exists": os.path.isfile(js),
        "injected": injected,
        "backup": html + ".bak" if os.path.isfile(html + ".bak") else None,
    }


def run_vendor_tool(args, install):
    if not vendor_present():
        return False, "汉化组件还没下载"
    env = dict(os.environ)
    env["CURSOR_INSTALL_DIR"] = install
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, VENDOR_TOOL] + list(args)
    log("run vendor tool: %s" % " ".join(cmd))
    try:
        p = subprocess.run(
            cmd, cwd=VENDOR_DIR, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    except Exception as e:
        return False, "调用失败：%s" % e
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        if line.strip():
            log("  [tool] " + line)
    if p.returncode != 0:
        return False, "返回码 %d\n%s" % (p.returncode, out[-2000:])
    return True, out


def ensure_injection(install):
    """跑完组件后校验注入是否真的生效。

    坑：组件用 HTML 注释标记判断"是否已注入"。若标记在但 <script> 标签没了
    （例如被手工改坏），组件会认为无需注入而直接跳过 -> 界面悄悄退回英文。
    这里做二次校验，不一致就恢复 .bak 再跑一次。
    """
    st = injection_status(install)
    if st.get("injected") and st.get("js_exists"):
        return True, "汉化脚本注入正常"
    bak = st.get("backup")
    if not bak or not os.path.isfile(bak):
        return False, "汉化脚本缺失，且没有备份可恢复（请运行 tool-update 后重试）"
    log("ensure_injection: 注入异常，恢复备份后重试")
    try:
        shutil.copyfile(bak, st["html"])
    except Exception as e:
        return False, "恢复备份失败：%s" % e
    good, _detail = run_vendor_tool([], install)
    st2 = injection_status(install)
    if good and st2.get("injected") and st2.get("js_exists"):
        return True, "已自动恢复并重新注入"
    return False, "重新注入后仍未生效，详见日志 %s" % LOG_FILE


# --------------------------------------------------------------------------- #
# 主体：一键汉化
# --------------------------------------------------------------------------- #


def preflight():
    print("      Python 版本 : %s" % sys.version.split()[0])
    if os.name == "nt":
        node = shutil.which("node")
        print("      Node.js     : %s" % (node or "未安装（可选，仅用于语法自检）"))
    print("      Cursor 数据 : %s" % user_data_dir())


def apply(quiet=False):
    head("Cursor 汉化工具 v%s" % VERSION)

    step(1, 5, "检查运行环境")
    preflight()

    step(2, 5, "查找 Cursor")
    install = pick_cursor()
    if not install:
        bad("没找到 Cursor 安装目录")
        print("      请确认 Cursor 已安装，或手动指定：")
        print("        set CURSOR_INSTALL_DIR=D:\\Cursor")
        return 2
    product = read_product(install)
    ok("Cursor %s 已安装于 %s" % (product["version"], install))
    info("内置 VS Code 基线：%s" % product["vscodeVersion"])

    step(3, 5, "准备汉化组件")
    if not vendor_present():
        info("首次运行，正在下载汉化组件…")
        good, msg = update_vendor_tool()
        if not good:
            bad(msg)
            return 2
    ok("汉化组件就绪（%s）" % UPSTREAM_REPO)

    step(4, 5, "执行汉化")
    good_run, detail = run_vendor_tool([], install)
    if good_run:
        ok("官方中文语言包 + 界面词典注入 完成")
    else:
        bad("汉化组件执行失败")
        print("      " + str(detail)[-1500:])
        return 2
    inj_ok, inj_msg = ensure_injection(install)
    (ok if inj_ok else bad)("汉化脚本校验：%s" % inj_msg)

    # 官方链路自检 + 烘焙补漏
    good, packs = find_pack(product["vscodeVersion"])
    if not good:
        for p in packs:
            warn("已装语言包 %s 与当前版本不匹配（需要 %s）" % (p["version"], p["engines"]))
        try:
            vsix, ver = openvsx_download(product["vscodeVersion"], os.path.join(TOOL_DIR, "cache"))
            target = os.path.join(extensions_dir(), "%s-%s" % (PACK_ID, ver))
            extract_vsix(vsix, target)
            pj = read_json(os.path.join(target, "package.json"), {}) or {}
            real_ver = pj.get("version", ver)
            if real_ver != ver:
                new_target = os.path.join(extensions_dir(), "%s-%s" % (PACK_ID, real_ver))
                if os.path.abspath(new_target) != os.path.abspath(target):
                    os.rename(target, new_target)
                    target = new_target
            register_extension(target, real_ver)
            good, packs = find_pack(product["vscodeVersion"])
            if good:
                ok("已安装匹配的中文语言包 %s" % real_ver)
        except Exception as e:
            warn("自动下载语言包失败：%s" % e)
    else:
        ok("中文语言包 %s 版本匹配" % good["version"])

    if good:
        write_languagepacks(good)
        okd, det = bake_core(install, good, product)
        if okd:
            ok("补漏：%s" % det)
        cnt, files = bake_extensions(install, good)
        ok("补漏：%d 个内置扩展文案已汉化" % cnt)
        if files:
            write_json(BAKED_MANIFEST, files, indent=2)

    step(5, 5, "验证结果")
    st = diagnose()
    healthy = True
    if st.get("argv_ok"):
        ok("显示语言 = %s" % LOCALE)
    else:
        warn("argv.json 里没有显示语言设置（一般不影响，可忽略）")
    if st.get("pack_good"):
        ok("中文语言包已就绪")
    else:
        bad("中文语言包缺失")
        healthy = False
    if st.get("languagepacks_ok"):
        ok("语言包注册表正常")
    else:
        bad("语言包注册表异常：%s" % st.get("languagepacks_detail"))
        healthy = False
    if (st.get("injection") or {}).get("injected"):
        ok("汉化脚本已注入")
    else:
        bad("汉化脚本未注入")
        healthy = False
    if st.get("baked"):
        ok("核心文案已补漏：%s" % st["stamp"].get("zhKeys"))
    else:
        warn("核心文案未补漏（不影响主要界面）")

    done(
        "汉化完成" if healthy else "汉化基本完成，但有项目未通过",
        [
            "",
            "  请按下面两步操作才能看到中文：",
            "",
            "  1) 完全退出 Cursor",
            "       注意：点窗口右上角的 X 只是关窗口，程序还在后台跑！",
            "       要点任务栏右下角托盘图标里的 Cursor 图标 -> 右键 -> 退出",
            "",
            "  2) 重新打开 Cursor，界面就是中文了",
            "",
            "  日志：%s" % LOG_FILE,
        ],
    )
    return 0 if healthy else 1


# --------------------------------------------------------------------------- #
# 状态 / 自检
# --------------------------------------------------------------------------- #


def diagnose():
    st = {}
    install = pick_cursor()
    st["install"] = install
    st["all_installs"] = find_cursor()
    if not install:
        st["product"] = None
        return st
    st["product"] = read_product(install)
    p = argv_path()
    st["argv_ok"] = False
    st["argv_detail"] = "argv.json 不存在"
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8-sig") as f:
            txt = f.read()
        m = re.search(r'"locale"\s*:\s*"([^"]*)"', txt)
        st["argv_ok"] = bool(m and m.group(1) == LOCALE)
        st["argv_detail"] = ("locale=%s" % m.group(1)) if m else "未设置 locale"
    st["user_locale_ok"] = False
    uj = os.path.join(user_data_dir(), "User", "locale.json")
    ujd = read_json(uj, {}) or {}
    st["user_locale_ok"] = ujd.get("locale") == LOCALE
    good, packs = find_pack(st["product"]["vscodeVersion"])
    st["pack_good"] = good
    st["packs"] = packs
    lp = read_json(languagepacks_path(), None)
    st["languagepacks"] = lp
    st["languagepacks_ok"] = False
    st["languagepacks_detail"] = "languagepacks.json 缺失"
    if isinstance(lp, dict):
        ent = lp.get(LOCALE)
        if not ent:
            st["languagepacks_detail"] = "没有 %s 条目" % LOCALE
        else:
            missing = [k for k, v in (ent.get("translations") or {}).items() if not os.path.isfile(v)]
            st["languagepacks_ok"] = not missing
            st["languagepacks_detail"] = (
                "OK（%d 条翻译）" % len(ent.get("translations") or {})
                if not missing
                else "路径失效：%s" % ", ".join(missing[:3])
            )
    st["clp_files"] = []
    clp = os.path.join(user_data_dir(), "clp")
    if os.path.isdir(clp):
        for root, _d, files in os.walk(clp):
            for fn in files:
                fp = os.path.join(root, fn)
                st["clp_files"].append((fp, os.path.getsize(fp)))
    out = app_out_dir(install)
    st["baked"] = os.path.isfile(os.path.join(out, STAMP_FILE_NAME))
    st["stamp"] = read_json(os.path.join(out, STAMP_FILE_NAME), {}) or {}
    st["baked_ext_count"] = 0
    ext_root = os.path.join(install, "resources", "app", "extensions")
    if os.path.isdir(ext_root):
        for n in os.listdir(ext_root):
            if os.path.isfile(os.path.join(ext_root, n, "package.nls.zh-cn.json")):
                st["baked_ext_count"] += 1
    st["injection"] = injection_status(install)
    st["vendor_present"] = vendor_present()
    return st


def print_status(st):
    head("Cursor 汉化状态")
    if not st["install"]:
        bad("没找到 Cursor 安装目录")
        return
    pr = st["product"]
    ok("Cursor %s  →  %s" % (pr["version"], st["install"]))
    info("内置 VS Code 基线：%s   commit：%s" % (pr["vscodeVersion"], pr["commit"][:12]))

    print()
    print("  ── 官方中文语言包 ──")
    (ok if st["argv_ok"] else warn)("显示语言设置：%s" % st["argv_detail"])
    (ok if st["user_locale_ok"] else warn)("用户语言设置：%s" % ("zh-cn" if st["user_locale_ok"] else "未设置"))
    if st["pack_good"]:
        ok("语言包 %s（兼容 %s）" % (st["pack_good"]["version"], st["pack_good"]["engines"]))
    else:
        bad("没有版本匹配的语言包")
        for p in st["packs"]:
            warn("已装 %s（需要 %s）" % (p["version"], p["engines"]))
    (ok if st["languagepacks_ok"] else bad)("语言包注册表：%s" % st["languagepacks_detail"])
    for fp, sz in st["clp_files"]:
        ok("文案缓存：%s" % os.path.basename(fp))

    print()
    print("  ── 界面词典注入（Cursor 专有界面）──")
    inj = st["injection"]
    if inj.get("injected") and inj.get("js_exists"):
        ok("已注入：%s" % inj.get("js"))
    else:
        bad("未注入 → 智能体侧栏 / Cursor 设置 / 插件市场会是英文")
    (ok if st["vendor_present"] else bad)("汉化组件：%s" % ("已就绪" if st["vendor_present"] else "未下载"))

    print()
    print("  ── 核心文案补漏 ──")
    if st["baked"]:
        s = st["stamp"]
        if s.get("commit") == pr["commit"]:
            ok("已补漏：%s 条中文（Cursor %s / 语言包 %s）" % (s.get("zhKeys"), s.get("cursorVersion"), s.get("packVersion")))
        else:
            bad("补漏内容已过期（Cursor 升级了），需要重新运行 apply")
    else:
        warn("未补漏（不影响主要界面）")
    ok("内置扩展补漏：%d 个" % st["baked_ext_count"])

    print()
    print("  ── 结论 ──")
    healthy = st["argv_ok"] and bool(st["pack_good"]) and st["languagepacks_ok"] and bool(st["clp_files"])
    injected = bool(inj.get("injected") and inj.get("js_exists"))
    baked_ok = st["baked"] and st["stamp"].get("commit") == pr["commit"]
    if healthy and injected and baked_ok:
        ok("一切正常，中文界面已生效")
    elif healthy and injected:
        warn("主要界面正常，但缺少核心文案补漏（Cursor 更新后建议重跑 apply）")
    elif injected and baked_ok:
        warn("语言包有问题，但界面词典注入 + 补漏仍生效")
    else:
        bad("汉化不完整，请运行：python cursor_han.py")


def selftest():
    st = diagnose()
    print_status(st)
    print()
    print("  自检结论：")
    issues = []
    if not st["pack_good"]:
        issues.append("中文语言包缺失或版本不匹配")
    if not st["languagepacks_ok"]:
        issues.append("语言包注册表异常")
    if not (st["injection"] or {}).get("injected"):
        issues.append("界面词典未注入")
    if issues:
        for i in issues:
            bad(i)
        return 1
    ok("未发现问题")
    return 0


# --------------------------------------------------------------------------- #
# 自动修复（计划任务用）
# --------------------------------------------------------------------------- #


def guard():
    install = pick_cursor()
    if not install:
        log("guard: 未找到 Cursor")
        return 2
    product = read_product(install)
    out = app_out_dir(install)
    stamp = read_json(os.path.join(out, STAMP_FILE_NAME), {}) or {}
    inj = injection_status(install)
    need = []
    if stamp.get("commit") != product["commit"]:
        need.append("Cursor 升级了")
    if not (inj.get("injected") and inj.get("js_exists")):
        need.append("汉化脚本失效")
    if not need:
        log("guard: 无变化，跳过")
        print("cursor-han guard: 无变化，跳过")
        return 0
    log("guard: %s -> 重新汉化" % "; ".join(need))
    print("cursor-han guard: %s -> 重新汉化" % "; ".join(need))
    return apply()


# --------------------------------------------------------------------------- #
# 计划任务
# --------------------------------------------------------------------------- #


def task_cmd_path():
    return os.path.join(TOOL_DIR, "guard.cmd")


def write_guard_cmd():
    body = '@echo off\r\n"%s" "%s" guard >> "%s" 2>&1\r\n' % (
        sys.executable,
        os.path.abspath(__file__),
        LOG_FILE,
    )
    os.makedirs(TOOL_DIR, exist_ok=True)
    with open(task_cmd_path(), "w", encoding="utf-8", newline="") as f:
        f.write(body)
    return task_cmd_path()


def install_task():
    cmd = write_guard_cmd()
    args = [
        "schtasks", "/Create", "/TN", TASK_NAME,
        "/SC", "HOURLY", "/MO", "1",
        "/TR", '"%s"' % cmd, "/F",
    ]
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    print(out)
    if p.returncode == 0:
        log("已注册计划任务 %s" % TASK_NAME)
        print()
        print("  已注册计划任务 '%s'：每小时检查一次，" % TASK_NAME)
        print("  Cursor 一升级或汉化失效就自动重新汉化。")
        return 0
    print("注册失败，可手动执行：")
    print('  schtasks /Create /TN "%s" /SC HOURLY /MO 1 /TR "\\"%s\\"" /F' % (TASK_NAME, cmd))
    return 1


def uninstall_task():
    p = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(((p.stdout or "") + (p.stderr or "")).strip())
    return p.returncode


# --------------------------------------------------------------------------- #
# 还原
# --------------------------------------------------------------------------- #


def restore():
    install = pick_cursor()
    if not install:
        bad("没找到 Cursor 安装目录")
        return 1
    out = app_out_dir(install)
    base_f = os.path.join(out, BASE_FILE_NAME)
    msgs_f = os.path.join(out, "nls.messages.json")
    if os.path.isfile(base_f):
        shutil.copyfile(base_f, msgs_f)
        ok("已还原核心文案为英文")
    else:
        warn("没有英文备份（下次 Cursor 更新会自动还原）")
    files = read_json(BAKED_MANIFEST, []) or []
    n = 0
    for f in files:
        try:
            if os.path.isfile(f):
                os.remove(f)
                n += 1
        except Exception:
            pass
    ok("已移除 %d 个扩展补漏文件" % n)
    for f in (os.path.join(out, STAMP_FILE_NAME),):
        if os.path.isfile(f):
            os.remove(f)
    try:
        os.remove(BAKED_MANIFEST)
    except OSError:
        pass
    good, detail = run_vendor_tool(["--restore"], install)
    if good:
        ok("已还原界面词典注入（官方语言包保留）")
    else:
        warn("界面词典还原失败：%s" % str(detail)[-500:])
    print()
    print("  提示：官方中文语言包仍然保留，所以界面可能还是中文。")
    print("  要彻底变英文：Cursor 设置 -> 扩展 -> 找到 “Chinese (Simplified)” -> 卸载。")
    return 0


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #


HELP = """
Cursor 汉化工具 v%s

用法：
  python cursor_han.py                一键汉化（推荐，第一次用就跑这个）
  python cursor_han.py status         只看当前状态，不做任何修改
  python cursor_han.py selftest       自检：逐项体检并给结论
  python cursor_han.py guard          仅在需要时自动修复（计划任务用）
  python cursor_han.py restore        还原回英文
  python cursor_han.py install-task   注册每小时自动修复的计划任务
  python cursor_han.py uninstall-task 注销计划任务
  python cursor_han.py tool-update    重新下载最新版汉化组件
""" % VERSION


def main(argv):
    cmd = (argv[1].lower() if len(argv) > 1 else "apply")
    try:
        if cmd in ("help", "-h", "--help"):
            print(HELP)
            return 0
        if cmd == "status":
            print_status(diagnose())
            return 0
        if cmd == "selftest":
            return selftest()
        if cmd == "apply":
            return apply()
        if cmd == "guard":
            return guard()
        if cmd == "restore":
            return restore()
        if cmd == "install-task":
            return install_task()
        if cmd == "uninstall-task":
            return uninstall_task()
        if cmd == "tool-update":
            good, msg = update_vendor_tool()
            (ok if good else bad)(msg)
            return 0 if good else 1
        print("未知命令：%s" % cmd)
        print(HELP)
        return 1
    except KeyboardInterrupt:
        print()
        print("已取消")
        return 130
    except Exception as e:
        import traceback

        traceback.print_exc()
        log("ERROR: %s" % e)
        print()
        bad("出错了：%s" % e)
        print("  日志：%s" % LOG_FILE)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
