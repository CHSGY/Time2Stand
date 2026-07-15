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
    # 番茄工作法
    _mode_var: tk.StringVar
    _pomodoro_cycle: int
    _is_pomodoro_break: bool
    _pomodoro_long_break: bool

    def __init__(self, root: tk.Tk) -> None:
        """初始化GUI界面组件"""
        self.root = root
        root.title("久坐提醒器")
        root.geometry("300x280")
        root.resizable(False, False)

        # ---------- 顶部：时间显示 ----------
        self.time_label = tk.Label(root, text="当前时间：", font=('Arial', 14))
        self.time_label.pack(pady=(10, 5))

        self.status_label = tk.Label(root, text="准备启动", font=('Arial', 12))
        self.status_label.pack(pady=(0, 5))

        # ---------- 模式选择 ----------
        mode_frame = tk.Frame(root)
        mode_frame.pack(pady=2, fill='x', padx=50)
        tk.Label(mode_frame, text="模式：", font=('Arial', 10)).pack(side='left')
        self._mode_var = tk.StringVar(value="normal")
        mode_menu = tk.OptionMenu(mode_frame, self._mode_var, "normal", "pomodoro")
        mode_menu.config(font=('Arial', 9), width=10)
        mode_menu.pack(side='left', padx=(5, 0))
        self._mode_var.trace_add("write", self._on_mode_change)

        # ---------- 倒计时设置 ----------
        self.settings_frame = tk.Frame(root)
        self.settings_frame.pack(pady=2, fill='x', padx=50)

        self.settings_label = tk.Label(self.settings_frame, text="倒计时（分钟）：", font=('Arial', 10))
        self.settings_label.pack(side='left')

        self._config = load_config()
        default_minutes = str(self._config.get("countdown_minutes", 30))

        self.minutes_var = tk.StringVar(value=default_minutes)
        self.minutes_entry = tk.Entry(
            self.settings_frame, textvariable=self.minutes_var,
            width=6, font=('Arial', 10), justify='center'
        )
        self.minutes_entry.pack(side='left', padx=(5, 0))

        # ---------- 按钮框架 ----------
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=5, fill='x', padx=50)

        self.start_btn = tk.Button(
            self.btn_frame, text="开始计时",
            width=10, command=self.start_timer
        )
        self.start_btn.pack(side='left', padx=(0, 10))

        self.stop_btn = tk.Button(
            self.btn_frame, text="停止计时",
            width=10, command=self.stop_timer,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side='left')

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
            pystray.MenuItem("显示窗口", on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("隐藏到托盘", on_hide),
            pystray.MenuItem("退出", on_quit),
        )

        self._tray_icon = pystray.Icon(
            "SightHabitKeeper",
            icon_image,
            "久坐提醒器",
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
                self._tray_icon.notify("久坐提醒器已最小化到系统托盘", "久坐提醒器")
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

    def _on_mode_change(self, *_args: Any) -> None:
        """模式切换回调"""
        mode = self._mode_var.get()
        if mode == "pomodoro":
            self.settings_label.config(text="工作时长（分钟）：")
            self.minutes_var.set("25")
            self.minutes_entry.config(state=tk.NORMAL)
        else:
            self.settings_label.config(text="倒计时（分钟）：")
            self.minutes_var.set(str(self._config.get("countdown_minutes", 30)))
            self.minutes_entry.config(state=tk.NORMAL)

    # ---------- 时间更新 ----------

    def update_time(self) -> None:
        """实时更新时间显示（每秒更新）"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"当前时间：{current_time}")
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
                messagebox.showwarning("输入错误", "请输入有效的分钟数（正数）")
                return

            self.countdown_seconds = int(minutes * 60)
            self.timer_running = True
            self.start_time = datetime.now()

            self.minutes_entry.config(state=tk.DISABLED)

            mins = int(self.countdown_seconds // 60)
            secs = int(self.countdown_seconds % 60)
            self.status_label.config(text=f"工作中（剩余{mins:02d}:{secs:02d}）")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

            mode = self._mode_var.get()
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

            self.minutes_entry.config(state=tk.NORMAL)
            self.status_label.config(text="已停止")
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
            self.status_label.config(text="检测到用户离开，计时暂停")
            # 不减少剩余时间，继续检测
            self._idle_check_id = self.root.after(5000, self.timer_cycle)
            return

        elapsed = (datetime.now() - self.start_time).total_seconds()
        remaining = max(0, self.countdown_seconds - elapsed)

        mins, secs = divmod(int(remaining), 60)
        self.status_label.config(text=f"工作中（剩余{mins:02d}:{secs:02d}）")

        if remaining <= 0:
            self.timer_running = False
            self.minutes_entry.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

            mode = self._mode_var.get()
            if mode == "pomodoro":
                self._on_pomodoro_complete()
            else:
                self.status_label.config(text="时间到！请起身活动")
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

        status_text = (
            f"🎉 完成第{self._pomodoro_cycle}个番茄钟！"
            f"休息{break_minutes}分钟"
        )
        self.status_label.config(text=status_text)
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
            messagebox.showerror("错误", "无法创建休息提醒窗口，请稍后重试")
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
                title_text = f"🎉 长休息 — 第{self._pomodoro_cycle}个番茄钟完成！"
            else:
                title_text = f"🍅 休息时间 — 第{self._pomodoro_cycle}个番茄钟完成！"
        else:
            title_text = "休息提醒"

        self.rest_window.title("休息提醒")
        self.rest_window.geometry("400x300")
        self.rest_window.resizable(False, False)
        self.rest_window.attributes('-topmost', True)

        # 主消息
        if is_pomodoro_break:
            msg = f"{title_text}\n休息{break_minutes}分钟，放松一下~"
        else:
            msg = f"您已连续工作{worked_minutes}分钟，请离开座位！"

        tk.Label(
            self.rest_window, text=msg,
            font=('Arial', 11), wraplength=360,
        ).pack(pady=(15, 5))

        # 休息倒计时
        self.rest_countdown_label = tk.Label(
            self.rest_window,
            text=f"还需休息 {break_minutes:02d}:00",
            font=('Arial', 14, 'bold'),
            fg='blue',
        )
        self.rest_countdown_label.pack(pady=(5, 5))

        # 健康小贴士
        tip = random.choice(HEALTH_TIPS)
        tk.Label(
            self.rest_window, text=tip,
            font=('Arial', 9), fg='#555555', wraplength=360,
            justify='center',
        ).pack(pady=(5, 5))

        # 按钮框架
        rest_btn_frame = tk.Frame(self.rest_window)
        rest_btn_frame.pack(pady=(10, 5))

        self.rest_confirm_btn = tk.Button(
            rest_btn_frame, text="确认重新开始",
            width=14, command=self.rest_confirm,
        )
        self.rest_confirm_btn.pack(side='left', padx=5)

        tk.Button(
            rest_btn_frame, text="忽略",
            width=8, command=self.rest_ignore,
        ).pack(side='left', padx=5)

        self.rest_window.protocol("WM_DELETE_WINDOW", self.rest_ignore)

        # 保存休息时长供倒计时使用
        self._break_seconds = break_minutes * 60
        self.update_rest_countdown()

    def update_rest_countdown(self) -> None:
        """更新休息倒计时显示"""
        if self.rest_window is None or not self.rest_window.winfo_exists():
            return

        elapsed = (datetime.now() - self.rest_start_time).total_seconds()
        remaining = max(0, self._break_seconds - elapsed)

        mins, secs = divmod(int(remaining), 60)

        if remaining <= 0:
            self.rest_countdown_label.config(
                text="休息时间到，可以继续工作了！", fg='green'
            )
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
            return

        self.rest_countdown_label.config(text=f"还需休息 {mins:02d}:{secs:02d}")
        self.rest_window.after(1000, self.update_rest_countdown)

    def rest_confirm(self) -> None:
        """点击确认重新开始"""
        if self.rest_window is None or not self.rest_window.winfo_exists():
            return

        elapsed = (datetime.now() - self.rest_start_time).total_seconds()
        if elapsed < 180:
            messagebox.showwarning("休息不足", "至少休息3分钟才可以继续工作哦~")
            return

        self.rest_window.destroy()
        self.rest_window = None
        self._on_rest_complete()

    def rest_ignore(self) -> None:
        """忽略休息限制，立即重新开始"""
        if self.rest_window and self.rest_window.winfo_exists():
            self.rest_window.destroy()
        self.rest_window = None
        self._on_rest_complete()

    def _on_rest_complete(self) -> None:
        """休息结束后的回调（启动下一轮计时）"""
        mode = self._mode_var.get()
        if mode == "pomodoro" and self._is_pomodoro_break:
            # 番茄模式休息结束后自动进入下一轮工作
            self._is_pomodoro_break = False
            self.status_label.config(
                text=f"🍅 开始第{self._pomodoro_cycle + 1}个番茄钟！"
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