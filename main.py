# -*- coding: utf-8 -*-
"""
タスクラベルツリー管理ツール
"""

import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import json
import os
import uuid
from datetime import datetime

# データファイルパス
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 状態の定義
STATUS_NOT_STARTED = "未着手"
STATUS_IN_PROGRESS = "実行中"
STATUS_COMPLETED = "完了"
STATUSES = [STATUS_NOT_STARTED, STATUS_IN_PROGRESS, STATUS_COMPLETED]

# 状態に対応する色
STATUS_COLORS = {
    STATUS_NOT_STARTED: "#6b7280",  # グレー
    STATUS_IN_PROGRESS: "#f59e0b",  # オレンジ
    STATUS_COMPLETED: "#10b981",    # グリーン
}


class TaskTreeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("タスクラベルツリー管理")
        self.geometry("1000x700")
        
        # テーマ設定
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # データ初期化
        self.tasks = {}  # id -> task_data
        self.current_file = None  # 現在開いているファイルパス
        
        # 現在選択中のタスクID
        self.selected_task_id = None
        
        # UI構築
        self.setup_ui()
        
        # ツリー更新
        self.refresh_tree()
        self.update_file_label()
    
    def setup_ui(self):
        """UIを構築"""
        # ファイル操作バー
        self.file_bar = ctk.CTkFrame(self)
        self.file_bar.pack(fill="x", padx=10, pady=(10, 5))
        
        self.new_file_btn = ctk.CTkButton(
            self.file_bar, text="新規作成", 
            command=self.new_file, width=100
        )
        self.new_file_btn.pack(side="left", padx=2)
        
        self.save_file_btn = ctk.CTkButton(
            self.file_bar, text="保存", 
            command=self.save_file, width=80
        )
        self.save_file_btn.pack(side="left", padx=2)
        
        self.save_as_btn = ctk.CTkButton(
            self.file_bar, text="名前を付けて保存", 
            command=self.save_file_as, width=130
        )
        self.save_as_btn.pack(side="left", padx=2)
        
        self.load_file_btn = ctk.CTkButton(
            self.file_bar, text="読み込み", 
            command=self.load_file, width=100
        )
        self.load_file_btn.pack(side="left", padx=2)
        
        # 区切り線
        self.separator = ctk.CTkLabel(self.file_bar, text="|", width=20)
        self.separator.pack(side="left", padx=5)
        
        # 現在のファイル名表示
        self.file_label = ctk.CTkLabel(
            self.file_bar, text="現在のファイル: (未保存)", 
            font=ctk.CTkFont(size=12)
        )
        self.file_label.pack(side="left", padx=10)
        
        # メインフレーム
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # 左側: ツリービュー
        self.left_frame = ctk.CTkFrame(self.main_frame)
        self.left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # ツリー操作ボタン
        self.tree_button_frame = ctk.CTkFrame(self.left_frame)
        self.tree_button_frame.pack(fill="x", pady=(0, 5))
        
        self.add_root_btn = ctk.CTkButton(
            self.tree_button_frame, text="＋ ルートタスク追加", 
            command=self.add_root_task, width=140
        )
        self.add_root_btn.pack(side="left", padx=2)
        
        self.add_child_btn = ctk.CTkButton(
            self.tree_button_frame, text="＋ 子タスク追加", 
            command=self.add_child_task, width=120
        )
        self.add_child_btn.pack(side="left", padx=2)
        
        self.delete_btn = ctk.CTkButton(
            self.tree_button_frame, text="削除", 
            command=self.delete_task, width=80,
            fg_color="#dc2626", hover_color="#b91c1c"
        )
        self.delete_btn.pack(side="left", padx=2)
        
        # ツリービュー用のフレーム（ttkを使用）
        self.tree_container = ctk.CTkFrame(self.left_frame)
        self.tree_container.pack(fill="both", expand=True)
        
        # スタイル設定
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                       background="#2b2b2b", 
                       foreground="white",
                       fieldbackground="#2b2b2b",
                       rowheight=28)
        style.configure("Treeview.Heading", 
                       background="#1f1f1f", 
                       foreground="white")
        style.map("Treeview", background=[("selected", "#1f6aa5")])
        
        # ツリービュー
        self.tree = ttk.Treeview(self.tree_container, columns=("status",), show="tree headings")
        self.tree.heading("#0", text="タスク名", anchor="w")
        self.tree.heading("status", text="状態", anchor="center")
        self.tree.column("#0", width=300, stretch=True)
        self.tree.column("status", width=80, stretch=False, anchor="center")
        
        # スクロールバー
        self.tree_scroll = ttk.Scrollbar(self.tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        
        # ツリー選択イベント
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        
        # 右側: 詳細パネル
        self.right_frame = ctk.CTkFrame(self.main_frame, width=350)
        self.right_frame.pack(side="right", fill="both", padx=(5, 0))
        self.right_frame.pack_propagate(False)
        
        # 詳細パネルのタイトル
        self.detail_title = ctk.CTkLabel(
            self.right_frame, text="タスク詳細", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.detail_title.pack(pady=10)
        
        # タスク名
        self.name_label = ctk.CTkLabel(self.right_frame, text="タスク名:")
        self.name_label.pack(anchor="w", padx=10)
        
        self.name_entry = ctk.CTkEntry(self.right_frame, width=300)
        self.name_entry.pack(padx=10, pady=(0, 10))
        
        # 状態選択
        self.status_label = ctk.CTkLabel(self.right_frame, text="状態:")
        self.status_label.pack(anchor="w", padx=10)
        
        self.status_var = ctk.StringVar(value=STATUS_NOT_STARTED)
        self.status_menu = ctk.CTkOptionMenu(
            self.right_frame, values=STATUSES, 
            variable=self.status_var, width=300
        )
        self.status_menu.pack(padx=10, pady=(0, 10))
        
        # メモセクション（折り畳み可能）
        self.memo_header_frame = ctk.CTkFrame(self.right_frame)
        self.memo_header_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        self.memo_toggle_btn = ctk.CTkButton(
            self.memo_header_frame, text="▼ メモ", 
            command=self.toggle_memo, width=100,
            fg_color="transparent", hover_color="#3b3b3b",
            anchor="w"
        )
        self.memo_toggle_btn.pack(side="left")
        
        self.memo_visible = True
        self.memo_frame = ctk.CTkFrame(self.right_frame)
        self.memo_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.memo_text = ctk.CTkTextbox(self.memo_frame, width=300, height=200)
        self.memo_text.pack(fill="both", expand=True)
        
        # 保存ボタン
        self.save_btn = ctk.CTkButton(
            self.right_frame, text="タスクを保存", 
            command=self.save_current_task, width=300
        )
        self.save_btn.pack(pady=10, padx=10)
        
        # 初期状態では詳細パネルを無効化
        self.set_detail_panel_state(False)
    
    def toggle_memo(self):
        """メモの表示/非表示を切り替え"""
        if self.memo_visible:
            self.memo_frame.pack_forget()
            self.memo_toggle_btn.configure(text="▶ メモ")
            self.memo_visible = False
        else:
            self.memo_frame.pack(fill="both", expand=True, padx=10, pady=5)
            self.memo_toggle_btn.configure(text="▼ メモ")
            self.memo_visible = True
    
    def set_detail_panel_state(self, enabled):
        """詳細パネルの有効/無効を切り替え"""
        state = "normal" if enabled else "disabled"
        self.name_entry.configure(state=state)
        self.status_menu.configure(state=state)
        self.memo_text.configure(state=state)
        self.save_btn.configure(state=state)
        
        if not enabled:
            self.name_entry.delete(0, "end")
            self.status_var.set(STATUS_NOT_STARTED)
            self.memo_text.delete("1.0", "end")
    
    def update_file_label(self):
        """現在のファイル名ラベルを更新"""
        if self.current_file:
            filename = os.path.basename(self.current_file)
            self.file_label.configure(text=f"現在のファイル: {filename}")
        else:
            self.file_label.configure(text="現在のファイル: (未保存)")
    
    def new_file(self):
        """新規作成"""
        if self.tasks:
            result = messagebox.askyesnocancel(
                "確認", 
                "現在のデータを保存しますか？"
            )
            if result is None:  # キャンセル
                return
            elif result:  # はい
                if not self.save_file():
                    return  # 保存がキャンセルされた場合は新規作成も中止
        
        self.tasks = {}
        self.current_file = None
        self.selected_task_id = None
        self.refresh_tree()
        self.set_detail_panel_state(False)
        self.update_file_label()
    
    def save_file(self):
        """保存（既存ファイルがあれば上書き、なければ名前を付けて保存）"""
        if self.current_file:
            self._save_to_file(self.current_file)
            return True
        else:
            return self.save_file_as()
    
    def save_file_as(self):
        """名前を付けて保存"""
        os.makedirs(DATA_DIR, exist_ok=True)
        
        filepath = filedialog.asksaveasfilename(
            initialdir=DATA_DIR,
            title="名前を付けて保存",
            defaultextension=".json",
            filetypes=[("JSONファイル", "*.json"), ("すべてのファイル", "*.*")]
        )
        
        if filepath:
            self._save_to_file(filepath)
            self.current_file = filepath
            self.update_file_label()
            return True
        return False
    
    def _save_to_file(self, filepath):
        """指定パスにデータを保存"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("完了", "保存しました")
        except IOError as e:
            messagebox.showerror("エラー", f"保存に失敗しました:\n{e}")
    
    def load_file(self):
        """ファイルを読み込み"""
        if self.tasks:
            result = messagebox.askyesnocancel(
                "確認", 
                "現在のデータを保存しますか？"
            )
            if result is None:  # キャンセル
                return
            elif result:  # はい
                if not self.save_file():
                    return
        
        os.makedirs(DATA_DIR, exist_ok=True)
        
        filepath = filedialog.askopenfilename(
            initialdir=DATA_DIR,
            title="ファイルを開く",
            filetypes=[("JSONファイル", "*.json"), ("すべてのファイル", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
                self.current_file = filepath
                self.selected_task_id = None
                self.refresh_tree()
                self.set_detail_panel_state(False)
                self.update_file_label()
            except (json.JSONDecodeError, IOError) as e:
                messagebox.showerror("エラー", f"読み込みに失敗しました:\n{e}")
    
    def refresh_tree(self):
        """ツリービューを更新"""
        # 既存のアイテムを削除
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # ルートタスクを取得して表示
        root_tasks = [
            (tid, data) for tid, data in self.tasks.items() 
            if data.get("parent_id") is None
        ]
        
        # 作成日時でソート
        root_tasks.sort(key=lambda x: x[1].get("created_at", ""))
        
        for task_id, task_data in root_tasks:
            self.insert_task_to_tree("", task_id, task_data)
    
    def insert_task_to_tree(self, parent_iid, task_id, task_data):
        """タスクをツリーに挿入（再帰的に子も挿入）"""
        status = task_data.get("status", STATUS_NOT_STARTED)
        
        # ツリーに挿入
        self.tree.insert(
            parent_iid, "end", iid=task_id,
            text=task_data.get("name", "無題"),
            values=(status,),
            open=True
        )
        
        # 子タスクを取得して挿入
        children = [
            (tid, data) for tid, data in self.tasks.items()
            if data.get("parent_id") == task_id
        ]
        children.sort(key=lambda x: x[1].get("created_at", ""))
        
        for child_id, child_data in children:
            self.insert_task_to_tree(task_id, child_id, child_data)
    
    def on_tree_select(self, event):
        """ツリーのアイテム選択時"""
        selection = self.tree.selection()
        if selection:
            task_id = selection[0]
            self.selected_task_id = task_id
            self.load_task_to_detail(task_id)
            self.set_detail_panel_state(True)
        else:
            self.selected_task_id = None
            self.set_detail_panel_state(False)
    
    def on_tree_double_click(self, event):
        """ツリーのダブルクリック時（インライン編集）"""
        # 今回はシンプルに詳細パネルでの編集のみ
        pass
    
    def load_task_to_detail(self, task_id):
        """タスクデータを詳細パネルに読み込み"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        
        self.name_entry.configure(state="normal")
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, task.get("name", ""))
        
        self.status_var.set(task.get("status", STATUS_NOT_STARTED))
        
        self.memo_text.configure(state="normal")
        self.memo_text.delete("1.0", "end")
        self.memo_text.insert("1.0", task.get("memo", ""))
    
    def save_current_task(self):
        """現在選択中のタスクを保存"""
        if self.selected_task_id is None:
            return
        
        if self.selected_task_id not in self.tasks:
            return
        
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("警告", "タスク名を入力してください")
            return
        
        self.tasks[self.selected_task_id]["name"] = name
        self.tasks[self.selected_task_id]["status"] = self.status_var.get()
        self.tasks[self.selected_task_id]["memo"] = self.memo_text.get("1.0", "end-1c")
        self.tasks[self.selected_task_id]["updated_at"] = datetime.now().isoformat()
        
        self.refresh_tree()
        
        # 選択状態を維持
        if self.selected_task_id in self.tasks:
            self.tree.selection_set(self.selected_task_id)
            self.tree.see(self.selected_task_id)
    
    def add_root_task(self):
        """ルートタスクを追加"""
        self.add_task(None)
    
    def add_child_task(self):
        """選択中のタスクの子タスクを追加"""
        if self.selected_task_id is None:
            messagebox.showinfo("情報", "親となるタスクを選択してください")
            return
        self.add_task(self.selected_task_id)
    
    def add_task(self, parent_id):
        """タスクを追加"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        self.tasks[task_id] = {
            "name": "新しいタスク",
            "status": STATUS_NOT_STARTED,
            "memo": "",
            "parent_id": parent_id,
            "created_at": now,
            "updated_at": now
        }
        
        self.refresh_tree()
        
        # 新しいタスクを選択
        self.tree.selection_set(task_id)
        self.tree.see(task_id)
        self.selected_task_id = task_id
        self.load_task_to_detail(task_id)
        self.set_detail_panel_state(True)
        
        # 名前入力にフォーカス
        self.name_entry.focus_set()
        self.name_entry.select_range(0, "end")
    
    def delete_task(self):
        """選択中のタスクを削除"""
        if self.selected_task_id is None:
            messagebox.showinfo("情報", "削除するタスクを選択してください")
            return
        
        # 子タスクがあるか確認
        children = [tid for tid, data in self.tasks.items() 
                   if data.get("parent_id") == self.selected_task_id]
        
        if children:
            result = messagebox.askyesno(
                "確認", 
                "このタスクには子タスクがあります。\n子タスクも含めて削除しますか？"
            )
            if not result:
                return
        else:
            result = messagebox.askyesno("確認", "このタスクを削除しますか？")
            if not result:
                return
        
        # 再帰的に削除
        self.delete_task_recursive(self.selected_task_id)
        
        self.refresh_tree()
        self.selected_task_id = None
        self.set_detail_panel_state(False)
    
    def delete_task_recursive(self, task_id):
        """タスクを再帰的に削除"""
        # 子タスクを先に削除
        children = [tid for tid, data in self.tasks.items() 
                   if data.get("parent_id") == task_id]
        for child_id in children:
            self.delete_task_recursive(child_id)
        
        # 自身を削除
        if task_id in self.tasks:
            del self.tasks[task_id]


if __name__ == "__main__":
    app = TaskTreeApp()
    app.mainloop()
