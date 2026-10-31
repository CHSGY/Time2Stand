"""界面主题 — 「晨间公园」设计 token（v2.5 UI 美化）

配色灵感来自产品本身：久坐后起身走进的清晨公园。
- 纸白背景、墨青正文，整体安静
- 深松绿 = 主操作与"工作中"状态（健康、行动）
- 琥珀 = 需要注意的状态（时间到、离开暂停）
- 视觉重心只有一个：倒计时/状态的大字（hero），其余一律弱化
"""

from __future__ import annotations

import tkinter as tk
from typing import Any

# ---------- 调色板 ----------
BG: str = "#FAFBF8"        # 纸白背景（冷调微绿）
CARD: str = "#FFFFFF"      # 卡片/输入框底
INK: str = "#22333B"       # 墨青正文
MUTED: str = "#6B7A72"     # 弱化文字（灰绿）
PRIMARY: str = "#2F5D50"   # 深松绿：主按钮/工作中
PRIMARY_DK: str = "#24483E"  # 深松绿按下态
SAGE: str = "#8FB8A8"      # 鼠尾草绿：辅助/成功
AMBER: str = "#B97A24"     # 琥珀：提醒/暂停（深琥珀保证白底可读）
LINE: str = "#E3EAE4"      # 分隔线/描边

# ---------- 字体 ----------
FONT: str = "Microsoft YaHei UI"


def font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    """统一字体元组：雅黑 UI + 字号 + 字重"""
    return (FONT, size, weight)


def style_button(
    btn: tk.Button,
    kind: str = "ghost",
    **kwargs: Any,
) -> None:
    """统一按钮样式。

    kind:
        primary — 深松绿实底白字（主动作，每屏至多一个）
        subtle  — 白底墨字细描边（次动作）
        ghost   — 无边框绿字（工具入口，如看板/成就）
    """
    presets: dict[str, dict[str, Any]] = {
        "primary": dict(
            bg=PRIMARY, fg="#FFFFFF",
            activebackground=PRIMARY_DK, activeforeground="#FFFFFF",
        ),
        "subtle": dict(
            bg=CARD, fg=INK,
            activebackground=LINE, activeforeground=INK,
        ),
        "ghost": dict(
            bg=BG, fg=PRIMARY,
            activebackground=LINE, activeforeground=PRIMARY_DK,
        ),
    }
    style = presets.get(kind, presets["ghost"])
    flat: dict[str, Any] = dict(
        relief="flat", bd=0,
        highlightthickness=1,
        highlightbackground=LINE if kind != "primary" else PRIMARY,
        highlightcolor=LINE if kind != "primary" else PRIMARY,
        cursor="hand2",
        font=font(10),
    )
    flat.update(style)
    flat.update(kwargs)
    btn.config(**flat)


def style_optionmenu(om: tk.OptionMenu, width: int = 10) -> None:
    """下拉框统一样式：白底细描边、扁平无立体"""
    om.config(
        relief="flat", bd=0, width=width,
        bg=CARD, fg=INK,
        activebackground=LINE, activeforeground=INK,
        highlightthickness=1, highlightbackground=LINE, highlightcolor=SAGE,
        font=font(9), cursor="hand2", anchor="w", indicatoron=False,
    )
    om["menu"].config(
        bg=CARD, fg=INK, bd=0, font=font(9),
        activebackground=LINE, activeforeground=INK,
    )


def card(parent: tk.Misc, **kwargs: Any) -> tk.Frame:
    """白色卡片容器：细描边、无边框立体感"""
    kwargs.setdefault("bg", CARD)
    kwargs.setdefault("highlightbackground", LINE)
    kwargs.setdefault("highlightthickness", 1)
    kwargs.setdefault("bd", 0)
    return tk.Frame(parent, **kwargs)


def label(parent: tk.Misc, text: str = "", **kwargs: Any) -> tk.Label:
    """背景透明化（用父容器底色）的标签快捷构造"""
    if "bg" not in kwargs:
        try:
            kwargs["bg"] = parent.cget("bg")
        except tk.TclError:
            kwargs["bg"] = BG
    kwargs.setdefault("fg", INK)
    kwargs.setdefault("font", font(10))
    return tk.Label(parent, text=text, **kwargs)


def setup_window(win: tk.Misc, bg: str = BG) -> None:
    """窗口统一底色"""
    win.configure({"bg": bg})
