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

logger = logging.getLogger("SightHabitKeeper")

STATE_FILE_NAME: str = "SightHabitKeeper_gamification.json"

# ---------- 徽章定义 ----------

# (id, 图标, 名称, 类型, 阈值, 描述)
BADGES: list[dict[str, Any]] = [
    {"id": "rest_1",   "icon": "🌱", "name": "第一滴汗水", "kind": "rest",  "threshold": 1,     "desc": "完成 1 次完整休息"},
    {"id": "rest_10",  "icon": "💧", "name": "润物无声",   "kind": "rest",  "threshold": 10,    "desc": "完成 10 次完整休息"},
    {"id": "rest_50",  "icon": "🌊", "name": "休息达人",   "kind": "rest",  "threshold": 50,    "desc": "完成 50 次完整休息"},
    {"id": "streak_3", "icon": "🔥", "name": "三日之约",   "kind": "streak", "threshold": 3,    "desc": "连续打卡 3 天"},
    {"id": "streak_7", "icon": "⚡", "name": "七日连续",   "kind": "streak", "threshold": 7,    "desc": "连续打卡 7 天"},
    {"id": "streak_30","icon": "🏔️", "name": "三十日如一", "kind": "streak", "threshold": 30,   "desc": "连续打卡 30 天"},
    {"id": "work_1",   "icon": "⏰", "name": "初露锋芒",   "kind": "work",  "threshold": 3600,   "desc": "累计工作 1 小时"},
    {"id": "work_10",  "icon": "💪", "name": "久坐克星",   "kind": "work",  "threshold": 36000,  "desc": "累计工作 10 小时"},
    {"id": "work_50",  "icon": "👑", "name": "时间主宰",   "kind": "work",  "threshold": 180000, "desc": "累计工作 50 小时"},
]


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
        return f"{seconds // 60}分钟"
    return f"{hours:.1f}小时"


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

    win.title("我的成就")
    win.geometry("380x480")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    tk.Label(win, text="🏆 我的成就", font=("Arial", 14, "bold")).pack(pady=(12, 4))

    # 打卡概览
    overview = tk.Frame(win)
    overview.pack(pady=2)
    tk.Label(
        overview,
        text=f"🔥 连续打卡 {streak} 天    🌿 累计休息 {totals['rest']} 次    ⏱️ 累计工作 {_fmt_hours(totals['work'])}",
        font=("Arial", 10),
    ).pack()

    # 打卡日历（最近 14 天，今天的排在最右）
    cal_frame = tk.LabelFrame(win, text="最近 14 天打卡", font=("Arial", 10))
    cal_frame.pack(fill="x", padx=15, pady=6)
    cal_row = tk.Frame(cal_frame)
    cal_row.pack(pady=4)
    today = date.today()
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        mark = "✅" if d.isoformat() in checked else "·"
        tk.Label(
            cal_row, text=mark, font=("Arial", 11),
            fg="green" if d.isoformat() in checked else "#bbbbbb",
        ).pack(side="left", expand=True)
    tk.Label(cal_frame, text="✅ 已打卡（当日完成过完整休息）", font=("Arial", 8), fg="#888888").pack(pady=(0, 4))

    # 徽章墙
    wall = tk.LabelFrame(win, text="成就徽章", font=("Arial", 10))
    wall.pack(fill="both", expand=True, padx=15, pady=6)
    for b in BADGES:
        row = tk.Frame(wall)
        row.pack(fill="x", padx=10, pady=2)
        is_unlocked = b["id"] in unlocked
        icon = b["icon"] if is_unlocked else "🔒"
        name_color = "#222222" if is_unlocked else "#aaaaaa"
        tk.Label(row, text=icon, font=("Arial", 13)).pack(side="left", padx=(0, 6))
        tk.Label(
            row, text=b["name"], font=("Arial", 10, "bold"),
            fg=name_color, width=10, anchor="w",
        ).pack(side="left")
        tk.Label(
            row,
            text=b["desc"] if is_unlocked else f"未解锁 · {b['desc']}",
            font=("Arial", 8),
            fg="#888888" if is_unlocked else "#cccccc",
        ).pack(side="left", padx=(0, 4))
        if is_unlocked:
            tk.Label(row, text="已解锁", font=("Arial", 8, "bold"), fg="green").pack(side="right")

    tk.Button(win, text="关闭", width=10, command=win.destroy).pack(pady=(6, 10))


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

        text = "  ".join(f"{b['icon']} {b['name']}" for b in fresh)
        _save_notified(notified + [b["id"] for b in fresh])
        logger.info("解锁新徽章：%s", "、".join(b["name"] for b in fresh))

        try:
            toast = tk.Toplevel(root)
        except tk.TclError:
            return
        toast.title("成就解锁")
        toast.geometry("320x120")
        toast.resizable(False, False)
        toast.attributes("-topmost", True)
        tk.Label(toast, text="🎉 解锁新成就！", font=("Arial", 12, "bold")).pack(pady=(18, 4))
        tk.Label(toast, text=text, font=("Arial", 11)).pack()
        toast.after(4000, toast.destroy)
    except Exception as e:  # 游戏化属于附加功能，任何异常不影响主流程
        logger.warning("成就通知检查失败：%s", e)
