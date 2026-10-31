from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from typing import Any
import winsound
import random
import ctypes
import ctypes.wintypes
import threading

import pystray
from PIL import Image, ImageDraw

from config import load_config, save_config
import i18n
import stats
import gamification
from i18n import tr
import theme

# 语言下拉框显示文案 ↔ 语言代码
_LANG_DISPLAY: dict[str, str] = {"zh": "中文", "en": "English"}

# ---------- 日志配置 ----------

logger = logging.getLogger("SightHabitKeeper")

# ---------- 健康小贴士库 ----------

HEALTH_TIPS: list[str] = [
    # 护眼类
    "👁️ 闭眼休息10秒，能有效缓解眼部疲劳",
    "👁️ 每20分钟看6米外远处20秒（20-20-20法则）",
    "👁️ 快速眨眼10次，帮助泪液均匀分布",
    "👁️ 远眺窗外绿色植物，放松睫状肌",
    "👁️ 热敷双眼5分钟，促进眼周血液循环",
    # 颈椎类
    "🧘 缓慢左右转动颈部各5次，缓解颈椎压力",
    "🧘 下巴画「米」字，活动颈椎各个方向",
    "🧘 双手抱头后仰，拉伸颈前肌群",
    "🧘 耸肩+放松重复10次，释放肩颈紧张",
    # 腰椎/背部类
    "💪 站起来向后弯腰3次，拉伸腰部",
    "💪 坐姿背部挺直，双肩后展，保持30秒",
    "💪 双手在背后交握，扩胸拉伸",
    "💪 左右侧身拉伸各15秒，活动腰方肌",
    "💪 站姿体前屈，手指够脚尖，拉伸后腰",
    # 手腕/手臂类
    "🤲 手腕上下弯曲各10次，预防鼠标手",
    "🤲 双手握拳再张开，促进手部血液循环",
    "🤲 手臂向前伸直，手指向上/下弯曲各10秒",
    # 全身活动类
    "🏃 站起来走动2分钟，促进血液循环",
    "🏃 原地踏步30次，唤醒身体活力",
    "🏃 上下楼梯一趟（如有），效果更佳",
    # 饮水/健康类
    "💧 喝一杯温水，补充水分促进代谢",
    "💧 每小时饮水150-200ml，保持身体水分平衡",
    "🧠 深呼吸3次：吸气4秒→屏息4秒→呼气6秒",
    "🧠 晒太阳5分钟，补充维生素D，提升情绪",
    "🧠 站起来伸个懒腰，全身舒展",
]

# ---------- 空闲检测工具函数 ----------


class LASTINPUTINFO(ctypes.Structure):
    """Windows LASTINPUTINFO 结构体"""
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("dwTime", ctypes.wintypes.DWORD),
    ]


def get_idle_seconds() -> int:
    """通过 Windows API 获取用户空闲秒数（仅 Windows）"""
    last_input_info = LASTINPUTINFO()
    last_input_info.cbSize = ctypes.sizeof(last_input_info)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input_info)):
        tick_now = ctypes.wintypes.DWORD(ctypes.windll.kernel32.GetTickCount())
        return int((tick_now.value - last_input_info.dwTime) / 1000)
    return 0


# ---------- 托盘图标图像 ----------


