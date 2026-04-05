# -*- coding: utf-8 -*-
"""
ツールタブ
エディターによるsmb.conf直接編集機能とログファイル表示機能を提供するタブ。
"""

import os
import subprocess
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .. import constants as const
from .. import system_utils
from ..dialogs.log_viewer import show_log
from ..dialogs.password_dialog import ask_samba_password


class UserRow:
    """ユーザー1行分のUIとロジックを管理するクラス"""
    def __init__(self, parent, user_obj, row_idx, app, tab):
        self.user = user_obj
        self.app = app
        self.tab = tab
        
        # --- 1. ユーザー名 ---
        self.lbl_name = ttk.Label(parent, text=user_obj.username)
        self.lbl_name.grid(row=row_idx, column=0, padx=10, pady=5, sticky="w")

        # --- 2. ステータス（アイコン/色） ---
        self.status_var = tk.StringVar()
        # ttk.Labelではfgが直接使えないのでtk.Labelを利用するかttkのstyleを使う
        # ここではテーマ対応のためttk.Labelにして状態テキストのみにする
        self.lbl_status = ttk.Label(parent, textvariable=self.status_var, width=12, anchor="w")
        self.lbl_status.grid(row=row_idx, column=1, padx=5)

        # --- 3. 登録/解除 ---
        self.btn_main_var = tk.StringVar()
        self.btn_main = ttk.Button(parent, textvariable=self.btn_main_var, command=self.on_main_click, width=12)
        self.btn_main.grid(row=row_idx, column=2, padx=5)

        # --- 4. 有効/無効 ---
        self.btn_switch_var = tk.StringVar()
        self.btn_switch = ttk.Button(parent, textvariable=self.btn_switch_var, command=self.on_switch_click, width=12)
        self.btn_switch.grid(row=row_idx, column=3, padx=10)

        self.update_ui()

    def update_ui(self):
        """状態に基づいてUI表示を更新"""
        from ..system_utils import SAMBA_STATUS_UNREGISTERED, SAMBA_STATUS_ENABLED, SAMBA_STATUS_DISABLED
        
        status = self.user.samba_status
        if status == SAMBA_STATUS_UNREGISTERED:
            self.status_var.set("[-] 未登録")
            self.btn_main_var.set("登録する")
            self.btn_switch_var.set("----")
            self.btn_switch.state(["disabled"])

        elif status == SAMBA_STATUS_ENABLED:
            self.status_var.set("[✔] 有効")
            self.btn_main_var.set("登録解除")
            self.btn_switch_var.set("無効にする")
            self.btn_switch.state(["!disabled"])

        elif status == SAMBA_STATUS_DISABLED:
            self.status_var.set("[❌] 無効")
            self.btn_main_var.set("登録解除")
            self.btn_switch_var.set("有効にする")
            self.btn_switch.state(["!disabled"])

    def _trigger_reload(self):
        # 画面のちらつきやコールバック中の破壊を避けるため遅延リロード
        self.tab.after(100, self.app.refresh_samba_cache_and_reload)

    def _run_helper(self, cmd_args):
        helper_path = const.get_helper_path()
        return subprocess.run(
            ["pkexec", helper_path] + cmd_args,
            capture_output=True, text=True, timeout=30
        )

    def on_main_click(self):
        """登録/解除ボタンが押されたとき"""
        from ..system_utils import SAMBA_STATUS_UNREGISTERED, SAMBA_STATUS_ENABLED
        username = self.user.username
        
        if self.user.samba_status == SAMBA_STATUS_UNREGISTERED:
            # 登録処理
            password = ask_samba_password(self.tab, username)
            if password is None:
                return
            
            helper_path = const.get_helper_path()
            try:
                # パスワードをstdinに渡すため直接subprocess.run
                result = subprocess.run(
                    ["pkexec", helper_path, "add-samba-user", username],
                    input=f"{password}\n{password}\n",
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    self.user.samba_status = SAMBA_STATUS_ENABLED
                    self.app.update_samba_user_cache(username, SAMBA_STATUS_ENABLED)
                    messagebox.showinfo("成功", f"ユーザー '{username}' をSambaに登録しました", parent=self.tab)
                    self._trigger_reload()
                else:
                    messagebox.showerror("エラー", f"登録に失敗しました:\n{result.stderr}", parent=self.tab)
            except Exception as e:
                messagebox.showerror("エラー", f"登録処理中にエラーが発生しました:\n{e}", parent=self.tab)

        else:
            # 解除処理
            if not messagebox.askyesno("確認", f"ユーザー '{username}' のSamba登録を解除しますか？\n(Sambaへのアクセスができなくなります)", parent=self.tab):
                return
            try:
                result = self._run_helper(["remove-samba-user", username])
                if result.returncode == 0:
                    self.user.samba_status = SAMBA_STATUS_UNREGISTERED
                    self.app.update_samba_user_cache(username, SAMBA_STATUS_UNREGISTERED)
                    messagebox.showinfo("成功", f"ユーザー '{username}' の登録を解除しました", parent=self.tab)
                    self._trigger_reload()
                else:
                    messagebox.showerror("エラー", f"解除に失敗しました:\n{result.stderr}", parent=self.tab)
            except Exception as e:
                messagebox.showerror("エラー", f"解除処理中にエラーが発生しました:\n{e}", parent=self.tab)
                
        self.update_ui()

    def on_switch_click(self):
        """スイッチ(有効/無効)が押されたとき"""
        from ..system_utils import SAMBA_STATUS_ENABLED, SAMBA_STATUS_DISABLED
        username = self.user.username
        
        try:
            if self.user.samba_status == SAMBA_STATUS_ENABLED:
                # 無効化
                result = self._run_helper(["disable-samba-user", username])
                if result.returncode == 0:
                    self.user.samba_status = SAMBA_STATUS_DISABLED
                    self.app.update_samba_user_cache(username, SAMBA_STATUS_DISABLED)
                    self._trigger_reload()
                else:
                    messagebox.showerror("エラー", f"無効化に失敗しました:\n{result.stderr}", parent=self.tab)
            elif self.user.samba_status == SAMBA_STATUS_DISABLED:
                # 有効化
                result = self._run_helper(["enable-samba-user", username])
                if result.returncode == 0:
                    self.user.samba_status = SAMBA_STATUS_ENABLED
                    self.app.update_samba_user_cache(username, SAMBA_STATUS_ENABLED)
                    self._trigger_reload()
                else:
                    messagebox.showerror("エラー", f"有効化に失敗しました:\n{result.stderr}", parent=self.tab)
        except Exception as e:
            messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n{e}", parent=self.tab)

        self.update_ui()


class ToolsTab(ttk.Frame):
    """ツールタブ"""

    def __init__(self, parent: tk.Widget, app):
        """タブを初期化する"""
        super().__init__(parent, padding=10)
        self._app = app

        # UIを構築
        self._build_ui()

    def _build_ui(self) -> None:
        """UIウィジェットを構築する"""
        # 全体をスクロール可能にするためのキャンバス
        main_canvas = tk.Canvas(self, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.bind(
            "<Configure>",
            lambda e: main_canvas.itemconfig(canvas_window, width=e.width)
        )
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._build_user_management_section(scrollable_frame)
        self._build_direct_edit_section(scrollable_frame)
        self._build_log_section(scrollable_frame)

    def _build_user_management_section(self, parent: tk.Widget) -> None:
        """Sambaユーザー管理セクションを構築する"""
        users_frame = ttk.LabelFrame(parent, text="Sambaユーザー管理", padding=10)
        users_frame.pack(fill=tk.X, pady=(0, 15), padx=5)

        self._user_list_frame = ttk.Frame(users_frame)
        self._user_list_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(self._user_list_frame, text="ユーザー名", width=15).grid(row=0, column=0, sticky="w", padx=(10, 0))
        ttk.Label(self._user_list_frame, text="状態", width=12).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(self._user_list_frame, text="登録/解除", width=12).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Label(self._user_list_frame, text="有効/無効", width=12).grid(row=0, column=3, sticky="w", padx=10)
        ttk.Separator(self._user_list_frame, orient="horizontal").grid(row=1, column=0, columnspan=4, sticky="ew", pady=(5, 5))

    def _build_direct_edit_section(self, parent: tk.Widget) -> None:
        """設定ファイルの直接編集セクションを構築する"""
        edit_frame = ttk.LabelFrame(parent, text="設定ファイルの直接編集", padding=10)
        edit_frame.pack(fill=tk.X, pady=(0, 15), padx=5)

        editor_row = ttk.Frame(edit_frame)
        editor_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(editor_row, text="使用するエディター:").pack(side=tk.LEFT, padx=(0, 5))
        
        self._editor_var = tk.StringVar(value=self._app.config_manager.get("editor", const.DEFAULT_EDITOR))
        ttk.Entry(editor_row, textvariable=self._editor_var, width=20).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(editor_row, text="確認", width=8, command=self._check_editor).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(editor_row, text="エディターで編集", width=14, command=self._direct_edit).pack(side=tk.LEFT)

        ttk.Label(
            edit_frame,
            text="[エディターで編集]をクリックすると、指定したエディターでsmb.confを編集できます。\n"
                 "エディター終了後、変更があれば構文チェック→適用を実行します。",
            font=("", 9), foreground="gray"
        ).pack(anchor=tk.W)

    def _build_log_section(self, parent: tk.Widget) -> None:
        """ログファイルセクションを構築する"""
        log_frame = ttk.LabelFrame(parent, text="ログファイル", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        logdir_row = ttk.Frame(log_frame)
        logdir_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(logdir_row, text="ログディレクトリ:").pack(side=tk.LEFT, padx=(0, 5))
        
        self._logdir_var = tk.StringVar(value=self._app.config_manager.get("log_dir", const.DEFAULT_LOG_DIR))
        ttk.Entry(logdir_row, textvariable=self._logdir_var, width=35).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(logdir_row, text="参照", width=5, command=self._browse_logdir).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(logdir_row, text="更新", width=5, command=self._refresh_log_list).pack(side=tk.LEFT)

        ttk.Label(log_frame, text="ログファイル:").pack(anchor=tk.W, pady=(0, 5))

        log_list_frame = ttk.Frame(log_frame)
        log_list_frame.pack(fill=tk.BOTH, expand=True)

        self._log_canvas = tk.Canvas(log_list_frame, highlightthickness=0)
        log_scrollbar = ttk.Scrollbar(log_list_frame, orient=tk.VERTICAL, command=self._log_canvas.yview)
        
        self._log_scrollable = ttk.Frame(self._log_canvas)
        self._log_scrollable.bind("<Configure>", lambda e: self._log_canvas.configure(scrollregion=self._log_canvas.bbox("all")))
        
        self._log_canvas_window = self._log_canvas.create_window((0, 0), window=self._log_scrollable, anchor="nw")
        self._log_canvas.configure(yscrollcommand=log_scrollbar.set)
        self._log_canvas.bind("<Configure>", self._on_log_canvas_configure)

        self._log_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self._refresh_log_list()

    def _on_log_canvas_configure(self, event) -> None:
        self._log_canvas.itemconfig(self._log_canvas_window, width=event.width)

    def _check_editor(self) -> None:
        """エディターの存在確認を行う"""
        editor = self._editor_var.get().strip()
        if not editor:
            messagebox.showwarning("入力エラー", "エディター名を入力してください", parent=self)
            return

        if system_utils.check_command_exists(editor):
            messagebox.showinfo("確認結果", f"'{editor}' はインストールされています ✓", parent=self)
            self._app.config_manager.set("editor", editor)
            self._app.config_manager.save()
        else:
            messagebox.showwarning(
                "確認結果",
                f"'{editor}' はインストールされていません ✗\n\n"
                f"sudo apt install {editor} でインストールしてください",
                parent=self
            )

    def _direct_edit(self) -> None:
        """エディターで直接編集を実行する"""
        editor = self._editor_var.get().strip()
        if not editor:
            messagebox.showwarning("入力エラー", "エディター名を入力してください", parent=self)
            return

        if not system_utils.check_command_exists(editor):
            messagebox.showerror(
                "エラー",
                f"エディター '{editor}' がインストールされていません",
                parent=self
            )
            return

        # 一時ファイルにsmb.confをコピー
        try:
            tmp_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.conf', prefix='smb_edit_',
                delete=False, dir=tempfile.gettempdir()
            )
            tmp_path = tmp_file.name
            tmp_file.close()
        except Exception as e:
            messagebox.showerror("エラー", f"一時ファイルの作成に失敗: {e}", parent=self)
            return

        # ヘルパースクリプトでsmb.confを一時ファイルにコピー
        helper_path = const.get_helper_path()
        try:
            result = subprocess.run(
                ["pkexec", helper_path, "copy-conf", tmp_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                messagebox.showerror("エラー", f"smb.confのコピーに失敗: {result.stderr}", parent=self)
                self._cleanup_temp(tmp_path)
                return
        except Exception as e:
            messagebox.showerror("エラー", f"smb.confのコピーに失敗: {e}", parent=self)
            self._cleanup_temp(tmp_path)
            return

        # 編集前の内容を保持
        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except IOError as e:
            messagebox.showerror("エラー", f"ファイルの読み取りに失敗: {e}", parent=self)
            self._cleanup_temp(tmp_path)
            return

        # エディターを起動
        messagebox.showinfo(
            "エディターで編集",
            f"エディター '{editor}' で smb.conf を開きます。\n"
            "編集が完了したらファイルを保存してエディターを閉じてください。",
            parent=self
        )

        try:
            subprocess.run([editor, tmp_path], timeout=3600)
        except subprocess.TimeoutExpired:
            messagebox.showwarning("タイムアウト", "エディターがタイムアウトしました", parent=self)
            self._cleanup_temp(tmp_path)
            return
        except Exception as e:
            messagebox.showerror("エラー", f"エディターの起動に失敗: {e}", parent=self)
            self._cleanup_temp(tmp_path)
            return

        # 編集後の内容を読み取り
        try:
            with open(tmp_path, "r", encoding="utf-8") as f:
                edited_content = f.read()
        except IOError as e:
            messagebox.showerror("エラー", f"編集後のファイルの読み取りに失敗: {e}", parent=self)
            self._cleanup_temp(tmp_path)
            return

        if original_content == edited_content:
            messagebox.showinfo("エディターで編集", "変更はありませんでした", parent=self)
            self._cleanup_temp(tmp_path)
            return

        confirm = messagebox.askyesno(
            "変更の適用",
            "smb.confが編集されました。変更を適用しますか？\n\n"
            "（構文チェック後に適用されます）",
            parent=self
        )
        if not confirm:
            self._cleanup_temp(tmp_path)
            return

        # 適用処理を実行
        result = self._app.apply_manager.apply_changes(
            new_conf_content=edited_content,
            category=const.CATEGORY_DIRECT_EDIT,
            comment="エディターで直接編集"
        )

        if result.success:
            messagebox.showinfo("完了", result.message, parent=self)
            self._app.reload_data()
        else:
            error_msg = "\n".join(result.errors)
            messagebox.showerror("エラー", f"適用に失敗しました:\n\n{error_msg}", parent=self)

        self._cleanup_temp(tmp_path)

    def _browse_logdir(self) -> None:
        initial_dir = self._logdir_var.get() or const.DEFAULT_LOG_DIR
        if not os.path.isdir(initial_dir):
            initial_dir = "/"
        selected = filedialog.askdirectory(
            parent=self, title="ログディレクトリの選択", initialdir=initial_dir
        )
        if selected:
            self._logdir_var.set(selected)
            self._app.config_manager.set("log_dir", selected)
            self._app.config_manager.save()
            self._refresh_log_list()

    def _refresh_log_list(self) -> None:
        """ログファイル一覧を更新する"""
        for widget in self._log_scrollable.winfo_children():
            widget.destroy()

        log_dir = self._logdir_var.get().strip()
        if not log_dir or not os.path.isdir(log_dir):
            ttk.Label(
                self._log_scrollable, text="ログディレクトリが見つかりません",
                foreground="gray"
            ).pack(anchor=tk.W, pady=5)
            return

        log_files = system_utils.get_log_files(log_dir)
        if not log_files:
            ttk.Label(
                self._log_scrollable, text="ログファイルがありません",
                foreground="gray"
            ).pack(anchor=tk.W, pady=5)
            return

        for filename in log_files:
            row = ttk.Frame(self._log_scrollable)
            row.pack(fill=tk.X, pady=1)

            ttk.Label(row, text=f"📄 {filename}", width=35, anchor=tk.W).pack(side=tk.LEFT)

            filepath = os.path.join(log_dir, filename)
            try:
                size = os.path.getsize(filepath)
                size_str = self._format_size(size)
            except OSError:
                size_str = "不明"
            ttk.Label(row, text=size_str, width=10, foreground="gray").pack(side=tk.LEFT, padx=(5, 0))

            ttk.Button(
                row, text="内容表示", width=10,
                command=lambda fp=filepath, fn=filename: self._show_log(fp, fn)
            ).pack(side=tk.LEFT, padx=(10, 0))

    def _show_log(self, filepath: str, filename: str) -> None:
        show_log(self, filepath, title=f"ログビューアー - {filename}")

    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def _cleanup_temp(self, filepath: str) -> None:
        try:
            if filepath and os.path.exists(filepath):
                os.unlink(filepath)
        except IOError:
            pass

    def load_data(self) -> None:
        # Sambaユーザー管理の行を再生成
        # row=0と1はヘッダー・セパレーターなので残す
        for widget in self._user_list_frame.winfo_children():
            info = widget.grid_info()
            if "row" in info and int(info["row"]) >= 2:
                widget.destroy()
            
        for i, user in enumerate(self._app._users):
            UserRow(self._user_list_frame, user, i + 2, self._app, self)

        self._refresh_log_list()
        self._editor_var.set(
            self._app.config_manager.get("editor", const.DEFAULT_EDITOR)
        )
        self._logdir_var.set(
            self._app.config_manager.get("log_dir", const.DEFAULT_LOG_DIR)
        )
