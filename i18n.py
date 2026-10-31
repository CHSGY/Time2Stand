"""多语言支持模块 — 中/英文界面切换（v2.0）

用法：
    import i18n
    i18n.set_language("en")        # 启动时根据配置设置
    text = i18n.tr("start_btn")    # 取当前语言的字符串
    text = i18n.tr("work_remaining", time="25:00")  # 带参数格式化

语言在主窗口切换后立即生效于主界面；休息对话框、看板、成就窗口
在各自创建时读取当前语言，因此随后打开的窗口即为新语言。
"""

from __future__ import annotations

import logging

logger = logging.getLogger("SightHabitKeeper")

LANGUAGES: tuple[str, ...] = ("zh", "en")

_STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        # 主窗口
        "app_title": "久坐提醒器",
        "current_time": "当前时间：{time}",
        "ready": "准备启动",
        "mode": "模式：",
        "mode_normal": "普通模式",
        "mode_pomodoro": "番茄模式",
        "countdown_label": "倒计时（分钟）：",
        "work_label": "工作时长（分钟）：",
        "start_btn": "开始计时",
        "stop_btn": "停止计时",
        "dashboard_btn": "📊 统计看板",
        "achievements_btn": "🏆 我的成就",
        "tab_home": "🏠 主界面",
        "language": "语言：",
        # 系统托盘
        "tray_show": "显示窗口",
        "tray_hide": "隐藏到托盘",
        "tray_quit": "退出",
        "tray_minimized": "久坐提醒器已最小化到系统托盘",
        # 计时状态
        "stopped": "已停止",
        "idle_paused": "检测到用户离开，计时暂停",
        "work_remaining": "工作中（剩余{time}）",
        "time_up": "时间到！请起身活动",
        "pomodoro_done": "🎉 完成第{n}个番茄钟！休息{m}分钟",
        "pomodoro_start": "🍅 开始第{n}个番茄钟！",
        # 休息对话框
        "rest_title": "休息提醒",
        "rest_title_pomodoro": "🍅 休息时间 — 第{n}个番茄钟完成！",
        "rest_title_long": "🎉 长休息 — 第{n}个番茄钟完成！",
        "rest_msg_pomodoro": "休息{m}分钟，放松一下~",
        "rest_msg_normal": "您已连续工作{m}分钟，请离开座位！",
        "rest_countdown": "还需休息 {time}",
        "rest_done": "休息时间到，可以继续工作了！",
        "rest_confirm_btn": "确认重新开始",
        "rest_ignore_btn": "忽略",
        # 消息框
        "warn_invalid_title": "输入错误",
        "warn_invalid_msg": "请输入有效的分钟数（正数）",
        "warn_rest_title": "休息不足",
        "warn_rest_msg": "至少休息3分钟才可以继续工作哦~",
        "rest_too_soon": "休息时间未到，再坚持一下~",
        "error_dialog_title": "错误",
        "error_dialog_msg": "无法创建休息提醒窗口，请稍后重试",
        # 统计看板
        "dashboard_title": "统计看板",
        "dashboard_heading": "📊 数据统计看板",
        "section_today": "今日（{date}）",
        "section_week": "本周",
        "section_month": "本月",
        "row_work": "工作时长",
        "row_pomodoro": "其中番茄模式",
        "row_rest": "完整休息",
        "row_rate": "打断率",
        "recent7": "最近 7 天工作时长",
        "unit_times": "{n} 次",
        "close_btn": "关闭",
        # 时长格式化
        "duration_hm": "{h}小时{m}分",
        "duration_m": "{m}分钟",
        "duration_h": "{h}小时",
        # 成就系统
        "ach_title": "我的成就",
        "ach_heading": "🏆 我的成就",
        "ach_overview": "🔥 连续打卡 {streak} 天    🌿 累计休息 {rest} 次    ⏱️ 累计工作 {work}",
        "streak_hero": "连续打卡 {n} 天",
        "cal_frame": "最近 14 天打卡",
        "cal_legend": "✅ 已打卡（当日完成过完整休息）",
        "badge_wall": "成就徽章",
        "badge_locked": "未解锁 · {desc}",
        "badge_unlocked": "已解锁",
        "toast_title": "成就解锁",
        "toast_heading": "🎉 解锁新成就！",
        # 徽章名称
        "badge_rest_1_name": "第一滴汗水",
        "badge_rest_10_name": "润物无声",
        "badge_rest_50_name": "休息达人",
        "badge_streak_3_name": "三日之约",
        "badge_streak_7_name": "七日连续",
        "badge_streak_30_name": "三十日如一",
        "badge_work_1_name": "初露锋芒",
        "badge_work_10_name": "久坐克星",
        "badge_work_50_name": "时间主宰",
        # 徽章描述
        "badge_rest_1_desc": "完成 1 次完整休息",
        "badge_rest_10_desc": "完成 10 次完整休息",
        "badge_rest_50_desc": "完成 50 次完整休息",
        "badge_streak_3_desc": "连续打卡 3 天",
        "badge_streak_7_desc": "连续打卡 7 天",
        "badge_streak_30_desc": "连续打卡 30 天",
        "badge_work_1_desc": "累计工作 1 小时",
        "badge_work_10_desc": "累计工作 10 小时",
        "badge_work_50_desc": "累计工作 50 小时",
    },
    "en": {
        "app_title": "Sit-Less Reminder",
        "current_time": "Time: {time}",
        "ready": "Ready",
        "mode": "Mode:",
        "mode_normal": "Normal",
        "mode_pomodoro": "Pomodoro",
        "countdown_label": "Countdown (minutes):",
        "work_label": "Work duration (minutes):",
        "start_btn": "Start",
        "stop_btn": "Stop",
        "dashboard_btn": "📊 Dashboard",
        "achievements_btn": "🏆 Achievements",
        "tab_home": "🏠 Home",
        "language": "Language:",
        "tray_show": "Show Window",
        "tray_hide": "Hide to Tray",
        "tray_quit": "Quit",
        "tray_minimized": "Sit-Less Reminder minimized to tray",
        "stopped": "Stopped",
        "idle_paused": "User away — timer paused",
        "work_remaining": "Working ({time} left)",
        "time_up": "Time's up! Please stand up",
        "pomodoro_done": "🎉 Pomodoro #{n} done! Rest {m} min",
        "pomodoro_start": "🍅 Starting pomodoro #{n}!",
        "rest_title": "Rest Reminder",
        "rest_title_pomodoro": "🍅 Break time — Pomodoro #{n} done!",
        "rest_title_long": "🎉 Long break — Pomodoro #{n} done!",
        "rest_msg_pomodoro": "Take a {m}-minute break, relax~",
        "rest_msg_normal": "You've worked {m} minutes straight — please leave your seat!",
        "rest_countdown": "Rest {time} left",
        "rest_done": "Break over, you can get back to work!",
        "rest_confirm_btn": "Resume Work",
        "rest_ignore_btn": "Ignore",
        "warn_invalid_title": "Invalid Input",
        "warn_invalid_msg": "Please enter a valid number of minutes (positive)",
        "warn_rest_title": "Rest Too Short",
        "warn_rest_msg": "Please rest at least 3 minutes before continuing~",
        "rest_too_soon": "Rest time isn't over yet — hang in there~",
        "error_dialog_title": "Error",
        "error_dialog_msg": "Failed to create the rest dialog. Please try again later.",
        "dashboard_title": "Dashboard",
        "dashboard_heading": "📊 Statistics Dashboard",
        "section_today": "Today ({date})",
        "section_week": "This Week",
        "section_month": "This Month",
        "row_work": "Work time",
        "row_pomodoro": "Pomodoro mode",
        "row_rest": "Full breaks",
        "row_rate": "Interruption rate",
        "recent7": "Work time — last 7 days",
        "unit_times": "{n}",
        "close_btn": "Close",
        "duration_hm": "{h}h {m}m",
        "duration_m": "{m} min",
        "duration_h": "{h}h",
        "ach_title": "My Achievements",
        "ach_heading": "🏆 My Achievements",
        "ach_overview": "🔥 Streak {streak} days    🌿 Rests {rest}    ⏱️ Worked {work}",
        "streak_hero": "{n}-day streak",
        "cal_frame": "Last 14 days",
        "cal_legend": "✅ Checked in (≥1 full break that day)",
        "badge_wall": "Badges",
        "badge_locked": "Locked · {desc}",
        "badge_unlocked": "Unlocked",
        "toast_title": "Achievement Unlocked",
        "toast_heading": "🎉 New achievement!",
        "badge_rest_1_name": "First Drop of Sweat",
        "badge_rest_10_name": "Silent Nourisher",
        "badge_rest_50_name": "Rest Master",
        "badge_streak_3_name": "Three-Day Pact",
        "badge_streak_7_name": "Seven-Day Streak",
        "badge_streak_30_name": "Thirty Days Strong",
        "badge_work_1_name": "First Steps",
        "badge_work_10_name": "Sedentary Slayer",
        "badge_work_50_name": "Time Master",
        "badge_rest_1_desc": "Complete 1 full break",
        "badge_rest_10_desc": "Complete 10 full breaks",
        "badge_rest_50_desc": "Complete 50 full breaks",
        "badge_streak_3_desc": "3-day check-in streak",
        "badge_streak_7_desc": "7-day check-in streak",
        "badge_streak_30_desc": "30-day check-in streak",
        "badge_work_1_desc": "1 hour of work total",
        "badge_work_10_desc": "10 hours of work total",
        "badge_work_50_desc": "50 hours of work total",
    },
}

import logging

logger = logging.getLogger("SightHabitKeeper")

# 当前语言（默认中文；主程序启动时按配置调用 set_language）
_current: str = "zh"


def set_language(lang: str) -> str:
    """设置当前语言，非法值时保持不变并告警。返回实际生效的语言。"""
    global _current
    if lang in LANGUAGES:
        _current = lang
    else:
        logger.warning("未知语言 %r，保持 %s", lang, _current)
    return _current


def get_language() -> str:
    """返回当前语言代码（zh / en）"""
    return _current


def tr(key: str, **kwargs: object) -> str:
    """按当前语言取字符串；缺失 key 时回退中文，再缺失则返回 key 本身"""
    text = _STRINGS.get(_current, {}).get(key)
    if text is None:
        text = _STRINGS["zh"].get(key, key)
        logger.warning("缺少翻译 key：%s（语言 %s）", key, _current)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError) as e:
            logger.warning("格式化失败 key=%s：%s", key, e)
    return text
