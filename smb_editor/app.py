# -*- coding: utf-8 -*-
"""
メインアプリケーションモジュール
tkinter.ttk + sv_ttk (Sun Valleyテーマ) によるGUIアプリケーション。
4つのタブ（共有設定、サーバー設定、ツール、バックアップ）を管理する。
[適用]ボタンはタブ上段に配置し、共有設定+サーバー設定を一括で適用する。
"""

import os
import subprocess
import sys
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

try:
    import sv_ttk
except ImportError:
    sv_ttk = None

from . import constants as const
from .config_manager import ConfigManager
from .backup_manager import BackupManager
from .apply_manager import ApplyManager
from .smb_parser import SmbConfParser, SmbConfig
from .smb_writer import SmbConfWriter
from . import system_utils
from .tabs.shares_tab import SharesTab
from .tabs.server_tab import ServerTab
from .tabs.tools_tab import ToolsTab
from .tabs.backup_tab import BackupTab


class SmbConfEditorApp:
    """Samba設定エディター メインアプリケーションクラス"""

    def __init__(self):
        """アプリケーションを初期化する"""
        # tkinter ルートウィンドウを作成
        self._root = tk.Tk(className="smb-conf-editor")
        self._root.title(f"{const.APP_NAME} v{const.APP_VERSION}")
        self._root.geometry(f"{const.WINDOW_WIDTH}x{const.WINDOW_HEIGHT}")
        self._root.minsize(800, 600)

        # マネージャーの初期化
        self._config_manager = ConfigManager()

        # ウィンドウアイコンの設定
        self._set_window_icon()

        # Sun Valley テーマを適用（config.jsonの読み込み後に実行）
        self._apply_theme()

        self._parser = SmbConfParser()
        self._config: SmbConfig = None  # パース済みのsmb.conf
        self._users = []     # システムユーザー一覧
        self._samba_users_cache: dict[str, int] = {}  # {username: samba_status} キャッシュ
        self._samba_users_loaded = False  # キャッシュ済みフラグ

        # バックアップマネージャーの初期化
        backup_dir = self._config_manager.get_backup_dir()
        max_backups = self._config_manager.get("max_backups", const.DEFAULT_MAX_BACKUPS)
        self._backup_manager = BackupManager(backup_dir, max_backups)

        # 適用マネージャーの初期化
        self._apply_manager = ApplyManager(self._config_manager, self._backup_manager)

        # 初回起動チェック
        if not self._startup_checks():
            return

        # UIを構築
        self._build_ui()

        # 閉じるボタンのイベントをフック
        self._root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # データを読み込む
        self.reload_data()

    def _set_window_icon(self) -> None:
        """ウィンドウのアイコンを設定する"""
        try:
            prod_icon_path = "/usr/share/pixmaps/smb-conf-editor.png"
            dev_icon_path = os.path.join(const.get_app_dir(), "packaging", "smb-conf-editor.png")
            icon_path = prod_icon_path if os.path.exists(prod_icon_path) else dev_icon_path
            
            if os.path.exists(icon_path):
                img = tk.PhotoImage(file=icon_path)
                self._root.iconphoto(True, img)
        except Exception as e:
            print(f"アイコンの設定に失敗しました: {e}")

    def _detect_os_theme(self) -> str:
        """システムのダーク/ライト設定を検出する"""
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                output = result.stdout.strip().strip("'")
                if "dark" in output:
                    return "dark"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        # 検出できない場合はライトをデフォルトにする
        return "light"

    def _apply_theme(self) -> None:
        """Sun Valley テーマを適用する（保存済み設定 > OS設定 > ライト）"""
        if sv_ttk is not None:
            saved_theme = self._config_manager.get("theme", None)
            if saved_theme in ("dark", "light"):
                theme = saved_theme
            else:
                theme = self._detect_os_theme()
                self._config_manager.set("theme", theme)
                self._config_manager.save()
            sv_ttk.set_theme(theme)
        else:
            print("警告: sv_ttk がインストールされていません。デフォルトテーマを使用します。")

    def _startup_checks(self) -> bool:
        """初回起動時のチェックを行う"""
        errors = []

        # Sambaの必要コマンドがインストールされているか確認
        cmd_status = system_utils.check_samba_installed()
        for cmd, installed in cmd_status.items():
            if not installed:
                errors.append(f"コマンド '{cmd}' がインストールされていません")

        # smb.confが存在するか確認
        if not system_utils.check_smb_conf_exists():
            from .messages import MSGS
            errors.append(MSGS.ERR_CONF_NOT_FOUND.format(path=const.SMB_CONF_PATH))

        # ヘルパースクリプトが存在するか確認
        helper_path = const.get_helper_path()
        if not os.path.isfile(helper_path):
            from .messages import MSGS
            errors.append(MSGS.ERR_HELPER_NOT_FOUND.format(path=helper_path))
        else:
            if not os.access(helper_path, os.X_OK):
                try:
                    os.chmod(helper_path, 0o755)
                except OSError:
                    errors.append(f"ヘルパースクリプトに実行権限を付与できません: {helper_path}")

        if errors:
            error_msg = "\n".join(f"・{e}" for e in errors)
            messagebox.showwarning(
                "起動チェック",
                f"以下の問題が検出されました:\n\n{error_msg}\n\n"
                "一部の機能が正しく動作しない可能性があります。",
                parent=self._root
            )

        return True

    def _build_ui(self) -> None:
        """UIウィジェットを構築する"""
        # メニューバーを構築
        self._build_menubar()

        main_frame = ttk.Frame(self._root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._build_toolbar(main_frame)
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=3)
        self._build_notebook(main_frame)
        self._build_statusbar()

    def _build_menubar(self) -> None:
        """メニューバーを構築する"""
        menubar = tk.Menu(self._root)
        self._root.config(menu=menubar)

        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="バージョン情報", command=self._show_about_dialog)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)

    def _build_toolbar(self, parent: tk.Widget) -> None:
        """上部のツールバー（適用ボタンなど）を構築する"""
        from .messages import UI
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=(5, 0))

        # 適用ボタンを Accent.TButton スタイルで目立たせる
        self._apply_btn = ttk.Button(toolbar, text=UI.BTN_APPLY, command=self._on_apply_all, style="Accent.TButton")
        self._apply_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(
            toolbar,
            text=UI.DESC_APP_APPLY,
            font=("", 9), foreground="gray"
        ).pack(side=tk.LEFT)

        self._theme_btn = ttk.Button(toolbar, text=UI.BTN_THEME, width=10, command=self._toggle_theme)
        self._theme_btn.pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(toolbar, text=UI.BTN_RELOAD, width=12, command=self.reload_data).pack(side=tk.RIGHT, padx=(5, 0))

    def _build_notebook(self, parent: tk.Widget) -> None:
        """メインのタブ（ノートブック）エリアを構築する"""
        from .messages import UI
        self._notebook = ttk.Notebook(parent)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        self._shares_tab = SharesTab(self._notebook, self)
        self._server_tab = ServerTab(self._notebook, self)
        self._tools_tab = ToolsTab(self._notebook, self)
        self._backup_tab = BackupTab(self._notebook, self)

        self._notebook.add(self._shares_tab, text=UI.TAB_SHARES)
        self._notebook.add(self._server_tab, text=UI.TAB_GLOBAL)
        self._notebook.add(self._tools_tab, text=UI.TAB_ADVANCED)
        self._notebook.add(self._backup_tab, text=UI.TAB_HISTORY)

    def _build_statusbar(self) -> None:
        """下部のステータスバーを構築する"""
        status_frame = ttk.Frame(self._root)
        status_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        self._status_label = ttk.Label(status_frame, text=f"設定ファイル: {const.SMB_CONF_PATH}", font=("", 9))
        self._status_label.pack(side=tk.LEFT)

    def _on_apply_all(self) -> None:
        """
        統合[適用]ボタンの処理。
        共有設定タブとサーバー設定タブの変更をまとめてsmb.confに適用する。
        パスワード入力は1回のみ（apply-allバッチコマンド使用）。
        """
        # Writerを作成（現在のsmb.configベース）
        writer = SmbConfWriter(self._config)

        # === 共有設定タブの変更を収集 ===
        shares_result = self._shares_tab.collect_changes(writer)
        if shares_result is None:
            # バリデーションエラー → 中断
            return

        # === サーバー設定タブの変更を収集 ===
        server_result = self._server_tab.collect_changes(writer)
        if server_result is None:
            # バリデーションエラー → 中断
            return

        # === 変更後の内容を生成 ===
        new_content = writer.generate_content()

        # === 各種変更データの取得と差分チェック ===
        samba_users = shares_result.get("samba_users", [])
        new_dirs = shares_result.get("new_dirs", [])
        enable_users = shares_result.get("enable_users", [])
        current_content = self._apply_manager.read_current_conf() or ""

        if not samba_users and not new_dirs and not enable_users and new_content.strip() == current_content.strip():
            messagebox.showinfo("適用", "設定に変更がありません。", parent=self._root)
            return

        # === バックアップコメントを自動生成 ===
        comment_parts = shares_result.get("comment_parts", [])
        if comment_parts:
            auto_comment = "共有設定/サーバー設定の変更: " + "、".join(comment_parts)
        else:
            auto_comment = "共有設定/サーバー設定の変更"

        # === 適用処理を実行（1回のpkexec） ===
        result = self._apply_manager.apply_changes(
            new_conf_content=new_content,
            category=const.CATEGORY_SHARE,
            comment=auto_comment,
            samba_users_to_add=samba_users if samba_users else None,
            new_share_dirs=new_dirs if new_dirs else None,
            enable_users=enable_users if enable_users else None
        )

        if result.success:
            # Sambaユーザーを追加/有効化した場合、キャッシュを更新
            if samba_users:
                for u in samba_users:
                    username = u.get("username", "")
                    if username:
                        self._samba_users_cache[username] = system_utils.SAMBA_STATUS_ENABLED
            # 無効→有効に変更されたユーザー分もキャッシュ更新
            enable_users = shares_result.get("enable_users", [])
            for username in enable_users:
                self._samba_users_cache[username] = system_utils.SAMBA_STATUS_ENABLED
            # 実行されたステップを表示
            steps_msg = ""
            if result.steps:
                steps_msg = "\n\n実行結果:\n" + "\n".join(f"  ✓ {s}" for s in result.steps)
            if result.errors:
                steps_msg += "\n\n注意:\n" + "\n".join(f"  ⚠ {e}" for e in result.errors)
            messagebox.showinfo("完了", f"{result.message}{steps_msg}", parent=self._root)
            self.reload_data()
        else:
            error_msg = "\n".join(result.errors)
            messagebox.showerror("エラー", f"適用に失敗しました:\n\n{error_msg}", parent=self._root)

    def _on_closing(self) -> None:
        """アプリ終了時の処理"""
        has_changes = False
        
        # 共有タブの簡易チェック（削除待ち、または新規入力中のカードがあるか）
        if hasattr(self, '_shares_tab'):
            for card in self._shares_tab._cards:
                if card.is_deleted or (card.is_new and not card.is_empty):
                    has_changes = True
                    break
        
        if has_changes:
            if not messagebox.askyesno(
                "確認", 
                "未適用の変更があります。\n破棄して終了しますか？", 
                parent=self._root,
                icon=messagebox.WARNING
            ):
                return
                
        self._root.destroy()

    def reload_data(self) -> None:
        """smb.confを再パースして全タブのデータを更新する"""
        try:
            self._config = self._parser.parse(const.SMB_CONF_PATH)
        except (IOError, PermissionError) as e:
            content = self._apply_manager.read_current_conf()
            if content:
                self._config = self._parser.parse_string(content, const.SMB_CONF_PATH)
            else:
                messagebox.showerror(
                    "エラー",
                    f"smb.confの読み取りに失敗しました:\n{e}",
                    parent=self._root
                )
                return

        # ユーザー一覧を取得（Sambaユーザー情報は起動時のみpkexecで取得）
        users = system_utils.get_system_users()
        if not self._samba_users_loaded:
            # 初回のみpkexecでSambaユーザー一覧を取得してキャッシュ
            helper_path = const.get_helper_path()
            try:
                self._samba_users_cache = system_utils.get_samba_users_with_status(helper_path)
                self._samba_users_loaded = True
            except Exception as e:
                print(f"警告: Sambaユーザー一覧の取得に失敗: {e}")
                self._samba_users_cache = {}
        # キャッシュからSambaユーザーステータスを設定
        for user in users:
            user.samba_status = self._samba_users_cache.get(
                user.username, system_utils.SAMBA_STATUS_UNREGISTERED
            )
        self._users = users

        # 各タブにデータを配信
        self._shares_tab.load_data(self._config, self._users)
        self._server_tab.load_data(self._config)
        self._tools_tab.load_data()
        self._backup_tab.load_data()

        # ステータスバーを更新
        section_count = len(self._config.sections)
        share_count = len(SmbConfParser.get_share_sections(self._config))
        self._status_label.config(
            text=f"設定ファイル: {const.SMB_CONF_PATH}  |  "
                 f"セクション数: {section_count}  |  "
                 f"共有フォルダ数: {share_count}"
        )

    def _toggle_theme(self) -> None:
        """ダーク/ライトテーマを切り替える"""
        if sv_ttk is not None:
            current = sv_ttk.get_theme()
            new_theme = "light" if current == "dark" else "dark"
            sv_ttk.set_theme(new_theme)
            self._config_manager.set("theme", new_theme)
            self._config_manager.save()

    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager

    @property
    def backup_manager(self) -> BackupManager:
        return self._backup_manager

    @property
    def apply_manager(self) -> ApplyManager:
        return self._apply_manager

    def update_samba_user_cache(self, username: str, status: int) -> None:
        """Sambaユーザーキャッシュを更新する（ツールタブ等から呼ばれる）"""
        if status == system_utils.SAMBA_STATUS_UNREGISTERED:
            self._samba_users_cache.pop(username, None)
        else:
            self._samba_users_cache[username] = status

    def refresh_samba_cache_and_reload(self) -> None:
        """Samba設定および全タブをキャッシュ情報を維持したまま再描画する"""
        self.reload_data()

    def _show_about_dialog(self) -> None:
        """バージョン情報ダイアログを表示する"""
        about_win = tk.Toplevel(self._root)
        about_win.title("バージョン情報")
        about_win.geometry("520x480")
        about_win.resizable(False, False)
        about_win.transient(self._root)
        about_win.grab_set()

        # メインフレーム
        main_frame = ttk.Frame(about_win, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # アプリ名とバージョン
        ttk.Label(
            main_frame,
            text=const.APP_NAME,
            font=("", 18, "bold")
        ).pack(pady=(0, 5))
        ttk.Label(
            main_frame,
            text=f"v{const.APP_VERSION}",
            font=("", 12)
        ).pack(pady=(0, 3))
        ttk.Label(
            main_frame,
            text=f"ライセンス: {const.APP_LICENSE}",
            font=("", 9), foreground="gray"
        ).pack(pady=(0, 15))

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 情報セクション
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))

        # 各情報行を表示するヘルパー関数
        def add_info_row(parent, label_text, value_text, row):
            """1行分の情報をGridで配置する"""
            ttk.Label(parent, text=label_text, font=("", 9, "bold")).grid(
                row=row, column=0, sticky="nw", padx=(0, 10), pady=3
            )
            ttk.Label(parent, text=value_text, font=("", 9), wraplength=350).grid(
                row=row, column=1, sticky="w", pady=3
            )

        # 情報行を追加
        add_info_row(info_frame, "設定ファイル:", self._config_manager.config_path, 0)
        add_info_row(info_frame, "バックアップ先:", self._config_manager.get_backup_dir(), 1)
        add_info_row(info_frame, "必要環境:", "Samba (samba, smbclient)\npolicykit-1 (polkitd, pkexec)", 2)

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # リンクセクション
        link_frame = ttk.Frame(main_frame)
        link_frame.pack(fill=tk.X, pady=(0, 10))

        def add_link_row(parent, label_text, url, row):
            """クリック可能なリンク行を配置する"""
            ttk.Label(parent, text=label_text, font=("", 9, "bold")).grid(
                row=row, column=0, sticky="w", padx=(0, 10), pady=3
            )
            link_label = ttk.Label(
                parent, text=url, font=("", 9),
                foreground="#4A90D9", cursor="hand2"
            )
            link_label.grid(row=row, column=1, sticky="w", pady=3)
            link_label.bind("<Button-1>", lambda e: webbrowser.open(url))

        # リンク行を追加
        add_link_row(link_frame, "プロジェクト:", const.APP_REPOSITORY_URL, 0)
        add_link_row(link_frame, "問題報告:", const.APP_ISSUES_URL, 1)

        # 閉じるボタン
        ttk.Button(
            main_frame, text="閉じる", width=10,
            command=about_win.destroy
        ).pack(pady=(10, 0))

    def run(self) -> None:
        """アプリケーションのメインループを開始する"""
        self._root.mainloop()
