# -*- coding: utf-8 -*-
"""
エディター管理ダイアログ
デフォルト以外のカスタムエディターの追加・編集・削除を行うダイアログ。
空欄方式: 常に最下行に空行を配置し、入力するとそのまま追加される。
"""

import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .. import constants as const


class EditorRow:
    """エディター管理ダイアログ内の1行分のUI"""

    def __init__(self, parent: tk.Widget, row_idx: int, editor_data: dict = None,
                 on_delete: callable = None):
        """
        1行分のUIを構築する。
        editor_data: {"name": str, "type": str, "command": str} または None（空行）
        """
        self._parent = parent
        self._row = row_idx
        self._on_delete = on_delete
        self._deleted = False

        # 名称
        self.name_var = tk.StringVar(value=editor_data.get("name", "") if editor_data else "")
        self.name_entry = ttk.Entry(parent, textvariable=self.name_var, width=16)
        self.name_entry.grid(row=row_idx, column=0, padx=(5, 5), pady=3, sticky="w")

        # 種類（ターミナル / グラフィカル）
        self.type_var = tk.StringVar(
            value=editor_data.get("type", const.EDITOR_TYPE_GRAPHICAL) if editor_data else const.EDITOR_TYPE_GRAPHICAL
        )
        self.type_combo = ttk.Combobox(
            parent, textvariable=self.type_var,
            values=[const.EDITOR_TYPE_GRAPHICAL, const.EDITOR_TYPE_TERMINAL],
            state="readonly", width=10
        )
        self.type_combo.grid(row=row_idx, column=1, padx=5, pady=3)

        # 実行コマンド
        self.command_var = tk.StringVar(value=editor_data.get("command", "") if editor_data else "")
        self.command_entry = ttk.Entry(parent, textvariable=self.command_var, width=30)
        self.command_entry.grid(row=row_idx, column=2, padx=5, pady=3, sticky="ew")

        # フォーカスアウト時のバリデーション（警告のみ）
        self.command_entry.bind("<FocusOut>", self._on_command_focus_out)
        self.name_entry.bind("<FocusOut>", self._on_name_focus_out)

        # [参照]ボタン
        self.browse_btn = ttk.Button(
            parent, text="参照", width=5,
            command=self._browse_command
        )
        self.browse_btn.grid(row=row_idx, column=3, padx=2, pady=3)

        # [削除]ボタン
        self.delete_btn = ttk.Button(
            parent, text="削除", width=8,
            command=self._toggle_delete
        )
        self.delete_btn.grid(row=row_idx, column=4, padx=(2, 5), pady=3)

        # 警告ラベル（バリデーション結果の表示用、行の下に表示）
        self.warning_var = tk.StringVar()
        self.warning_label = ttk.Label(
            parent, textvariable=self.warning_var,
            foreground="red", font=("", 8)
        )
        # 警告がある場合のみ表示するので初期状態では非表示

    @property
    def is_deleted(self) -> bool:
        return self._deleted

    def _show_warning(self, msg: str) -> None:
        """警告メッセージを表示する"""
        self.warning_var.set(msg)
        if msg:
            self.warning_label.grid(
                row=self._row + 1, column=0, columnspan=5,
                sticky="w", padx=10
            )
        else:
            self.warning_label.grid_remove()

    def _browse_command(self) -> None:
        """ファイル選択ダイアログで実行ファイルを選ぶ"""
        filepath = filedialog.askopenfilename(
            parent=self._parent,
            title="実行ファイルの選択",
            filetypes=[
                ("すべてのファイル", "*"),
                ("AppImage", "*.AppImage"),
                ("スクリプト", "*.py *.sh"),
            ]
        )
        if filepath:
            self.command_var.set(filepath)
            # 名前が空なら、ファイル名を自動入力
            if not self.name_var.get().strip():
                basename = os.path.basename(filepath)
                name_part = os.path.splitext(basename)[0]
                self.name_var.set(name_part)

    def _on_name_focus_out(self, event=None) -> None:
        """名称欄からフォーカスが外れた時のバリデーション（警告のみ）"""
        name = self.name_var.get().strip()
        command = self.command_var.get().strip()

        # 両方空なら何もしない（空行）
        if not name and not command:
            self._show_warning("")
            return

        if not name and command:
            self._show_warning("⚠ 名称を入力してください")
            return

        # 名称あり + コマンド空 → インストール確認
        if name and not command:
            if not shutil.which(name):
                self._show_warning(f"⚠ '{name}' はインストールされていません")
            else:
                self._show_warning("")
        else:
            self._show_warning("")

    def _on_command_focus_out(self, event=None) -> None:
        """実行コマンド欄からフォーカスが外れた時のバリデーション（警告のみ）"""
        name = self.name_var.get().strip()
        command = self.command_var.get().strip()

        # 両方空なら何もしない（空行）
        if not name and not command:
            self._show_warning("")
            return

        if not command:
            # コマンド空 + 名称あり → インストール確認
            if name and not shutil.which(name):
                self._show_warning(f"⚠ '{name}' はインストールされていません")
            else:
                self._show_warning("")
            return

        # コマンドの実行ファイル部分を抽出して存在確認
        exec_path = command.split()[0]
        if not os.path.isfile(exec_path) and not shutil.which(exec_path):
            self._show_warning(f"⚠ '{exec_path}' が見つかりません")
        else:
            self._show_warning("")

    def _toggle_delete(self) -> None:
        """行の削除状態を切り替える"""
        if self._deleted:
            # 復元する
            self._deleted = False
            self.name_entry.config(state="normal")
            self.type_combo.config(state="readonly")
            self.command_entry.config(state="normal")
            self.browse_btn.config(state="normal")
            self.delete_btn.config(text="削除")
            # 警告をクリアして再バリデーション
            self._show_warning("")
            self._on_command_focus_out()
        else:
            # 削除待ち状態にする
            self._deleted = True
            self.name_entry.config(state="disabled")
            self.type_combo.config(state="disabled")
            self.command_entry.config(state="disabled")
            self.browse_btn.config(state="disabled")
            self.delete_btn.config(text="元に戻す")
            self._show_warning("⚠ 「適用」をクリックすると削除されます")
            if self._on_delete:
                self._on_delete(self)

    def validate(self) -> str | None:
        """バリデーション。エラーがあればメッセージを返す。空行はNone（スキップ）"""
        if self._deleted:
            return None

        name = self.name_var.get().strip()
        command = self.command_var.get().strip()

        # 両方空ならスキップ（空行は無視）
        if not name and not command:
            return None

        # 名称なし + コマンドあり → エラー
        if not name:
            return "名称が入力されていない行があります"

        # コマンド空 → インストール確認
        if not command:
            if not shutil.which(name):
                return f"'{name}' はインストールされていません"
        else:
            # コマンドの実行ファイル部分の存在確認
            exec_path = command.split()[0]
            if not os.path.isfile(exec_path) and not shutil.which(exec_path):
                return f"'{exec_path}' が見つかりません"

        return None

    def get_data(self) -> dict | None:
        """行データを辞書として返す。空行や削除済みはNone"""
        if self._deleted:
            return None
        name = self.name_var.get().strip()
        command = self.command_var.get().strip()
        # 両方空なら空行（無視）
        if not name and not command:
            return None
        return {
            "name": name,
            "type": self.type_var.get(),
            "command": command,
        }

    def destroy_widgets(self) -> None:
        """全ウィジェットを破棄する"""
        for w in (self.name_entry, self.type_combo, self.command_entry,
                  self.browse_btn, self.delete_btn, self.warning_label):
            w.destroy()


