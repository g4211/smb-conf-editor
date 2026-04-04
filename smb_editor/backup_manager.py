# -*- coding: utf-8 -*-
"""
バックアップ管理モジュール
smb.confのバックアップファイルの作成、復元、削除、履歴管理を行う。
"""

import json
import os
import shutil
import difflib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from . import constants as const


@dataclass
class BackupEntry:
    """バックアップエントリのデータクラス"""
    filename: str                    # バックアップファイル名
    timestamp: str                   # ISO形式のタイムスタンプ
    comment: str = ""                # ユーザーコメント
    exclude_from_deletion: bool = False  # 削除対象から除外するフラグ
    category: str = ""               # 変更カテゴリー


class BackupManager:
    """バックアップの管理クラス"""

    def __init__(self, backup_dir: str, max_backups: int = const.DEFAULT_MAX_BACKUPS):
        """バックアップマネージャーを初期化する"""
        self._backup_dir = backup_dir
        self._max_backups = max_backups
        self._history_path = os.path.join(backup_dir, const.HISTORY_FILENAME)
        # バックアップディレクトリが存在しない場合は作成
        os.makedirs(backup_dir, exist_ok=True)
        # 履歴を読み込む
        self._history = self._load_history()

    def _load_history(self) -> list[BackupEntry]:
        """history.jsonから履歴を読み込む"""
        if os.path.exists(self._history_path):
            try:
                with open(self._history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                entries = []
                for item in data.get("backups", []):
                    entries.append(BackupEntry(**item))
                return entries
            except (json.JSONDecodeError, IOError, TypeError) as e:
                print(f"警告: 履歴ファイルの読み込みに失敗しました: {e}")
                return []
        return []

    def _save_history(self) -> None:
        """履歴をhistory.jsonに保存する"""
        try:
            data = {
                "backups": [asdict(entry) for entry in self._history]
            }
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"エラー: 履歴ファイルの保存に失敗しました: {e}")

    def create_backup(self, source_path: str, category: str,
                      comment: str = "") -> Optional[str]:
        """
        smb.confのバックアップを作成する。
        source_path: バックアップ元のファイルパス
        category: 変更カテゴリー（shared_folder, global, direct_edit, restore）
        comment: ユーザーコメント
        戻り値: バックアップファイル名（失敗時はNone）
        """
        # タイムスタンプからファイル名を生成
        now = datetime.now()
        timestamp_str = now.strftime(const.BACKUP_DATETIME_FORMAT)
        filename = f"{const.BACKUP_PREFIX}{timestamp_str}{const.BACKUP_EXTENSION}"
        backup_path = os.path.join(self._backup_dir, filename)

        try:
            # ファイルをバックアップディレクトリにコピー
            shutil.copy2(source_path, backup_path)
        except IOError as e:
            print(f"エラー: バックアップの作成に失敗しました: {e}")
            return None

        # 履歴エントリを作成
        entry = BackupEntry(
            filename=filename,
            timestamp=now.isoformat(timespec='seconds'),
            comment=comment,
            exclude_from_deletion=False,
            category=category,
        )
        self._history.append(entry)
        self._save_history()

        # 古いバックアップを削除
        self.delete_old_backups()

        return filename

    def restore_backup(self, filename: str, target_path: str) -> bool:
        """
        バックアップファイルからsmb.confを復元する。
        実際のファイルコピーはヘルパースクリプト経由で行うため、
        ここではバックアップファイルのパスを返す。
        """
        backup_path = os.path.join(self._backup_dir, filename)
        if not os.path.exists(backup_path):
            print(f"エラー: バックアップファイルが見つかりません: {backup_path}")
            return False
        return True

    def get_backup_path(self, filename: str) -> str:
        """バックアップファイルの絶対パスを返す"""
        return os.path.join(self._backup_dir, filename)

    def delete_old_backups(self) -> None:
        """
        バックアップ最大数を超えた古いファイルを削除する。
        削除対象から除外されたファイルはスキップする。
        """
        # 除外されていないエントリのみ対象
        deletable = [e for e in self._history if not e.exclude_from_deletion]
        # タイムスタンプでソート（古い順）
        deletable.sort(key=lambda e: e.timestamp)

        # 最大数を超えた分を削除
        while len(deletable) > self._max_backups:
            entry_to_delete = deletable.pop(0)
            backup_path = os.path.join(self._backup_dir, entry_to_delete.filename)
            try:
                if os.path.exists(backup_path):
                    os.remove(backup_path)
            except IOError as e:
                print(f"警告: バックアップファイルの削除に失敗しました: {e}")
            # 履歴からも削除
            self._history = [e for e in self._history
                           if e.filename != entry_to_delete.filename]

        self._save_history()

    def get_backup_list(self) -> list[BackupEntry]:
        """バックアップ一覧を返す（新しい順）"""
        sorted_list = sorted(self._history, key=lambda e: e.timestamp, reverse=True)
        return sorted_list

    def update_comment(self, filename: str, comment: str) -> None:
        """バックアップエントリのコメントを更新する"""
        for entry in self._history:
            if entry.filename == filename:
                entry.comment = comment
                break
        self._save_history()

    def set_exclude(self, filename: str, exclude: bool) -> None:
        """バックアップエントリの削除除外フラグを設定する"""
        for entry in self._history:
            if entry.filename == filename:
                entry.exclude_from_deletion = exclude
                break
        self._save_history()

    def get_diff(self, backup_filename: str, current_filepath: str) -> str:
        """
        バックアップファイルと現在の設定ファイルの差分を返す。
        unified diff 形式で返す。
        """
        backup_path = os.path.join(self._backup_dir, backup_filename)
        try:
            # バックアップファイルの内容を読み込む
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_lines = f.readlines()
            # 現在のファイルの内容を読み込む
            with open(current_filepath, "r", encoding="utf-8") as f:
                current_lines = f.readlines()

            # unified diff形式で差分を生成
            diff = difflib.unified_diff(
                backup_lines,
                current_lines,
                fromfile=f"バックアップ ({backup_filename})",
                tofile="現在の設定",
                lineterm=""
            )
            return "\n".join(diff)
        except IOError as e:
            return f"エラー: 差分の生成に失敗しました: {e}"

    def read_backup(self, filename: str) -> Optional[str]:
        """バックアップファイルの内容を読み取る"""
        backup_path = os.path.join(self._backup_dir, filename)
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                return f.read()
        except IOError as e:
            return f"エラー: ファイルの読み取りに失敗しました: {e}"

    @property
    def backup_dir(self) -> str:
        """バックアップディレクトリのパスを返す"""
        return self._backup_dir

    @property
    def max_backups(self) -> int:
        """バックアップ最大数を返す"""
        return self._max_backups

    @max_backups.setter
    def max_backups(self, value: int) -> None:
        """バックアップ最大数を設定する"""
        self._max_backups = max(1, value)  # 最小値は1