def _create_tray_image() -> Image.Image:
    """创建一个 64x64 的托盘图标图像"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 画一个绿色的圆形
    draw.ellipse([4, 4, 60, 60], fill=(76, 175, 80, 255))
    # 画一个白色的"P"字母（简单示意）
    draw.rectangle([24, 16, 28, 48], fill=(255, 255, 255, 255))
    draw.arc([24, 16, 42, 36], -90, 90, fill=(255, 255, 255, 255), width=4)
    return img


class StandUpApp:
    """主应用程序类，使用Tkinter实现非线程化定时功能"""

    # 类型注解：实例变量
    root: tk.Tk
    time_label: tk.Label
    status_label: tk.Label
    settings_frame: tk.Frame
    settings_label: tk.Label
    minutes_var: tk.StringVar
    minutes_entry: tk.Entry
    btn_frame: tk.Frame
    start_btn: tk.Button
    stop_btn: tk.Button
    timer_running: bool
    timer_id: str | None
    start_time: datetime | None
    rest_start_time: datetime | None
    rest_window: tk.Toplevel | None
    _config: dict[str, Any]
    countdown_seconds: int
    rest_countdown_label: tk.Label | None
    rest_confirm_btn: tk.Button | None
    # 系统托盘
    _tray_icon: pystray.Icon | None
    _tray_thread: threading.Thread | None
    # 空闲检测
    _idle_check_id: str | None
    # 休息对话框
    _break_seconds: int
    # 統计/成就入口按钮
    stats_btn: tk.Button
    achievements_btn: tk.Button
    # 番茄工作法
    _mode: str
    _mode_menu: tk.OptionMenu
    # 语言切换
    _lang_var: tk.StringVar
    _lang_menu: tk.OptionMenu
    _mode_var: tk.StringVar
    _pomodoro_cycle: int
    _is_pomodoro_break: bool
    _pomodoro_long_break: bool

    def __init__(self, root: tk.Tk) -> None:
        """初始化GUI界面组件"""
        self.root = root
        # 加载配置并应用语言（必须先于任何界面文本创建）
        self._config = load_config()
        i18n.set_language(str(self._config.get("language", "zh")))

        root.title(tr("app_title"))
        root.geometry("320x360")
        root.resizable(False, False)
        theme.setup_window(root)

        # ---------- 顶部：弱化的时钟 ----------
        self.time_label = tk.Label(
            root, text=tr("current_time", time=""),
            font=theme.font(9), fg=theme.MUTED,
        )
        self.time_label.pack(pady=(14, 2))

        # ---------- hero：状态/倒计时大字 ----------
        self.status_label = tk.Label(
            root, text=tr("ready"),
            font=theme.font(17, "bold"), fg=theme.MUTED,
        )
        self.status_label.pack(pady=(2, 10))

        # ---------- 模式选择 ----------
        mode_frame = tk.Frame(root, bg=theme.BG)
        mode_frame.pack(pady=3, fill='x', padx=40)
        theme.label(mode_frame, tr("mode"), font=theme.font(9), fg=theme.MUTED).pack(side='left')
        self._mode = "normal"  # 内部模式值：normal / pomodoro
        self._mode_var = tk.StringVar(value=tr("mode_normal"))
        self._mode_menu = tk.OptionMenu(mode_frame, self._mode_var, "")
        theme.style_optionmenu(self._mode_menu, width=12)
        self._mode_menu.pack(side='left', padx=(5, 0))
        self._rebuild_mode_menu()
        self._mode_var.trace_add("write", self._on_mode_change)

        # ---------- 倒计时设置 ----------
        self.settings_frame = tk.Frame(root, bg=theme.BG)
        self.settings_frame.pack(pady=3, fill='x', padx=40)

        self.settings_label = theme.label(
            self.settings_frame, tr("countdown_label"),
            font=theme.font(9), fg=theme.MUTED,
        )
        self.settings_label.pack(side='left')

        default_minutes = str(self._config.get("countdown_minutes", 30))

        self.minutes_var = tk.StringVar(value=default_minutes)
        self.minutes_entry = tk.Entry(
            self.settings_frame, textvariable=self.minutes_var,
            width=7, font=theme.font(10), justify='center',
            bg=theme.CARD, fg=theme.INK,
            relief="flat", insertbackground=theme.INK,
            highlightthickness=1, highlightbackground=theme.LINE,
            highlightcolor=theme.SAGE,
            disabledbackground=theme.LINE, disabledforeground=theme.MUTED,
        )
        self.minutes_entry.pack(side='left', padx=(5, 0))

        # ---------- 按钮框架 ----------
        self.btn_frame = tk.Frame(root, bg=theme.BG)
        self.btn_frame.pack(pady=12, fill='x', padx=40)

        self.start_btn = tk.Button(
            self.btn_frame, text=tr("start_btn"),
            width=11, command=self.start_timer,
        )
        theme.style_button(self.start_btn, "primary")
        self.start_btn.pack(side='left', padx=(0, 10))

        self.stop_btn = tk.Button(
            self.btn_frame, text=tr("stop_btn"),
            width=11, command=self.stop_timer,
            state=tk.DISABLED
        )
        theme.style_button(self.stop_btn, "subtle")
        self.stop_btn.pack(side='left')

        # ---------- 统计看板按钮 ----------
        self.stats_btn = tk.Button(
            root, text=tr("dashboard_btn"),
            width=20, command=lambda: stats.show_dashboard(root)
        )
        theme.style_button(self.stats_btn, "ghost")
        self.stats_btn.pack(pady=(2, 0))

        # ---------- 成就系统按钮 ----------
        self.achievements_btn = tk.Button(
            root, text=tr("achievements_btn"),
            width=20, command=lambda: gamification.show_achievements(root)
        )
        theme.style_button(self.achievements_btn, "ghost")
        self.achievements_btn.pack(pady=(3, 6))

        # ---------- 语言切换 ----------
        lang_frame = tk.Frame(root, bg=theme.BG)
        lang_frame.pack(pady=2, fill='x', padx=40)
        theme.label(lang_frame, tr("language"), font=theme.font(9), fg=theme.MUTED).pack(side='left')
        self._lang_var = tk.StringVar(value=self._lang_display())
        self._lang_menu = tk.OptionMenu(
            lang_frame, self._lang_var,
            *[_LANG_DISPLAY[lang] for lang in i18n.LANGUAGES],
            command=self._on_language_change,
        )
        theme.style_optionmenu(self._lang_menu, width=9)
        self._lang_menu.pack(side='left', padx=(5, 0))

        # ---------- 状态初始化 ----------
        self.timer_running = False
        self.timer_id = None
        self.start_time = None
        self._idle_check_id = None

        # 休息状态
        self.rest_start_time = None
        self.rest_window = None

        # 番茄工作法状态
        self._pomodoro_cycle = 0
        self._is_pomodoro_break = False
        self._pomodoro_long_break = False

        # 系统托盘
        self._tray_icon = None
        self._tray_thread = None

        # 绑定关闭事件 → 最小化到托盘
        root.protocol("WM_DELETE_WINDOW", self._minimize_to_tray)

        # 启动托盘图标
        self.root.after(200, self._setup_tray)

        # 启动 UI 更新
        self.update_time()

    # ---------- 系统托盘 ----------

    def _setup_tray(self) -> None:
        """创建系统托盘图标（在后台线程运行）"""
        if self._tray_icon is not None:
            return

        icon_image = _create_tray_image()

        def on_show() -> None:
            """显示主窗口"""
            self.root.after(0, self._show_window)

        def on_hide() -> None:
            """隐藏主窗口到托盘"""
            self.root.after(0, self._hide_window)

        def on_quit() -> None:
            """完全退出程序"""
            self.root.after(0, self._quit_app)

        menu = pystray.Menu(
            pystray.MenuItem(tr("tray_show"), on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(tr("tray_hide"), on_hide),
            pystray.MenuItem(tr("tray_quit"), on_quit),
        )

        self._tray_icon = pystray.Icon(
            "SightHabitKeeper",
            icon_image,
            tr("app_title"),
            menu,
        )

        # 在后台线程运行托盘图标
        self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        self._tray_thread.start()
        logger.info("系统托盘图标已启动")

    def _minimize_to_tray(self) -> None:
        """关闭窗口时最小化到系统托盘，而非退出"""
        if self._tray_icon is not None:
            self._hide_window()
            # 在托盘显示通知
            if self._tray_icon:
                self._tray_icon.notify(tr("tray_minimized"), tr("app_title"))
        else:
            # 托盘尚未就绪，直接退出
            self._quit_app()

    def _show_window(self) -> None:
        """显示主窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        logger.info("从系统托盘恢复主窗口")

    def _hide_window(self) -> None:
        """隐藏主窗口到系统托盘"""
        self.root.withdraw()
        logger.info("主窗口已隐藏到系统托盘")

    def _quit_app(self) -> None:
        """完全退出程序"""
        logger.info("通过系统托盘退出程序")
        # 保存配置
        self._config["countdown_minutes"] = float(self.minutes_var.get())
        save_config(self._config)
        # 停止托盘图标
        if self._tray_icon is not None:
            self._tray_icon.stop()
            self._tray_icon = None
        # 销毁窗口
        self.root.destroy()

    # ---------- 模式切换 ----------

    def _rebuild_mode_menu(self) -> None:
        """按当前语言重建模式下拉框（显示文案随语言，内部值不变）"""
        menu = self._mode_menu["menu"]
        menu.delete(0, "end")
        for internal in ("normal", "pomodoro"):
            menu.add_command(
                label=tr(f"mode_{internal}"),
                command=lambda value=internal: self._set_mode(value),
            )
        self._mode_var.set(tr(f"mode_{self._mode}"))

    def _set_mode(self, internal: str) -> None:
        """菜单选择：把内部模式值写入变量（显示为对应文案）"""
        self._mode_var.set(tr(f"mode_{internal}"))

    def _on_mode_change(self, *_args: Any) -> None:
        """模式切换回调（界面文案映射回内部模式值）"""
        label = self._mode_var.get()
        for internal in ("normal", "pomodoro"):
            if tr(f"mode_{internal}") == label:
                self._mode = internal
                break
        if self._mode == "pomodoro":
            self.settings_label.config(text=tr("work_label"))
        else:
            self.settings_label.config(text=tr("countdown_label"))
        if getattr(self, "timer_running", False):
            return  # 计时中不改输入框，避免打断倒计时设置
        if self._mode == "pomodoro":
            self.minutes_var.set("25")
        else:
            self.minutes_var.set(str(self._config.get("countdown_minutes", 30)))
        self.minutes_entry.config(state=tk.NORMAL)

    # ---------- 语言切换 ----------

    def _lang_display(self) -> str:
        """当前语言的显示文案"""
        return _LANG_DISPLAY.get(i18n.get_language(), "中文")

    def _on_language_change(self, label: str) -> None:
        """切换语言：立即生效于主窗口并持久化到配置"""
        code = next((c for c, d in _LANG_DISPLAY.items() if d == label), "zh")
        if code == i18n.get_language():
            return
        i18n.set_language(code)
        self._config["language"] = code
        save_config(self._config)
        self._apply_language()
        logger.info("界面语言切换为：%s", code)

    def _apply_language(self) -> None:
        """把当前语言刷新到主窗口的静态文本"""
        self.root.title(tr("app_title"))
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=tr("current_time", time=now_text))
        if not self.timer_running:
            self._set_status(tr("ready"), theme.MUTED)
        self._rebuild_mode_menu()  # 触发 _on_mode_change 刷新设置行文案
        self.start_btn.config(text=tr("start_btn"))
        self.stop_btn.config(text=tr("stop_btn"))
        self.stats_btn.config(text=tr("dashboard_btn"))
        self.achievements_btn.config(text=tr("achievements_btn"))

    # ---------- 时间更新 ----------

    def _set_status(self, text: str, color: str | None = None) -> None:
        """更新 hero 状态大字，color 缺省为墨青"""
        self.status_label.config(text=text, fg=color or theme.INK)

    def update_time(self) -> None:
        """实时更新时间显示（每秒更新）"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=tr("current_time", time=current_time))
        self.root.after(1000, self.update_time)

    # ---------- 计时核心 ----------

    def start_timer(self) -> None:
        """启动计时功能"""
        if not self.timer_running:
            try:
                minutes = float(self.minutes_var.get())
                if minutes <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(tr("warn_invalid_title"), tr("warn_invalid_msg"))
                return

            self.countdown_seconds = int(minutes * 60)
            self.timer_running = True
            self.start_time = datetime.now()

            self.minutes_entry.config(state=tk.DISABLED)

            mins = int(self.countdown_seconds // 60)
            secs = int(self.countdown_seconds % 60)
            self._set_status(
                tr("work_remaining", time=f"{mins:02d}:{secs:02d}"),
                theme.PRIMARY,
            )
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

            mode = self._mode
            logger.info(
                "计时开始：%d 分钟（%d 秒），模式：%s",
                minutes, self.countdown_seconds, mode,
            )

            # 开始计时循环
            self.timer_cycle()

    def stop_timer(self) -> None:
        """停止计时功能"""
        if self.timer_running:
            self.timer_running = False
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
                self.timer_id = None
            if self._idle_check_id:
                self.root.after_cancel(self._idle_check_id)
                self._idle_check_id = None

            # 统计：手动停止计为打断，并记录已工作时长
            if self.start_time is not None:
                worked = int((datetime.now() - self.start_time).total_seconds())
                stats.record_work(worked, self._mode)
            stats.record_interruption()

            self.minutes_entry.config(state=tk.NORMAL)
            self._set_status(tr("stopped"), theme.MUTED)
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

            logger.info("计时被用户手动停止")

    def timer_cycle(self) -> None:
        """计时循环的核心逻辑 - 使用after递归实现，自校正时间精度"""
        if not self.timer_running:
            return

        # 空闲检测：如果用户离开超过5分钟，暂停计时
        idle_secs = get_idle_seconds()
        if idle_secs > 300:  # 5分钟无操作
            self._set_status(tr("idle_paused"), theme.AMBER)
            # 不减少剩余时间，继续检测
            self._idle_check_id = self.root.after(5000, self.timer_cycle)
            return

        if self.start_time is None:  # 理论上不会发生，仅类型收窄
            return
        elapsed = (datetime.now() - self.start_time).total_seconds()
        remaining = max(0, self.countdown_seconds - elapsed)

        mins, secs = divmod(int(remaining), 60)
        self._set_status(
            tr("work_remaining", time=f"{mins:02d}:{secs:02d}"),
            theme.PRIMARY,
        )

        if remaining <= 0:
            self.timer_running = False
            # 统计：完整工作段结束，记录时长
            if self.start_time is not None:
                stats.record_work(
                    int((datetime.now() - self.start_time).total_seconds()),
                    self._mode,
                )
            self.minutes_entry.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

            mode = self._mode
            if mode == "pomodoro":
                self._on_pomodoro_complete()
            else:
                self._set_status(tr("time_up"), theme.AMBER)
                logger.info("计时结束，弹出休息提醒")
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)
                minutes_text = int(self.countdown_seconds // 60)
                self.show_rest_dialog(minutes_text)
            return

        # 自校正：计算距下一整秒的剩余毫秒数
        now = datetime.now()
        next_second = (now.timestamp() // 1 + 1) * 1000
        current_ms = now.timestamp() * 1000
        delay = max(50, int(next_second - current_ms))

        self.timer_id = self.root.after(delay, self.timer_cycle)

    # ---------- 番茄工作法 ----------

    def _on_pomodoro_complete(self) -> None:
        """番茄工作法计时完成回调"""
        self._pomodoro_cycle += 1
        self._is_pomodoro_break = True

        # 每4个番茄钟一次长休息（15分钟）
        if self._pomodoro_cycle % 4 == 0:
            break_minutes = 15
            self._pomodoro_long_break = True
        else:
            break_minutes = 5
            self._pomodoro_long_break = False

        status_text = tr("pomodoro_done", n=self._pomodoro_cycle, m=break_minutes)
        self._set_status(status_text, theme.PRIMARY)
        logger.info(
            "番茄钟 #%d 完成，休息 %d 分钟", self._pomodoro_cycle, break_minutes
        )

        winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS)

        # 显示休息对话框（带番茄工作法信息）
        self.show_rest_dialog(
            worked_minutes=int(self.countdown_seconds // 60),
            is_pomodoro_break=True,
            break_minutes=break_minutes,
        )

    # ---------- 休息对话框 ----------

    def show_rest_dialog(
        self,
        worked_minutes: int,
        is_pomodoro_break: bool = False,
        break_minutes: int = 3,
    ) -> None:
        """显示休息对话框，包含健康小贴士"""
        self.rest_start_time = datetime.now()

        try:
            self.rest_window = tk.Toplevel(self.root)
        except tk.TclError as e:
            logger.error("创建休息对话框失败：%s", e)
            messagebox.showerror(tr("error_dialog_title"), tr("error_dialog_msg"))
            return

        # 如果主窗口已隐藏到托盘，确保对话框可见时恢复主窗口
        try:
            if self.root.state() == "withdrawn":
                self.root.deiconify()
        except tk.TclError:
            pass

        # 对话框标题随模式变化
        if is_pomodoro_break:
            if self._pomodoro_long_break:
                title_text = tr("rest_title_long", n=self._pomodoro_cycle)
            else:
                title_text = tr("rest_title_pomodoro", n=self._pomodoro_cycle)
        else:
            title_text = tr("rest_title")

        # ---------- 全屏遮罩：深松绿满屏，居中卡片 ----------
        win = self.rest_window
        win.title(tr("rest_title"))
        win.configure(bg=theme.PRIMARY_DK)
        win.attributes('-topmost', True)
        try:
            win.attributes('-fullscreen', True)
        except tk.TclError:
            win.geometry("800x600")

        def _close(event: Any = None) -> None:
            """Esc / 关闭 = 忽略休息"""
            self.rest_ignore()

        win.bind("<Escape>", _close)

        card = theme.card(win)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # 卡片标题
        theme.label(
            card, title_text,
            font=theme.font(12, "bold"), fg=theme.INK,
            wraplength=440, justify="center",
        ).pack(padx=50, pady=(28, 2))

        # 主消息
        if is_pomodoro_break:
            msg = tr("rest_msg_pomodoro", m=break_minutes)
        else:
            msg = tr("rest_msg_normal", m=worked_minutes)
        theme.label(
            card, msg,
            font=theme.font(10), fg=theme.MUTED,
            wraplength=440, justify="center",
        ).pack(padx=50, pady=(4, 14))

        # 休息倒计时（卡片内的视觉重心）
        self.rest_countdown_label = theme.label(
            card,
            text=tr("rest_countdown", time=f"{break_minutes:02d}:00"),
            font=theme.font(30, "bold"), fg=theme.PRIMARY,
        )
        self.rest_countdown_label.pack(pady=(6, 10))

        # 健康小贴士
        tip = random.choice(HEALTH_TIPS)
        theme.label(
            card, tip,
            font=theme.font(9), fg=theme.MUTED,
            wraplength=420, justify="center",
        ).pack(padx=50, pady=(2, 16))

        # 按钮框架
        rest_btn_frame = tk.Frame(card, bg=theme.CARD)
        rest_btn_frame.pack(pady=(0, 26))

        self.rest_confirm_btn = tk.Button(
            rest_btn_frame, text=tr("rest_confirm_btn"),
            width=14, command=self.rest_confirm,
        )
        theme.style_button(self.rest_confirm_btn, "primary")
        self.rest_confirm_btn.pack(side='left', padx=5)

        ignore_btn = tk.Button(
            rest_btn_frame, text=tr("rest_ignore_btn"),
            width=8, command=self.rest_ignore,
        )
        theme.style_button(ignore_btn, "subtle")
        ignore_btn.pack(side='left', padx=5)

        self.rest_window.protocol("WM_DELETE_WINDOW", self.rest_ignore)

        # 保存休息时长供倒计时使用
        self._break_seconds = break_minutes * 60
        self.update_rest_countdown()

    def update_rest_countdown(self) -> None:
        """更新休息倒计时显示"""
        if self.rest_window is None or not self.rest_window.winfo_exists():
            return
        if self.rest_start_time is None:  # 理论上不会发生，仅类型收窄
            return

        elapsed = (datetime.now() - self.rest_start_time).total_seconds()
        remaining = max(0, self._break_seconds - elapsed)

        mins, secs = divmod(int(remaining), 60)

        if self.rest_countdown_label is None:  # 类型收窄
            return
        if remaining <= 0:
            self.rest_countdown_label.config(
                text=tr("rest_done"), fg=theme.PRIMARY
            )
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
            return

        self.rest_countdown_label.config(
            text=tr("rest_countdown", time=f"{mins:02d}:{secs:02d}"),
            fg=theme.PRIMARY,
        )
        self.rest_window.after(1000, self.update_rest_countdown)

    def rest_confirm(self) -> None:
        """点击确认重新开始"""
        if self.rest_window is None or not self.rest_window.winfo_exists():
            return
        if self.rest_start_time is None:  # 理论上不会发生，仅类型收窄
            return

        elapsed = (datetime.now() - self.rest_start_time).total_seconds()
        if elapsed < 180:
            messagebox.showwarning(tr("warn_rest_title"), tr("warn_rest_msg"))
            return

        # 统计：一次完整休息
        stats.record_rest_completed()
        # 游戏化：检查是否有新徽章解锁
        gamification.check_and_notify(self.root)

        self.rest_window.destroy()
        self.rest_window = None
        self._on_rest_complete()

    def rest_ignore(self) -> None:
        """忽略休息限制，立即重新开始"""
        # 统计：忽略休息提醒计为打断
        stats.record_interruption()
        if self.rest_window and self.rest_window.winfo_exists():
            self.rest_window.destroy()
        self.rest_window = None
        self._on_rest_complete()

    def _on_rest_complete(self) -> None:
        """休息结束后的回调（启动下一轮计时）"""
        mode = self._mode
        if mode == "pomodoro" and self._is_pomodoro_break:
            # 番茄模式休息结束后自动进入下一轮工作
            self._is_pomodoro_break = False
            self._set_status(
                tr("pomodoro_start", n=self._pomodoro_cycle + 1),
                theme.PRIMARY,
            )
            # 恢复默认工作时长
            self.minutes_var.set("25")
            self.start_timer()
        else:
            self.start_timer()

    # ---------- 窗口关闭 ----------

    def _on_closing(self) -> None:
        """窗口关闭时保存配置并退出（通过托盘关闭时已保存）"""
        self._config["countdown_minutes"] = float(self.minutes_var.get())
        save_config(self._config)
        if self._tray_icon is not None:
            self._tray_icon.stop()
        self.root.destroy()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("应用程序启动")
    root = tk.Tk()
    app = StandUpApp(root)
    root.mainloop()
    logger.info("应用程序退出")