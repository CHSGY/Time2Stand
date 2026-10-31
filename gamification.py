"""游戏化模块 — 打卡天数 + 成就徽章

只读消费 stats.py 的统计数据，实时推导打卡与徽章状态：
- 打卡口径：当日存在 ≥1 次完整休息即打卡成功
- 徽章：由累计休息 / 连续打卡 / 累计工作时长推导，无需独立存储
自身仅持久化「新徽章通知已展示」的标记，避免重复弹窗。
"""

from __future__ import annotations

import json
import logging
import os
import tkinter as tk
from datetime import date, timedelta
from typing import Any

import stats
from config import _get_config_dir
from i18n import tr
import theme

logger = logging.getLogger("SightHabitKeeper")

STATE_FILE_NAME: str = "SightHabitKeeper_gamification.json"

# ---------- 徽章定义 ----------

# (id, 图标, 类型, 阈值)；名称与描述按 id 从 i18n 取（badge_<id>_name / _desc）
BADGES: list[dict[str, Any]] = [
    {"id": "rest_1",    "icon": "🌱", "kind": "rest",   "threshold": 1},
    {"id": "rest_10",   "icon": "💧", "kind": "rest",   "threshold": 10},
    {"id": "rest_50",   "icon": "🌊", "kind": "rest",   "threshold": 50},
    {"id": "streak_3",  "icon": "🔥", "kind": "streak", "threshold": 3},
    {"id": "streak_7",  "icon": "⚡", "kind": "streak", "threshold": 7},
    {"id": "streak_30", "icon": "🏔️", "kind": "streak", "threshold": 30},
    {"id": "work_1",    "icon": "⏰", "kind": "work",   "threshold": 3600},
    {"id": "work_10",   "icon": "💪", "kind": "work",   "threshold": 36000},
    {"id": "work_50",   "icon": "👑", "kind": "work",   "threshold": 180000},
]


def badge_name(b: dict[str, Any]) -> str:
    """徽章的本地化名称"""
    return tr(f"badge_{b['id']}_name")


def badge_desc(b: dict[str, Any]) -> str:
    """徽章的本地化描述"""
    return tr(f"badge_{b['id']}_desc")


# ---------- 状态持久化（仅存已展示的新徽章通知标记） ----------

def _get_state_path() -> str:
    return os.path.join(_get_config_dir(), STATE_FILE_NAME)