def show_editor_manager(parent: tk.Widget, config_manager, on_save: callable = None) -> None:
    """
    エディター管理ダイアログを表示する。
    on_save: 保存完了時に呼ばれるコールバック
    """
    dialog = tk.Toplevel(parent)
    dialog.title("エディター管理")
    dialog.geometry("720x400")
    dialog.resizable(True, True)
    dialog.transient(parent)
    dialog.grab_set()

    main_frame = ttk.Frame(dialog, padding=15)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # 説明文
    default_names = "、".join(const.DEFAULT_EDITORS.keys())
    ttk.Label(
        main_frame,
        text=f"以下のエディターはデフォルトで登録済みです:\n{default_names}\n\n"
             "これら以外のエディターを追加・編集・削除できます。",
        font=("", 9), foreground="gray", wraplength=680, justify=tk.LEFT
    ).pack(anchor=tk.W, pady=(0, 10))

    ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

    # ボタンフレーム（適用・閉じる）を先にBOTTOMでpackして領域を確保
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))

    # スクロール可能なエリア（ヘッダー + リスト一体型）
    scroll_container = ttk.Frame(main_frame)
    scroll_container.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    canvas = tk.Canvas(scroll_container, highlightthickness=0)
    scrollbar = ttk.Scrollbar(scroll_container, orient=tk.VERTICAL, command=canvas.yview)
    list_frame = ttk.Frame(canvas)

    list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas_window = canvas.create_window((0, 0), window=list_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))

    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # ヘッダー行（list_frame内に配置してカラムを揃える）
    list_frame.columnconfigure(2, weight=1)
    ttk.Label(list_frame, text="名称", font=("", 9, "bold")).grid(
        row=0, column=0, padx=(5, 5), pady=(0, 3), sticky="w"
    )
    ttk.Label(list_frame, text="種類", font=("", 9, "bold")).grid(
        row=0, column=1, padx=5, pady=(0, 3), sticky="w"
    )
    ttk.Label(list_frame, text="実行コマンド（空欄=インストール済み）", font=("", 9, "bold")).grid(
        row=0, column=2, padx=5, pady=(0, 3), sticky="w", columnspan=3
    )
    ttk.Separator(list_frame, orient=tk.HORIZONTAL).grid(
        row=1, column=0, columnspan=5, sticky="ew", pady=(0, 3)
    )

    # 行管理用のリストと次の行インデックス
    rows: list[EditorRow] = []
    next_row_idx = [2]  # row=0はヘッダー、row=1はセパレーター

    def add_row(editor_data: dict = None) -> EditorRow:
        """行を追加する"""
        row = EditorRow(list_frame, next_row_idx[0], editor_data=editor_data)
        rows.append(row)
        next_row_idx[0] += 2  # 各行は2行分使用（入力行 + 警告行用スペース）
        return row

    # 既存のカスタムエディターを行として表示
    custom_editors = config_manager.get_custom_editors()
    for editor_data in custom_editors:
        add_row(editor_data)

    # 常に最下行に空行を1つ配置（空欄方式）
    add_row()

    # 適用・閉じるボタン（中央寄せ）
    action_frame = ttk.Frame(btn_frame)
    action_frame.pack(anchor=tk.CENTER)

    # 初期の状態を保存しておく（未保存チェック用）
    initial_editors = config_manager.get_custom_editors()

    def on_apply():
        """適用ボタンの処理（ダイアログは閉じない）"""
        # バリデーション
        errors = []
        valid_editors = []
        for row in rows:
            if row.is_deleted:
                continue
            error = row.validate()
            if error:
                errors.append(error)
                continue
            data = row.get_data()
            if data:
                valid_editors.append(data)

        if errors:
            messagebox.showerror(
                "入力エラー",
                "\n".join(f"・{e}" for e in errors),
                parent=dialog
            )
            return

        # config.jsonに保存
        config_manager.set_custom_editors(valid_editors)
        config_manager.save()

        # 適用されたので、現在の状態を初期状態として更新する
        nonlocal initial_editors
        initial_editors = config_manager.get_custom_editors()

        # コールバック呼び出し（Comboboxの更新等）
        if on_save:
            on_save()

        messagebox.showinfo("適用完了", "エディター設定を保存しました。", parent=dialog)

        # 画面をリフレッシュ（削除済み行のクリーンアップ＋空行の補充）
        _refresh_rows()

    def _refresh_rows():
        """行を再構築する（適用後のクリーンアップ）"""
        nonlocal rows
        # 現在の有効データを収集
        current_data = []
        for row in rows:
            data = row.get_data()
            if data:
                current_data.append(data)
        # 全行のウィジェットを破棄
        for row in rows:
            row.destroy_widgets()
        rows.clear()
        next_row_idx[0] = 2

        # 有効なデータで行を再生成
        for editor_data in current_data:
            add_row(editor_data)
        # 最下行に空行を追加
        add_row()

    def on_closing():
        """ダイアログを閉じる際の未保存チェック"""
        current_editors = []
        for row in rows:
            data = row.get_data()
            if data:
                current_editors.append(data)
        
        if current_editors != initial_editors:
            if not messagebox.askyesno(
                "確認", 
                "変更が適用されていません。\n破棄して閉じますか？", 
                parent=dialog,
                icon=messagebox.WARNING
            ):
                return  # 閉じない
        
        dialog.destroy()

    dialog.protocol("WM_DELETE_WINDOW", on_closing)

    ttk.Button(action_frame, text="適用", width=8, command=on_apply).pack(side=tk.LEFT, padx=(0, 10))
    ttk.Button(action_frame, text="閉じる", width=8, command=on_closing).pack(side=tk.LEFT)
