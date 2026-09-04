"""LLM 服务配置管理：多套「地址 + Key + 模型」方案的新增 / 保存 / 启用 / 禁用。

背景
----
- 系统默认走 config.py 里的静态配置（.env 的 DEEPSEEK_API_KEY + LLM_BASE_URL + LLM_MODEL）。
- 用户可在界面里新增多套第三方 OpenAI 兼容服务（DeepSeek / 小米 MiMo / 任意自定义），
  保存为方案（profile），随时启用 / 禁用 / 删除，无需重启。

约定
----
- 方案（含明文 Key）持久化到项目根 llm_settings.json —— 已在 .gitignore，严禁入库。
- active_id 记录当前启用的方案；为空表示「使用系统默认」。
- 返回给前端的 profile 一律经 mask_profile() 脱敏（Key 打码），明文只在后端内部流转。
"""
import json
import logging
import random
import threading
import time
from pathlib import Path

_log = logging.getLogger("llm_settings")

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "llm_settings.json"

# 常用 OpenAI 兼容服务商预设（base_url 可随时在界面改成任意自定义值）
# model 不做硬编码：以「获取模型」从服务商拉取的真实列表为准，避免填错。
PRESETS = [
    {"name": "DeepSeek",      "base_url": "https://api.deepseek.com"},
    {"name": "OpenAI",        "base_url": "https://api.openai.com/v1"},
    {"name": "智谱 GLM",       "base_url": "https://open.bigmodel.cn/api/paas/v4"},
    {"name": "通义千问",       "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"name": "Kimi (Moonshot)", "base_url": "https://api.moonshot.cn/v1"},
    {"name": "火山方舟",       "base_url": "https://ark.cn-beijing.volces.com/api/v3"},
    {"name": "小米 MiMo",     "base_url": "https://api.xiaomimimo.com/v1"},
    {"name": "自定义",         "base_url": ""},
]

_lock = threading.Lock()


def load():
    """读取配置文件；不存在 / 损坏时返回空结构。"""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("profiles", [])
            data.setdefault("active_id", None)
            return data
    except FileNotFoundError:
        pass
    except Exception as e:
        _log.warning("读取 %s 失败，按空配置处理: %s", SETTINGS_FILE.name, e)
    return {"profiles": [], "active_id": None}


def save(data):
    """原子写配置（先写临时文件再替换，避免中途崩溃留下半截 JSON）。"""
    data.setdefault("profiles", [])
    data.setdefault("active_id", None)
    tmp = SETTINGS_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(SETTINGS_FILE)


def _new_id():
    return "p_%s%04d" % (time.strftime("%H%M%S"), random.randint(0, 9999))


def _find(profiles, pid):
    for p in profiles:
        if p.get("id") == pid:
            return p
    return None


def upsert(payload):
    """保存方案：带 id 且已存在 → 更新；否则新增。返回 (profile, is_new)。

    payload 可含 api_key='' 或脱敏串（含 *）表示「不改 Key」（仅更新时有效）。
    """
    with _lock:
        data = load()
        profiles = data["profiles"]
        pid = (payload.get("id") or "").strip()
        existing = _find(profiles, pid) if pid else None
        is_new = existing is None

        api_key = (payload.get("api_key") or "").strip()
        if existing is not None and (not api_key or "*" in api_key):
            api_key = existing.get("api_key", "")  # 留空/打码 = 保留原 Key

        if not api_key:
            raise ValueError("请填写 API Key（更新已有方案可留空表示不修改）")

        profile = {
            "id": existing["id"] if existing else _new_id(),
            "name": (payload.get("name") or "").strip() or "未命名方案",
            "base_url": (payload.get("base_url") or "").strip().rstrip("/"),
            "api_key": api_key,
            "model": (payload.get("model") or "").strip(),
            "created_at": existing["created_at"] if existing else time.strftime("%Y-%m-%d %H:%M"),
        }
        if not profile["base_url"] or not profile["model"]:
            raise ValueError("Base URL 与 模型 ID 均不能为空")

        if existing is not None:
            profiles[profiles.index(existing)] = profile
        else:
            profiles.append(profile)
        save(data)
        return profile, is_new


def delete_profile(pid):
    """删除方案。返回是否删掉的是当前启用项（True 表示系统应回落到默认）。"""
    with _lock:
        data = load()
        profiles = data["profiles"]
        was_active = data.get("active_id") == pid
        data["profiles"] = [p for p in profiles if p.get("id") != pid]
        if was_active:
            data["active_id"] = None
        save(data)
        return was_active


def activate(pid):
    """启用某方案并持久化；返回该方案完整数据。找不到则抛 ValueError。"""
    with _lock:
        data = load()
        prof = _find(data["profiles"], pid)
        if prof is None:
            raise ValueError("该方案不存在或已被删除")
        data["active_id"] = pid
        save(data)
        return dict(prof)


def deactivate():
    """禁用自定义，回落到系统默认。"""
    with _lock:
        data = load()
        data["active_id"] = None
        save(data)


def get_active_profile():
    """返回当前启用方案（自动清理指向已删除方案的脏 active_id）。"""
    with _lock:
        data = load()
        pid = data.get("active_id")
        if not pid:
            return None
        prof = _find(data["profiles"], pid)
        if prof is None:
            data["active_id"] = None
            save(data)
            return None
        return dict(prof)


def list_profiles_masked():
    """给前端用的方案列表：Key 一律打码。"""
    data = load()
    return [mask_profile(p) for p in data["profiles"]], data.get("active_id")


def get_profile_by_id(pid):
    """按 id 返回完整方案（含明文 Key），仅后端内部使用。"""
    if not pid:
        return None
    data = load()
    prof = _find(data["profiles"], pid)
    return dict(prof) if prof else None


def mask_key(key):
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def mask_profile(p):
    out = dict(p)
    out["api_key"] = mask_key(p.get("api_key", ""))
    return out


def is_masked_key(s):
    """判断前端回传的 Key 是否为占位打码串（表示用户未改动）。"""
    return bool(s) and "*" in s


# 便于从 config 层引用的统一入口
def get_settings_file():
    return SETTINGS_FILE
