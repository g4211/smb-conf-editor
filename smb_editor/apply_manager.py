# -*- coding: utf-8 -*-
"""
適用処理管理モジュール
smb.confへの変更適用処理（*1）の共通ロジックを提供する。
apply-allバッチコマンドで全操作を1回のpkexec呼び出しで実行し、
パスワード入力を1回に削減する。
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional

from . import constants as const
from .backup_manager import BackupManager
from .config_manager import ConfigManager


@dataclass
class ApplyResult:
    """適用処理の結果"""
    success: bool                         # 全体の成否
    message: str = ""                     # 結果メッセージ
    errors: list[str] = field(default_factory=list)  # エラーメッセージのリスト
    steps: list[str] = field(default_factory=list)   # 実行されたステップ
    backup_filename: str = ""             # 作成されたバックアップファイル名


class ApplyManager:
    """適用処理の管理クラス"""

    def __init__(self, config_manager: ConfigManager, backup_manager: BackupManager):
        """適用マネージャーを初期化する"""
        self._config_manager = config_manager
        self._backup_manager = backup_manager
        self._helper_path = const.get_helper_path()

    def _run_helper(self, command: str, *args, stdin_data: str = None,
                    timeout: int = 30) -> subprocess.CompletedProcess:
        """ヘルパースクリプトをpkexec経由で実行する"""
        cmd = ["pkexec", self._helper_path, command] + list(args)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                input=stdin_data, timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                args=cmd, returncode=1,
                stdout="", stderr="エラー: 操作がタイムアウトしました"
            )
        except FileNotFoundError as e:
            return subprocess.CompletedProcess(
                args=cmd, returncode=1,
                stdout="", stderr=f"エラー: コマンドが見つかりません: {e}"
            )

    def apply_changes(self, new_conf_content: str, category: str,
                      comment: str = "",
                      samba_users_to_add: Optional[list[dict]] = None,
                      new_share_dirs: Optional[list[str]] = None,
                      enable_users: Optional[list[str]] = None) -> ApplyResult:
        """
        apply-allバッチコマンドで全操作を1回のpkexecで実行する。
        パスワード入力は1回だけ。

        手順:
        1. 新しいsmb.confを一時ファイルに書き出し
        2. バックアップ先パスを決定
        3. JSON設定ファイルを作成
        4. pkexec smb-helper.sh apply-all <json> を1回だけ実行
        5. 結果を解析して返す
        """
        result = ApplyResult(success=False)

        # === 一時ファイルに新しいsmb.confを書き出し ===
        try:
            tmp_new = tempfile.NamedTemporaryFile(
                mode='w', suffix='.conf', prefix='smb_new_',
                delete=False, dir=tempfile.gettempdir(),
                encoding='utf-8'
            )
            tmp_new.write(new_conf_content)
            tmp_new.close()
            tmp_new_path = tmp_new.name
            # 読み取り権限をrootからも読めるようにする
            os.chmod(tmp_new_path, 0o644)
        except Exception as e:
            result.errors.append(f"一時ファイルの書き出しに失敗: {e}")
            return result

        # === バックアップ先パスを決定 ===
        from datetime import datetime
        now = datetime.now()
        timestamp_str = now.strftime(const.BACKUP_DATETIME_FORMAT)
        backup_filename = f"{const.BACKUP_PREFIX}{timestamp_str}{const.BACKUP_EXTENSION}"
        backup_path = os.path.join(self._backup_manager.backup_dir, backup_filename)
        # バックアップディレクトリが存在するか確認
        os.makedirs(self._backup_manager.backup_dir, exist_ok=True)

        # === JSON設定ファイルを作成 ===
        apply_config = {
            "backup_dest": backup_path,
            "new_conf_path": tmp_new_path,
            "restart_smbd": True,
            "samba_users": [],
            "enable_users": [],
            "create_dirs": [],
        }

        # Sambaユーザー追加情報
        if samba_users_to_add:
            for user_info in samba_users_to_add:
                apply_config["samba_users"].append({
                    "username": user_info.get("username", ""),
                    "password": user_info.get("password", ""),
                })

        # 無効→有効にするユーザー
        if enable_users:
            apply_config["enable_users"] = enable_users

        # ディレクトリ作成情報
        if new_share_dirs:
            for dir_path in new_share_dirs:
                apply_config["create_dirs"].append({
                    "path": dir_path,
                    "owner": "nobody",
                    "group": "nogroup",
                    "mode": "0777",
                })

        # JSON設定ファイルを一時ファイルに書き出し
        try:
            tmp_json = tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', prefix='smb_apply_',
                delete=False, dir=tempfile.gettempdir(),
                encoding='utf-8'
            )
            json.dump(apply_config, tmp_json, ensure_ascii=False)
            tmp_json.close()
            tmp_json_path = tmp_json.name
            # セキュリティ: パスワード含むためアクセス制限
            os.chmod(tmp_json_path, 0o600)
        except Exception as e:
            result.errors.append(f"設定ファイルの作成に失敗: {e}")
            self._cleanup_temp(tmp_new_path)
            return result

        # === pkexec apply-all を1回だけ実行 ===
        helper_result = self._run_helper("apply-all", tmp_json_path, timeout=120)

        # === 結果を解析 ===
        if helper_result.returncode == 0 and helper_result.stdout.strip():
            try:
                result_data = json.loads(helper_result.stdout.strip())
                result.success = result_data.get("success", False)
                result.steps = result_data.get("steps", [])
                result.errors = result_data.get("errors", [])
            except json.JSONDecodeError:
                # JSON以外の出力（旧形式互換）
                if "OK" in helper_result.stdout:
                    result.success = True
                    result.steps.append(helper_result.stdout.strip())
                else:
                    result.errors.append(helper_result.stdout.strip())
        else:
            # 実行失敗
            error_msg = helper_result.stderr or helper_result.stdout or "不明なエラー"
            result.errors.append(f"適用処理に失敗しました:\n{error_msg}")

        # === バックアップ履歴を更新（成功時） ===
        if result.success:
            from .backup_manager import BackupEntry
            entry = BackupEntry(
                filename=backup_filename,
                timestamp=now.isoformat(timespec='seconds'),
                comment=comment,
                exclude_from_deletion=False,
                category=category,
            )
            self._backup_manager._history.append(entry)
            self._backup_manager._save_history()
            self._backup_manager.delete_old_backups()
            result.backup_filename = backup_filename
            result.message = "設定を正常に適用しました"
            if result.errors:
                result.message = "設定を適用しましたが、一部でエラーが発生しました"
        else:
            result.message = "適用処理に失敗しました"

        # === 一時ファイルの削除 ===
        self._cleanup_temp(tmp_new_path)
        self._cleanup_temp(tmp_json_path)

        return result

    def read_current_conf(self) -> Optional[str]:
        """現在のsmb.confの内容を読み取る（ヘルパー経由）"""
        try:
            result = self._run_helper("read-conf")
            if result.returncode == 0:
                return result.stdout
            else:
                # フォールバック: 直接読み取りを試みる
                try:
                    with open(const.SMB_CONF_PATH, "r", encoding="utf-8") as f:
                        return f.read()
                except IOError:
                    return None
        except Exception:
            return None

    def _cleanup_temp(self, filepath: str) -> None:
        """一時ファイルを安全に削除する"""
        try:
            if filepath and os.path.exists(filepath):
                os.unlink(filepath)
        except IOError:
            pass
