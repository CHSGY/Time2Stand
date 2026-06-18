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
            self.timer_running = True  # 设置运行标志
            self.start_time = datetime.now()  # 记录开始时间
            
            # 更新UI状态
            self.status_label.config(text="工作中（剩余30:00）")
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
        remaining = max(0, 1800 - elapsed)  # 1800秒 = 30分钟，确保不小于0

        # 将秒转换为分钟和秒，并更新显示
        mins, secs = divmod(int(remaining), 60)
        self.status_label.config(text=f"工作中（剩余{mins:02d}:{secs:02d}）")

        # 检查是否需要提醒（剩余时间≤0）
        if remaining <= 0:
            # 停止计时器
            self.timer_running = False
            self.status_label.config(text="时间到！请起身活动")

            # 弹出模态提醒窗口（会阻塞直到用户点击确定）
            self.root.attributes('-topmost', 1)   # 窗口置顶
            messagebox.showinfo("休息提醒", "您已连续工作30分钟，请离开座位！")
            self.root.attributes('-topmost', 0)   # 取消置顶

            # 用户点击确定后，自动重新开始倒计时
            self.start_timer()
            return  # 退出函数，不递归调用

        # 计划下一次检查 - 每秒更新一次（递归实现）
        self.timer_id = self.root.after(1000, self.timer_cycle)  # 关键点：替代线程的核心
        
    def check_inactive_timer(self):
        """空闲状态监控 - 仅用于维持after事件循环，无实质逻辑"""
        # 每200毫秒递归调用自身（仅为维持事件循环，不执行任何阻塞操作）
        self.root.after(200, self.check_inactive_timer)

if __name__ == "__main__":
    root = tk.Tk()  # 创建主窗口
    app = StandUpApp(root)  # 实例化应用程序
    root.mainloop()  # 启动GUI事件循环