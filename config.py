"""配置管理模块 — 持久化用户偏好设置"""

from __future__ import annotations

import json
import os
import platform
from typing import Any

CONFIG_FILE_NAME: str = "SightHabitKeeper_config.json"


def _get_config_dir() -> str:
    """获取跨平台配置文件目录"""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif system == "Darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get(
            "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
        )
    return os.path.join(base, "SightHabitKeeper")


def _get_config_path() -> str:
    """返回配置文件的完整路径"""
    return os.path.join(_get_config_dir(), CONFIG_FILE_NAME)


def load_config() -> dict[str, Any]:
    """从 JSON 文件加载配置，不存在则返回默认值"""
    path = _get_config_path()
    defaults: dict[str, Any] = {"countdown_minutes": 30}
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
                for k, v in defaults.items():
                    data.setdefault(k, v)
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return dict(defaults)


def save_config(config: dict[str, Any]) -> None:
    """将配置写入 JSON 文件"""
    path = _get_config_path()
    try:
        os.makedirs(_get_config_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # 写入失败时静默忽略