import tkinter as tk
from tkinter import messagebox
from datetime import datetime

class StandUpApp:
    """主应用程序类，使用Tkinter实现非线程化定时功能"""
    
    def __init__(self, root):
        """初始化GUI界面组件"""
        self.root = root
        root.title("久坐提醒器")  # 设置窗口标题
        root.geometry("300x200")  # 设置初始窗口尺寸
        root.resizable(False, False)  # 禁止调整窗口大小，保持固定布局
        
        # 时间显示标签 - 显示当前系统时间
        self.time_label = tk.Label(root, text="当前时间：", font=('Arial', 14))
        self.time_label.pack(pady=(10, 5))  # 放置标签并设置垂直间距
        
        # 状态显示标签 - 显示计时器状态
        self.status_label = tk.Label(root, text="准备启动", font=('Arial', 12))
        self.status_label.pack(pady=(0, 10))  # 放置标签并设置垂直间距
        
        # 倒计时设置框架 - 用于输入自定义时长
        self.settings_frame = tk.Frame(root)
        self.settings_frame.pack(pady=2, fill='x', padx=50)

        # 倒计时分钟数输入
        self.settings_label = tk.Label(self.settings_frame, text="倒计时（分钟）：", font=('Arial', 10))
        self.settings_label.pack(side='left')

        self.minutes_var = tk.StringVar(value="30")
        self.minutes_entry = tk.Entry(
            self.settings_frame, textvariable=self.minutes_var,
            width=6, font=('Arial', 10), justify='center'
        )
        self.minutes_entry.pack(side='left', padx=(5, 0))

        # 按钮框架 - 用于容纳开始和停止按钮
        self.btn_frame = tk.Frame(root)
        self.btn_frame.pack(pady=5, fill='x', padx=50)  # 水平居中放置
        
        # 开始按钮 - 触发计时启动
        self.start_btn = tk.Button(
            self.btn_frame, text="开始计时", 
            width=10, command=self.start_timer
        )
        self.start_btn.pack(side='left', padx=(0, 10))  # 左侧放置，右边留空隙
        
        # 停止按钮 - 停止正在运行的计时器
        self.stop_btn = tk.Button(
            self.btn_frame, text="停止计时", 
            width=10, command=self.stop_timer,
            state=tk.DISABLED  # 初始不可用（没有计时时停止按钮无效）
        )
        self.stop_btn.pack(side='left')  # 左侧放置
        
        # 初始化计时器状态
        self.timer_running = False  # 计时器运行标志
        self.timer_id = None  # 存储after调用的ID，用于取消
        self.start_time = None  # 计时开始的时间点
        
        # 休息状态变量
        self.rest_start_time = None  # 休息开始时间
        self.rest_window = None  # 休息对话框引用
        
        # 初始化UI
        self.update_time()  # 启动时间更新
        self.check_inactive_timer()  # 启动空闲检测

    def update_time(self):
        """实时更新时间显示（每秒更新）"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 获取当前时间
        self.time_label.config(text=f"当前时间：{current_time}")  # 更新标签文本
        # 每1秒递归调用自身，实现持续更新时间
        self.root.after(1000, self.update_time)  # 关键点：使用after而非线程

    def start_timer(self):
        """启动计时功能"""
        if not self.timer_running:  # 防止重复启动
            # 读取用户输入的分辨数
            try:
                minutes = float(self.minutes_var.get())
                if minutes <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("输入错误", "请输入有效的分钟数（正数）")
                return

            self.countdown_seconds = int(minutes * 60)  # 转换为秒
            self.timer_running = True  # 设置运行标志
            self.start_time = datetime.now()  # 记录开始时间

            # 禁用输入框，防止计时中修改时长
            self.minutes_entry.config(state=tk.DISABLED)
            
            # 更新UI状态
            mins = int(self.countdown_seconds // 60)
            secs = int(self.countdown_seconds % 60)
            self.status_label.config(text=f"工作中（剩余{mins:02d}:{secs:02d}）")
            self.start_btn.config(state=tk.DISABLED)  # 禁用开始按钮
            self.stop_btn.config(state=tk.NORMAL)  # 启用停止按钮
            
            # 开始计时循环 - 核心功能入口
            self.timer_cycle()
        
    def stop_timer(self):
        """停止计时功能"""
        if self.timer_running:  # 确保计时器正在运行
            self.timer_running = False  # 清除运行标志
            if self.timer_id:  # 检查是否有待处理的after调用
                self.root.after_cancel(self.timer_id)  # 取消待处理的定时任务
                self.timer_id = None
            
            # 恢复输入框，允许修改时长
            self.minutes_entry.config(state=tk.NORMAL)
            
            # 更新UI状态
            self.status_label.config(text="已停止")
            self.start_btn.config(state=tk.NORMAL)  # 启用开始按钮
            self.stop_btn.config(state=tk.DISABLED)  # 禁用停止按钮

    def timer_cycle(self):
        """计时循环的核心逻辑 - 使用after递归实现"""
        # 如果计时器被停止（例如点击了停止按钮），则直接退出
        if not self.timer_running:
            return

        # 计算已过时间和剩余时间
        elapsed = (datetime.now() - self.start_time).total_seconds()  # 自开始以来的秒数
        remaining = max(0, self.countdown_seconds - elapsed)  # 使用自定义倒计时时长

        # 将秒转换为分钟和秒，并更新显示
        mins, secs = divmod(int(remaining), 60)
        self.status_label.config(text=f"工作中（剩余{mins:02d}:{secs:02d}）")

        # 检查是否需要提醒（剩余时间≤0）
        if remaining <= 0:
            # 停止计时器
            self.timer_running = False
            self.status_label.config(text="时间到！请起身活动")
            self.minutes_entry.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

            # 显示休息对话框
            minutes_text = int(self.countdown_seconds // 60)
            self.show_rest_dialog(minutes_text)
            return  # 退出函数，不递归调用

        # 计划下一次检查 - 每秒更新一次（递归实现）
        self.timer_id = self.root.after(1000, self.timer_cycle)  # 关键点：替代线程的核心
        
    def check_inactive_timer(self):
        """空闲状态监控 - 仅用于维持after事件循环，无实质逻辑"""
        # 每200毫秒递归调用自身（仅为维持事件循环，不执行任何阻塞操作）
        self.root.after(200, self.check_inactive_timer)

    # ---------- 休息对话框（3分钟强制休息） ----------

    def show_rest_dialog(self, worked_minutes):
        """显示休息对话框，强制休息至少3分钟"""
        self.rest_start_time = datetime.now()

        # 创建顶级对话框
        self.rest_window = tk.Toplevel(self.root)
        self.rest_window.title("休息提醒")
        self.rest_window.geometry("360x200")
        self.rest_window.resizable(False, False)
        self.rest_window.attributes('-topmost', True)

        # 主消息
        tk.Label(self.rest_window, text=f"您已连续工作{worked_minutes}分钟，请离开座位！",
                 font=('Arial', 11)).pack(pady=(15, 5))

        # 休息倒计时标签
        self.rest_countdown_label = tk.Label(
            self.rest_window,
            text="还需休息 3:00",
            font=('Arial', 14, 'bold'),
            fg='blue'
        )
        self.rest_countdown_label.pack(pady=(5, 5))

        # 按钮框架
        rest_btn_frame = tk.Frame(self.rest_window)
        rest_btn_frame.pack(pady=(10, 5))

        # 确认重新开始按钮（始终可用，但3分钟内点击会弹出警告）
        self.rest_confirm_btn = tk.Button(
            rest_btn_frame, text="确认重新开始",
            width=14, command=self.rest_confirm
        )
        self.rest_confirm_btn.pack(side='left', padx=5)

        # 忽略按钮 - 取消3分钟限制，立即重新开始
        tk.Button(
            rest_btn_frame, text="忽略",
            width=8, command=self.rest_ignore
        ).pack(side='left', padx=5)

        # 窗口关闭事件绑定（关闭窗口等同于忽略）
        self.rest_window.protocol("WM_DELETE_WINDOW", self.rest_ignore)

        # 启动休息倒计时更新
        self.update_rest_countdown()

    def update_rest_countdown(self):
        """更新休息倒计时显示"""
        if self.rest_window is None or not self.rest_window.winfo_exists():
            return

        elapsed = (datetime.now() - self.rest_start_time).total_seconds()
        remaining = max(0, 180 - elapsed)  # 180秒 = 3分钟

        mins, secs = divmod(int(remaining), 60)

        if remaining <= 0:
            self.rest_countdown_label.config(
                text="休息时间到，可以继续工作了！", fg='green'
            )
            return

        self.rest_countdown_label.config(text=f"还需休息 {mins:02d}:{secs:02d}")

        # 每秒更新一次
        self.rest_window.after(1000, self.update_rest_countdown)

    def rest_confirm(self):
        """点击确认重新开始 - 3分钟内弹出警告，3分钟后才生效"""
        if self.rest_window is None or not self.rest_window.winfo_exists():
            return

        elapsed = (datetime.now() - self.rest_start_time).total_seconds()
        if elapsed < 180:
            # 还没到3分钟，弹出警告
            messagebox.showwarning("休息不足", "至少休息3分钟才可以继续工作哦~")
            self.root.attributes('-topmost', 0)
            return

        # 3分钟已到，正常重新开始
        self.rest_window.destroy()
        self.rest_window = None
        self.start_timer()

    def rest_ignore(self):
        """忽略3分钟限制，立即重新开始计时"""
        if self.rest_window and self.rest_window.winfo_exists():
            self.rest_window.destroy()
        self.rest_window = None
        self.start_timer()

if __name__ == "__main__":
    root = tk.Tk()  # 创建主窗口
    app = StandUpApp(root)  # 实例化应用程序
    root.mainloop()  # 启动GUI事件循环