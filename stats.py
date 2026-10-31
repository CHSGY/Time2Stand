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
from i18n import tr
import theme

logger = logging.getLogger("SightHabitKeeper")

STATS_FILE_NAME: str = "SightHabitKeeper_stats.json"
_RETENTION_DAYS: int = 90  # 只保留最近 90 天数据


def _get_stats_path() -> str:
    """返回统计文件的完整路径"""
    return os.path.join(_get_config_dir(), STATS_FILE_NAME)


def get_stats_mtime() -> float | None:
    """统计文件的最后修改时间（不存在返回 None），用于界面缓存失效判断"""
    try:
        return os.path.getmtime(_get_stats_path())
    except OSError:
        return None


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


def get_summary() -> dict[str, Any]:
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
        return tr("duration_hm", h=hours, m=mins)
    return tr("duration_m", m=mins)


def _interruption_rate(day: dict[str, int]) -> str:
    """打断率 = 打断次数 ÷ (完整休息 + 打断)"""
    total = day.get("rest_completed", 0) + day.get("interruptions", 0)
    if total == 0:
        return "—"
    rate = day.get("interruptions", 0) / total
    return f"{rate:.0%}"


def build_dashboard(parent: tk.Misc) -> None:
    """在给定容器内渲染统计看板内容（嵌入主界面选项卡，每次调用重建）"""
    summary = get_summary()

    # 可滚动容器：内容超出可视区时可用滚轮查看
    outer, canvas, content = theme.scrollable(parent, height=396)
    outer.pack(fill="both", expand=True)

    theme.label(
        content, tr("dashboard_heading"),
        font=theme.font(13, "bold"),
    ).pack(pady=(12, 8))

    def section(title: str, day: dict[str, Any]) -> None:
        """渲染一个汇总区块（白色卡片 + 左名右值行）"""
        frame = theme.card(content)
        frame.pack(fill="x", padx=12, pady=6)
        theme.label(
            frame, title,
            font=theme.font(9, "bold"), fg=theme.PRIMARY,
        ).pack(anchor="w", padx=12, pady=(8, 2))
        rows = [
            (tr("row_work"), _fmt_duration(day.get("work_seconds", 0))),
            (tr("row_pomodoro"), _fmt_duration(day.get("pomodoro_work_seconds", 0))),
            (tr("row_rest"), tr("unit_times", n=day.get("rest_completed", 0))),
            (tr("row_rate"), _interruption_rate(day)),
        ]
        for name, value in rows:
            row = tk.Frame(frame, bg=theme.CARD)
            row.pack(fill="x", padx=12, pady=1)
            theme.label(row, name, font=theme.font(9), fg=theme.MUTED).pack(side="left")
            theme.label(
                row, value, font=theme.font(9, "bold"),
            ).pack(side="right")

    today = summary["today"]
    section(tr("section_today", date=today["date"]), today)
    section(tr("section_week"), summary["week"])
    section(tr("section_month"), summary["month"])

    # 最近 7 天简表
    recent_frame = theme.card(content)
    recent_frame.pack(fill="x", padx=12, pady=6)
    theme.label(
        recent_frame, tr("recent7"),
        font=theme.font(9, "bold"), fg=theme.PRIMARY,
    ).pack(anchor="w", padx=12, pady=(8, 2))
    for day_str, day in summary["recent_days"]:
        row = tk.Frame(recent_frame, bg=theme.CARD)
        row.pack(fill="x", padx=12, pady=1)
        theme.label(
            row, day_str[5:], font=theme.font(8), fg=theme.MUTED, width=8,
        ).pack(side="left")
        theme.label(
            row, _fmt_duration(day.get("work_seconds", 0)),
            font=theme.font(8),
        ).pack(side="right")
    # 底部留白，防止卡片贴边
    tk.Frame(content, bg=theme.BG, height=8).pack()

    # 内容构建完成后绑定滚轮（滚动容器 + 递归子控件）
    theme.enable_wheel(canvas, content)
    canvas.update_idletasks()
