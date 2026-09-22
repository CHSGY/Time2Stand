"""数据统计模块 — 记录工作/休息数据并生成看板

数据存储为 JSON（与 config.json 同目录），按日期累计：
    工作时长（秒）、完整休息次数、打断次数、番茄模式工作时长
"""

from __future__ import annotations

import json
import logging
import os
import tkinter as tk
from datetime import date, datetime, timedelta
from typing import Any

from config import _get_config_dir

logger = logging.getLogger("SightHabitKeeper")

STATS_FILE_NAME: str = "SightHabitKeeper_stats.json"
_RETENTION_DAYS: int = 90  # 只保留最近 90 天数据


def _get_stats_path() -> str:
    """返回统计文件的完整路径"""
    return os.path.join(_get_config_dir(), STATS_FILE_NAME)


def _empty_day() -> dict[str, int]:
    """返回单日统计的空结构"""
    return {
        "work_seconds": 0,
        "rest_completed": 0,
        "interruptions": 0,
        "pomodoro_work_seconds": 0,
    }


def load_stats() -> dict[str, dict[str, int]]:
    """加载统计数据，损坏或缺失时返回空数据"""
    path = _get_stats_path()
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            days = data.get("days", {})
            if isinstance(days, dict):
                # 补齐缺失字段并丢弃非法条目
                result: dict[str, dict[str, int]] = {}
                for k, v in days.items():
                    if isinstance(v, dict):
                        day = _empty_day()
                        for field in day:
                            if isinstance(v.get(field), int):
                                day[field] = v[field]
                        result[k] = day
                return result
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("统计文件读取失败：%s", e)
    return {}


def save_stats(days: dict[str, dict[str, int]]) -> None:
    """将统计数据写入 JSON 文件，失败时静默忽略（与 config.py 一致）"""
    path = _get_stats_path()
    try:
        os.makedirs(_get_config_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"days": days}, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning("统计文件写入失败：%s", e)


def record_work(seconds: int, mode: str) -> None:
    """记录一段工作时长（秒），mode 为 normal / pomodoro"""
    if seconds <= 0:
        return
    days = load_stats()
    key = date.today().isoformat()
    day = days.setdefault(key, _empty_day())
    day["work_seconds"] += seconds
    if mode == "pomodoro":
        day["pomodoro_work_seconds"] += seconds
    _prune(days)
    save_stats(days)
    logger.info("统计：记录工作 %d 秒（模式 %s）", seconds, mode)


def record_rest_completed() -> None:
    """记录一次完整休息（≥3 分钟确认）"""
    days = load_stats()
    key = date.today().isoformat()
    days.setdefault(key, _empty_day())["rest_completed"] += 1
    _prune(days)
    save_stats(days)


def record_interruption() -> None:
    """记录一次打断（忽略休息提醒 / 手动停止计时）"""
    days = load_stats()
    key = date.today().isoformat()
    days.setdefault(key, _empty_day())["interruptions"] += 1
    _prune(days)
    save_stats(days)


def _prune(days: dict[str, dict[str, int]]) -> None:
    """清理超过保留期的旧数据"""
    cutoff = (date.today() - timedelta(days=_RETENTION_DAYS)).isoformat()
    for k in [k for k in days if k < cutoff]:
        del days[k]


def _sum_range(start: date, end: date, days: dict[str, dict[str, int]]) -> dict[str, int]:
    """汇总 [start, end] 闭区间内各指标"""
    total = _empty_day()
    d = start
    while d <= end:
        day = days.get(d.isoformat())
        if day:
            for field in total:
                total[field] += day.get(field, 0)
        d += timedelta(days=1)
    return total


def get_summary() -> dict[str, dict[str, Any]]:
    """生成看板数据：今日 / 本周（ISO 周）/ 本月 汇总及最近 7 天明细"""
    days = load_stats()
    today = date.today()

    week_start = today - timedelta(days=today.weekday())  # 周一
    month_start = today.replace(day=1)

    week = _sum_range(week_start, today, days)
    month = _sum_range(month_start, today, days)

    recent: list[tuple[str, dict[str, int]]] = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        recent.append((d.isoformat(), days.get(d.isoformat(), _empty_day())))

    return {
        "today": {"date": today.isoformat(), **days.get(today.isoformat(), _empty_day())},
        "week": week,
        "month": month,
        "recent_days": recent,
    }


def _fmt_duration(seconds: int) -> str:
    """将秒数格式化为 X小时Y分"""
    minutes = seconds // 60
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}小时{mins}分"
    return f"{mins}分钟"


def _interruption_rate(day: dict[str, int]) -> str:
    """打断率 = 打断次数 ÷ (完整休息 + 打断)"""
    total = day.get("rest_completed", 0) + day.get("interruptions", 0)
    if total == 0:
        return "—"
    rate = day.get("interruptions", 0) / total
    return f"{rate:.0%}"


def show_dashboard(root: tk.Tk) -> None:
    """弹出统计看板窗口（Toplevel），每次打开时重新计算数据"""
    summary = get_summary()

    try:
        win = tk.Toplevel(root)
    except tk.TclError as e:
        logger.error("创建统计看板失败：%s", e)
        return

    win.title("统计看板")
    win.geometry("360x420")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    tk.Label(win, text="📊 数据统计看板", font=("Arial", 14, "bold")).pack(pady=(12, 6))

    def section(title: str, day: dict[str, Any]) -> None:
        """渲染一个汇总区块"""
        frame = tk.LabelFrame(win, text=title, font=("Arial", 10))
        frame.pack(fill="x", padx=15, pady=6)
        rows = [
            ("工作时长", _fmt_duration(day.get("work_seconds", 0))),
            ("其中番茄模式", _fmt_duration(day.get("pomodoro_work_seconds", 0))),
            ("完整休息", f"{day.get('rest_completed', 0)} 次"),
            ("打断率", _interruption_rate(day)),
        ]
        for name, value in rows:
            row = tk.Frame(frame)
            row.pack(fill="x", padx=10, pady=1)
            tk.Label(row, text=name, font=("Arial", 9), anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Arial", 9, "bold"), anchor="e").pack(side="right")

    today = summary["today"]
    section(f"今日（{today['date']}）", today)
    section("本周", summary["week"])
    section("本月", summary["month"])

    # 最近 7 天简表
    recent_frame = tk.LabelFrame(win, text="最近 7 天工作时长", font=("Arial", 10))
    recent_frame.pack(fill="x", padx=15, pady=6)
    for day_str, day in summary["recent_days"]:
        row = tk.Frame(recent_frame)
        row.pack(fill="x", padx=10, pady=1)
        tk.Label(row, text=day_str[5:], font=("Arial", 8), width=8, anchor="w").pack(side="left")
        tk.Label(
            row, text=_fmt_duration(day.get("work_seconds", 0)),
            font=("Arial", 8), anchor="e",
        ).pack(side="right")

    tk.Button(win, text="关闭", width=10, command=win.destroy).pack(pady=(8, 10))
