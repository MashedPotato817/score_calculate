import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Literal

from models import BigGame, SmallRound
from persistence import (
    load_games, save_games, get_active_game,
    finish_all_active, finish_game, resume_game, delete_game,
)

# ── 格式化常量 ─────────────────────────────────────────────────────────────
def _format_round_line(r) -> str:
    return (
        f"#{r.seq} 地主:{r.landlord} "
        f"番数:{r.fanshu}  {r.winner}赢"
    )


class DoudizhuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("斗地主计分器")
        self.geometry("720x620")
        self.minsize(600, 580)

        self._setup_style()

        self.games: list[BigGame] = load_games()
        self.active_game: BigGame | None = get_active_game(self.games)

        self._create_widgets()
        self._refresh_all()

    # ========== 样式 ==========

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel",   font=("Microsoft YaHei", 13, "bold"), foreground="#2c3e50")
        style.configure("Section.TLabel", font=("Microsoft YaHei", 10, "bold"), foreground="#34495e")
        style.configure("Score.TLabel",   font=("Consolas", 20, "bold"),        foreground="#e74c3c")
        style.configure("Fanshu.TLabel",  font=("Consolas", 18, "bold"),        foreground="#e67e22")
        style.configure("Action.TButton", font=("Microsoft YaHei", 10))
        style.configure("Win.TButton",    font=("Microsoft YaHei", 10, "bold"), padding=(15, 5))
        style.configure("PlayerName.TEntry", font=("Microsoft YaHei", 14))
        style.configure("Treeview",       font=("Microsoft YaHei", 9))
        style.configure("TLabelframe.Label", font=("Microsoft YaHei", 9, "bold"))
        style.layout("Tab", [("Notebook.tab", {"sticky": "nswe",
            "children": [("Notebook.padding", {"side": "top", "sticky": "nswe",
                "children": [("Notebook.focus", {"side": "top", "sticky": "nswe",
                    "children": [("Notebook.label", {"side": "top", "sticky": ""})],
                })],
            })],
        })])
        style.configure("TNotebook.Tab", font=("Microsoft YaHei", 10), padding=(15, 3))

    # ========== 控件工厂 ==========

    @staticmethod
    def _make_button(parent, text, command, bg, active_bg,
                     fg="white", font_size=10, bold=False,
                     padx=15, pady=4,
                     state: Literal['normal', 'active', 'disabled'] = tk.NORMAL) -> tk.Button:
        """统一风格的 tk.Button 工厂，消除各处重复的样式参数。"""
        weight = "bold" if bold else "normal"
        return tk.Button(
            parent, text=text, command=command,
            font=("Microsoft YaHei", font_size, weight),
            bg=bg, fg=fg,
            activebackground=active_bg, activeforeground=fg,
            relief=tk.RAISED, bd=1,
            padx=padx, pady=pady,
            cursor="hand2", state=state,
        )

    # ========== 控件创建 ==========

    def _create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.page1 = ttk.Frame(self.notebook)
        self.page2 = ttk.Frame(self.notebook)
        self.notebook.add(self.page1, text="当前大局")
        self.notebook.add(self.page2, text="历史大局")

        self._build_page1()
        self._build_page2()

    def _build_page1(self):
        # ── 标题区域（居中，带状态标签）──
        header = ttk.Frame(self.page1)
        header.pack(pady=(8, 5))
        self.p1_badge = ttk.Label(header, text="进行中",
                                  font=("Microsoft YaHei", 9),
                                  foreground="#993C1D", background="#FAECE7",
                                  padding=(6, 1))
        self.p1_badge.pack()
        self.p1_badge.configure(background="#FAECE7")
        self.p1_title = ttk.Label(header, text="大局 #1 · 2026-06-19 00:30",
                                  font=("Microsoft YaHei", 13, "bold"),
                                  foreground="#2c3e50")
        self.p1_title.pack()

        # ── 玩家区域 ──
        pframe = ttk.LabelFrame(self.page1, text="玩家", padding=8)
        pframe.pack(fill=tk.X, padx=10, pady=3)
        pcenter = ttk.Frame(pframe)
        pcenter.pack(anchor=tk.CENTER)

        self.player_name_vars: list[tk.StringVar] = []
        self.player_score_vars: list[tk.IntVar]   = []
        self.landlord_btns: list[ttk.Button]      = []
        self.landlord_idx = -1

        for i in range(3):
            frame = ttk.Frame(pcenter)
            frame.pack(fill=tk.X, pady=3)

            # 头像圆圈（取名字前两字）
            avatar = tk.Label(frame, text=f"P{i+1}", width=3,
                              font=("Microsoft YaHei", 9),
                              bg="#E6F1FB", fg="#0C447C",
                              relief=tk.FLAT)
            avatar.pack(side=tk.LEFT, padx=(0, 6))
            avatar.configure(bg="#E6F1FB")

            name_var  = tk.StringVar(value=f"玩家{i+1}")
            score_var = tk.IntVar(value=0)

            entry = ttk.Entry(frame, textvariable=name_var, width=10,
                              font=("Microsoft YaHei", 14))
            entry.pack(side=tk.LEFT, padx=(0, 8))
            entry.bind("<FocusOut>", lambda e, idx=i: self._on_name_change(idx))

            ttk.Label(frame, textvariable=score_var, width=4,
                      style="Score.TLabel").pack(side=tk.LEFT)

            btn = ttk.Button(frame, text="设为地主", style="Action.TButton",
                             command=lambda idx=i: self._toggle_landlord(idx))
            btn.pack(side=tk.RIGHT, padx=5)

            self.landlord_btns.append(btn)
            self.player_name_vars.append(name_var)
            self.player_score_vars.append(score_var)

        # ── 番数 + 计分并排 ──
        mid = ttk.Frame(self.page1)
        mid.pack(fill=tk.X, padx=10, pady=3)

        # 左：番数
        ff = ttk.LabelFrame(mid, text="番数", padding=6)
        ff.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        fc = ttk.Frame(ff)
        fc.pack()
        self.fanshu_var = tk.IntVar(value=1)
        ttk.Label(fc, textvariable=self.fanshu_var, width=3,
                  style="Fanshu.TLabel").pack(side=tk.LEFT, padx=(2, 4))
        ttk.Button(fc, text="+1", style="Action.TButton",
                   command=lambda: self.fanshu_var.set(self.fanshu_var.get() + 1)
                   ).pack(side=tk.LEFT, padx=4)
        ttk.Button(fc, text="+2", style="Action.TButton",
                   command=lambda: self.fanshu_var.set(self.fanshu_var.get() + 2)
                   ).pack(side=tk.LEFT, padx=4)
        ttk.Button(fc, text="重置", style="Action.TButton",
                   command=self._reset_fanshu).pack(side=tk.LEFT, padx=4)

        # 右：计分（并排两个按钮填满）
        sf = ttk.LabelFrame(mid, text="计分", padding=6)
        sf.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))
        sc = ttk.Frame(sf)
        sc.pack(fill=tk.X)
        sc.grid_columnconfigure(0, weight=1)
        sc.grid_columnconfigure(1, weight=1)

        self.btn_landlord_win = self._make_button(
            sc, "地主赢", self._landlord_win,
            bg="#D85A30", active_bg="#c04a22",
            font_size=12, bold=True, padx=10, pady=6)
        self.btn_landlord_win.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.btn_farmer_win = self._make_button(
            sc, "农民赢", self._farmer_win,
            bg="#185FA5", active_bg="#124a80",
            font_size=12, bold=True, padx=10, pady=6)
        self.btn_farmer_win.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        # ── 底部操作（先 pack，确保始终可见）──
        bb = ttk.Frame(self.page1)
        bb.pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 6), padx=10)
        ttk.Separator(bb, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 4))
        br = ttk.Frame(bb)
        br.pack()

        self.btn_delete_round = self._make_button(
            br, "撤销最后小局", self._delete_last_round,
            bg="#f5f5f5", active_bg="#e0e0e0", fg="#555",
            font_size=10, padx=14, pady=3)
        self.btn_delete_round.pack(side=tk.LEFT, padx=5)

        self.btn_toggle_game = self._make_button(
            br, "开始新大局", self._toggle_game,
            bg="#2ecc71", active_bg="#27ae60",
            font_size=10, padx=14, pady=3)
        self.btn_toggle_game.pack(side=tk.LEFT, padx=5)

        # ── 小局历史 ──
        hf = ttk.LabelFrame(self.page1, text="小局历史", padding=5)
        hf.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)
        scrollbar = ttk.Scrollbar(hf)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_listbox = tk.Listbox(
            hf, height=8,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 12),
            relief=tk.FLAT, highlightthickness=0)
        self.history_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)

    def _build_page2(self):
        ttk.Label(self.page2, text="历史大局列表",
                  style="Title.TLabel").pack(anchor=tk.W, pady=(8, 5), padx=10)

        columns = ("name", "status", "scores")
        self.tree = ttk.Treeview(self.page2, columns=columns,
                                 show="headings", height=12)
        self.tree.heading("name",   text="名称")
        self.tree.heading("status", text="状态")
        self.tree.heading("scores", text="累计分")
        self.tree.column("name",   width=260)
        self.tree.column("status", width=80)
        self.tree.column("scores", width=260)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree.bind("<Double-1>",        self._on_tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        bf = ttk.Frame(self.page2)
        bf.pack(fill=tk.X, pady=5, padx=10)
        ttk.Separator(bf, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 5))
        br = ttk.Frame(bf)
        br.pack()

        self.btn_resume = self._make_button(
            br, "▶ 继续打", self._resume_selected,
            bg="#2ecc71", active_bg="#27ae60",
            font_size=10, padx=15, pady=4, state=tk.DISABLED)
        self.btn_resume.pack(side=tk.LEFT, padx=5)

        self.btn_delete = self._make_button(
            br, "🗑 删除", self._delete_selected,
            bg="#e74c3c", active_bg="#c0392b",
            font_size=10, padx=15, pady=4, state=tk.DISABLED)
        self.btn_delete.pack(side=tk.LEFT, padx=5)

        self.btn_detail = self._make_button(
            br, "📋 查看详情", self._detail_selected,
            bg="#3498db", active_bg="#2980b9",
            font_size=10, padx=15, pady=4, state=tk.DISABLED)
        self.btn_detail.pack(side=tk.LEFT, padx=5)

    # ========== 第一页交互 ==========

    def _toggle_landlord(self, idx: int):
        if not self.active_game:
            messagebox.showwarning("提示", "请先开始或继续一个大局", parent=self)
            return
        if self.landlord_idx == idx:
            self.landlord_idx = -1
            self.landlord_btns[idx].config(text="设为地主")
        else:
            if self.landlord_idx >= 0:
                self.landlord_btns[self.landlord_idx].config(text="设为地主")
            self.landlord_idx = idx
            self.landlord_btns[idx].config(text="👑 地主")

    def _reset_fanshu(self):
        self.fanshu_var.set(1)

    def _reset_after_score(self):
        self.fanshu_var.set(1)
        if self.landlord_idx >= 0:
            self.landlord_btns[self.landlord_idx].config(text="设为地主")
            self.landlord_idx = -1

    def _landlord_win(self):
        if not self._check_can_score():
            return
        fanshu   = self.fanshu_var.get()
        changes  = [0, 0, 0]
        changes[self.landlord_idx] = fanshu * 2
        self._record_round("地主", changes)

    def _farmer_win(self):
        if not self._check_can_score():
            return
        fanshu  = self.fanshu_var.get()
        changes = [fanshu if i != self.landlord_idx else 0 for i in range(3)]
        self._record_round("农民", changes)

    def _check_can_score(self) -> bool:
        if not self.active_game:
            messagebox.showwarning("提示", "请先开始或继续一个大局", parent=self)
            return False
        if self.landlord_idx < 0:
            messagebox.showwarning("提示", "请先选择地主", parent=self)
            return False
        return True

    def _record_round(self, winner: str, changes: list[int]):
        """记录一局得分，更新模型、持久化、刷新历史列表。"""
        if not self.active_game:
            return
        names  = [v.get() for v in self.player_name_vars]
        fanshu = self.fanshu_var.get()

        for i in range(3):
            self.active_game.scores[i] += changes[i]
            self.player_score_vars[i].set(self.active_game.scores[i])

        new_scores = {names[i]: self.active_game.scores[i] for i in range(3)}
        seq        = len(self.active_game.rounds) + 1
        round_data = SmallRound(
            seq=seq,
            landlord=names[self.landlord_idx],
            fanshu=fanshu,
            winner=winner,
            score_changes={names[i]: changes[i] for i in range(3)},
            scores_after=new_scores,
        )
        self.active_game.rounds.append(round_data)
        save_games(self.games)

        self.history_listbox.insert(tk.END, _format_round_line(round_data))
        self.history_listbox.see(tk.END)

        self._reset_after_score()

    def _delete_last_round(self):
        if not self.active_game or not self.active_game.rounds:
            messagebox.showinfo("提示", "没有小局记录可删除", parent=self)
            return
        if not messagebox.askyesno(
                "确认删除", "确定要删除最后一条小局记录吗？\n此操作不可撤销。", parent=self):
            return
        last = self.active_game.rounds.pop()
        for name, change in last.score_changes.items():
            for i in range(3):
                if self.active_game.players[i] == name:
                    self.active_game.scores[i] -= change
                    break
        save_games(self.games)
        self._refresh_page1()

    def _toggle_game(self):
        if self.active_game:
            self._finish_active_game()
        else:
            self._start_new_game()

    def _finish_active_game(self):
        if not self.active_game:
            return
        finish_game(self.games, self.active_game.name)
        self.active_game = None
        self._refresh_all()

    def _on_name_change(self, idx: int):
        if self.active_game:
            self.active_game.players[idx] = self.player_name_vars[idx].get()
            save_games(self.games)

    # ========== 第二页交互 ==========

    def _start_new_game(self):
        active = get_active_game(self.games)
        if active:
            if not messagebox.askyesno(
                    "提示",
                    f"当前「{active.name}」还未结束，是否结束并开始新大局？",
                    parent=self):
                return
            active.status = "已结束"

        last_players = self.games[-1].players[:] if self.games else ["玩家1", "玩家2", "玩家3"]
        now  = datetime.now().strftime("%Y-%m-%d %H:%M")
        game = BigGame(
            name=f"大局 #{len(self.games) + 1} {now}",
            players=last_players,
            status="进行中",
            rounds=[],
            created_at=now,
            scores=[0, 0, 0],
        )
        self.games.append(game)
        save_games(self.games)
        self.active_game = game
        self._refresh_all()
        self.notebook.select(0)

    def _get_selected_game(self) -> BigGame | None:
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0])["values"]
        if not values:
            return None
        return next((g for g in self.games if g.name == values[0]), None)

    def _on_tree_select(self, event=None):
        game = self._get_selected_game()
        if not game:
            self.btn_resume.config(state=tk.DISABLED)
            self.btn_delete.config(state=tk.DISABLED)
            self.btn_detail.config(state=tk.DISABLED)
            return
        self.btn_detail.config(state=tk.NORMAL)
        finished = game.status == "已结束"
        self.btn_resume.config(state=tk.NORMAL  if finished else tk.DISABLED)
        self.btn_delete.config(state=tk.NORMAL  if finished else tk.DISABLED)

    def _resume_selected(self):
        game = self._get_selected_game()
        if game:
            self._resume_game(game.name)

    def _delete_selected(self):
        game = self._get_selected_game()
        if game:
            self._delete_game(game.name)

    def _detail_selected(self):
        game = self._get_selected_game()
        if game:
            self._show_game_detail(game)

    # Double-click → 查看详情（与 _detail_selected 共享同一入口）
    def _on_tree_double_click(self, event):
        self._detail_selected()

    def _resume_game(self, name: str):
        active = get_active_game(self.games)
        if active:
            if not messagebox.askyesno(
                    "提示",
                    f"当前「{active.name}」还未结束，是否结束并继续「{name}」？",
                    parent=self):
                return
        resume_game(self.games, name)
        self.active_game = get_active_game(self.games)
        self._refresh_all()
        self.notebook.select(0)

    def _delete_game(self, name: str):
        if not messagebox.askyesno(
                "确认删除", f"确定要删除「{name}」吗？\n此操作不可撤销。", parent=self):
            return
        delete_game(self.games, name)
        if self.active_game and self.active_game.name == name:
            self.active_game = None
        self._refresh_all()

    def _finish_from_page2(self, name: str):
        finish_game(self.games, name)
        if self.active_game and self.active_game.name == name:
            self.active_game = None
        self._refresh_all()

    def _show_game_detail(self, game: BigGame):
        win = tk.Toplevel(self)
        win.title(game.name)
        win.geometry("550x450")
        text = tk.Text(win, wrap=tk.WORD, state=tk.NORMAL, font=("Consolas", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        lines = [
            f"大局: {game.name}",
            f"状态: {game.status}",
            f"玩家: {' / '.join(game.players)}",
            f"累计分: {'  '.join(f'{game.players[i]}:{game.scores[i]}' for i in range(3))}",
            f"创建时间: {game.created_at}",
            "=" * 50,
            f"共 {len(game.rounds)} 小局",
            "",
        ]
        for r in game.rounds:
            after = "  ".join(f"{k}:{v}" for k, v in r.scores_after.items())
            lines.append(f"#{r.seq} | 地主:{r.landlord} 番数:{r.fanshu} {r.winner}赢")
            lines.append(f"      变化: {'  '.join(f'{k}:{v:+d}' for k,v in r.score_changes.items())}")
            lines.append(f"      总分: {after}")
            lines.append("")

        text.insert(tk.END, "\n".join(lines))
        text.config(state=tk.DISABLED)

    # ========== 刷新 ==========

    def _refresh_page1(self):
        if self.active_game:
            self.p1_badge.config(text=self.active_game.status)
            self.p1_title.config(text=self.active_game.name)
            for i in range(3):
                self.player_name_vars[i].set(self.active_game.players[i])
                self.player_score_vars[i].set(self.active_game.scores[i])
        else:
            self.p1_badge.config(text="未开始")
            self.p1_title.config(text="无进行中的大局")
            for i in range(3):
                self.player_name_vars[i].set(f"玩家{i+1}")
                self.player_score_vars[i].set(0)

        self.landlord_idx = -1
        for btn in self.landlord_btns:
            btn.config(text="设为地主")
        self.fanshu_var.set(1)

        if self.active_game:
            self.btn_toggle_game.config(
                text="⏹ 结束大局", bg="#e67e22", activebackground="#d35400")
            self.btn_delete_round.config(state=tk.NORMAL)
        else:
            self.btn_toggle_game.config(
                text="▶ 开始新大局", bg="#2ecc71", activebackground="#27ae60")
            self.btn_delete_round.config(state=tk.DISABLED)

        self.history_listbox.delete(0, tk.END)
        if self.active_game:
            for r in self.active_game.rounds:
                self.history_listbox.insert(tk.END, _format_round_line(r))
            if self.active_game.rounds:
                self.history_listbox.see(tk.END)

    def _refresh_page2(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for g in self.games:
            scores_str = "  ".join(f"{g.players[i]}:{g.scores[i]}" for i in range(3))
            self.tree.insert("", tk.END, values=(g.name, g.status, scores_str))

    def _refresh_all(self):
        self._refresh_page1()
        self._refresh_page2()

    def run(self):
        self.mainloop()