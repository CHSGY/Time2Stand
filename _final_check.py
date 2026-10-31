# -*- coding: utf-8 -*-
"""一次性回归（最终确认）：选项卡 + 休息浮动提示核心路径。运行后删除。"""
import os
import sys
import tempfile
import time
from datetime import timedelta

tmpdir = tempfile.mkdtemp()
os.environ["APPDATA"] = tmpdir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import messagebox
import theme

root = tk.Tk()
root.withdraw()

import Sight_Habit_Keeper as app_mod
app = app_mod.StandUpApp(root)
root.deiconify()
root.update()

ok = []
def check(name, cond):
    ok.append((name, cond))
    print(("PASS " if cond else "FAIL ") + name)

# 选项卡往返
for tab in ("dashboard", "achievements", "home"):
    app._show_tab(tab)
    root.update()
check("选项卡往返后回到首页", app._active_tab == "home")
check("首页已布局", app._tab_frames["home"].winfo_manager() == "pack")

# 休息浮动提示核心路径
warned = []
messagebox.showwarning = lambda *a, **k: warned.append(a)
app._show_tab("home")
app.minutes_var.set("0.02")
app.start_timer()
time.sleep(1.3)
app.timer_cycle()
check("休息界面弹出", app.rest_window is not None)
app.rest_confirm()
app.rest_confirm()
root.update()
check("叠加提示", len(app._rest_warn_frame.winfo_children()) == 2)
check("不再弹窗", len(warned) == 0)
for _ in range(25):
    root.update()
    time.sleep(0.1)
check("淡出消失", len(app._rest_warn_frame.winfo_children()) == 0)
app.rest_ignore()
check("忽略退出", app.rest_window is None)

# 满休息时间后确认成功
app.stop_timer()
app._set_mode("pomodoro")
app.minutes_var.set("0.02")
app.start_timer()
time.sleep(1.3)
app.timer_cycle()
if app.rest_window is not None:
    app.rest_start_time -= timedelta(minutes=5)
    app.rest_confirm()
check("满休息确认成功并自动下一轮", app.timer_running is True)
app.stop_timer()

app._quit_app()

failed = [n for n, c in ok if not c]
print("ALL_OK" if not failed else "FAILED: %s" % failed)
sys.exit(1 if failed else 0)