def _load_notified() -> list[str]:
    """已展示过解锁通知的徽章 id 列表"""
    try:
        if os.path.isfile(_get_state_path()):
            with open(_get_state_path(), "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            notified = data.get("notified_badges", [])
            if isinstance(notified, list):
                return [x for x in notified if isinstance(x, str)]
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("游戏化状态文件读取失败：%s", e)
    return []


def _save_notified(notified: list[str]) -> None:
    try:
        os.makedirs(_get_config_dir(), exist_ok=True)
        with open(_get_state_path(), "w", encoding="utf-8") as f:
            json.dump({"notified_badges": notified}, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning("游戏化状态文件写入失败：%s", e)


# ---------- 打卡与徽章计算（纯函数，便于测试） ----------

def get_checkin_set(days: dict[str, dict[str, int]]) -> set[str]:
    """返回所有已打卡的日期（当日有 ≥1 次完整休息）"""
    return {k for k, v in days.items() if v.get("rest_completed", 0) >= 1}


def get_streak(days: dict[str, dict[str, int]]) -> int:
    """当前连续打卡天数：今天已打卡则从今天回溯，否则从昨天回溯"""
    checked = get_checkin_set(days)
    d = date.today()
    if d.isoformat() not in checked:
        d -= timedelta(days=1)  # 今天还没打卡不打断连击
    streak = 0
    while d.isoformat() in checked:
        streak += 1
        d -= timedelta(days=1)
    return streak


def get_totals(days: dict[str, dict[str, int]]) -> dict[str, int]:
    """全部历史累计：休息次数、工作秒数"""
    total_rest = 0
    total_work = 0
    for v in days.values():
        total_rest += v.get("rest_completed", 0)
        total_work += v.get("work_seconds", 0)
    return {"rest": total_rest, "work": total_work}


def get_unlocked_ids(days: dict[str, dict[str, int]]) -> list[str]:
    """返回已解锁的徽章 id 列表"""
    streak = get_streak(days)
    totals = get_totals(days)
    metrics: dict[str, int] = {
        "rest": totals["rest"],
        "streak": streak,
        "work": totals["work"],
    }
    unlocked: list[str] = []
    for b in BADGES:
        if metrics[b["kind"]] >= b["threshold"]:
            unlocked.append(b["id"])
    return unlocked


# ---------- 成就窗口 ----------

def _fmt_hours(seconds: int) -> str:
    hours = seconds / 3600
    if hours < 1:
        return tr("duration_m", m=seconds // 60)
    return tr("duration_h", h=f"{hours:.1f}")


def show_achievements(root: tk.Tk) -> None:
    """弹出成就窗口：连续打卡 + 徽章墙 + 打卡日历（最近 14 天）"""
    days = stats.load_stats()
    streak = get_streak(days)
    totals = get_totals(days)
    unlocked = set(get_unlocked_ids(days))
    checked = get_checkin_set(days)

    try:
        win = tk.Toplevel(root)
    except tk.TclError as e:
        logger.error("创建成就窗口失败：%s", e)
        return

    win.title(tr("ach_title"))
    win.geometry("380x500")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    theme.setup_window(win)

    theme.label(
        win, tr("ach_heading"),
        font=theme.font(13, "bold"),
    ).pack(pady=(14, 4))

    # 打卡概览（白色卡片：连击大字 + 汇总行）
    overview = theme.card(win)
    overview.pack(fill="x", padx=16, pady=5)
    theme.label(
        overview,
        text=tr("streak_hero", n=streak),
        font=theme.font(22, "bold"), fg=theme.PRIMARY,
    ).pack(pady=(10, 0))
    theme.label(
        overview,
        text=tr(
            "ach_overview",
            streak=streak,
            rest=totals["rest"],
            work=_fmt_hours(totals["work"]),
        ),
        font=theme.font(9), fg=theme.MUTED,
    ).pack(pady=(0, 10))

    # 打卡日历（最近 14 天，今天的排在最右）
    cal_frame = theme.card(win)
    cal_frame.pack(fill="x", padx=16, pady=5)
    theme.label(
        cal_frame, tr("cal_frame"),
        font=theme.font(9, "bold"), fg=theme.PRIMARY,
    ).pack(anchor="w", padx=12, pady=(8, 0))
    cal_row = tk.Frame(cal_frame, bg=theme.CARD)
    cal_row.pack(pady=4)
    today = date.today()
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        mark = "✅" if d.isoformat() in checked else "·"
        theme.label(
            cal_row, text=mark, font=theme.font(11),
            fg=theme.PRIMARY if d.isoformat() in checked else "#cccccc",
        ).pack(side="left", expand=True)
    theme.label(
        cal_frame, tr("cal_legend"),
        font=theme.font(8), fg=theme.MUTED,
    ).pack(pady=(0, 6))

    # 徽章墙
    wall = theme.card(win)
    wall.pack(fill="both", expand=True, padx=16, pady=5)
    theme.label(
        wall, tr("badge_wall"),
        font=theme.font(9, "bold"), fg=theme.PRIMARY,
    ).pack(anchor="w", padx=12, pady=(8, 2))
    for b in BADGES:
        row = tk.Frame(wall, bg=theme.CARD)
        row.pack(fill="x", padx=12, pady=2)
        is_unlocked = b["id"] in unlocked
        icon = b["icon"] if is_unlocked else "🔒"
        name_color = theme.INK if is_unlocked else "#b5bfc0"
        theme.label(row, icon, font=theme.font(13)).pack(side="left", padx=(0, 6))
        theme.label(
            row, badge_name(b), font=theme.font(10, "bold"),
            fg=name_color, width=10, anchor="w",
        ).pack(side="left")
        theme.label(
            row,
            badge_desc(b) if is_unlocked else tr("badge_locked", desc=badge_desc(b)),
            font=theme.font(8),
            fg=theme.MUTED if is_unlocked else "#c9d2d3",
        ).pack(side="left", padx=(0, 4))
        if is_unlocked:
            theme.label(
                row, tr("badge_unlocked"),
                font=theme.font(8, "bold"), fg=theme.PRIMARY,
            ).pack(side="right")

    close_btn = tk.Button(win, text=tr("close_btn"), width=11, command=win.destroy)
    theme.style_button(close_btn, "subtle")
    close_btn.pack(pady=(8, 12))


# ---------- 新徽章通知 ----------

def check_and_notify(root: tk.Tk) -> None:
    """检查是否有未展示过的新解锁徽章，若有则弹轻量提示。

    在主程序完成一次休息后调用（Tk 主线程）。
    """
    try:
        days = stats.load_stats()
        unlocked = get_unlocked_ids(days)
        notified = _load_notified()
        fresh = [b for b in BADGES if b["id"] in unlocked and b["id"] not in notified]
        if not fresh:
            return

        text = "  ".join(f"{b['icon']} {badge_name(b)}" for b in fresh)
        _save_notified(notified + [b["id"] for b in fresh])
        logger.info("解锁新徽章：%s", "、".join(badge_name(b) for b in fresh))

        try:
            toast = tk.Toplevel(root)
        except tk.TclError:
            return
        toast.title(tr("toast_title"))
        toast.geometry("340x120")
        toast.resizable(False, False)
        toast.attributes("-topmost", True)
        theme.setup_window(toast)
        theme.label(
            toast, tr("toast_heading"),
            font=theme.font(11, "bold"), fg=theme.PRIMARY,
        ).pack(pady=(18, 4))
        theme.label(toast, text, font=theme.font(11)).pack()
        toast.after(4000, toast.destroy)
    except Exception as e:  # 游戏化属于附加功能，任何异常不影响主流程
        logger.warning("成就通知检查失败：%s", e)
