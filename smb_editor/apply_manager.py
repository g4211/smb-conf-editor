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
        """
        result = ApplyResult(success=False)
        from datetime import datetime
        now = datetime.now()

        # 1. 新しいsmb.confの一時ファイル作成
        tmp_new_path = self._prepare_new_conf_tempfile(new_conf_content, result)
        if not tmp_new_path:
            return result

        # 2. JSON設定の組み立てと一時ファイル保存
        backup_filename, backup_path = self._get_backup_path_info(now)
        os.makedirs(self._backup_manager.backup_dir, exist_ok=True)
        
        apply_config = self._build_apply_config(
            backup_path, tmp_new_path,
            samba_users_to_add, enable_users, new_share_dirs
        )
        
        tmp_json_path = self._write_json_tempfile(apply_config, tmp_new_path, result)
        if not tmp_json_path:
            return result

        # 3. pkexecコマンド実行と結果解析
        helper_result = self._run_helper("apply-all", tmp_json_path, timeout=120)
        self._parse_helper_result(helper_result, result)

        # 4. 履歴更新と後処理
        if result.success:
            self._update_backup_history(backup_filename, now, category, comment)
            result.backup_filename = backup_filename
            result.message = "設定を正常に適用しました" if not result.errors else "設定を適用しましたが、一部でエラーが発生しました"
        else:
            result.message = "適用処理に失敗しました"

        self._cleanup_temp(tmp_new_path)
        self._cleanup_temp(tmp_json_path)
        return result

    def _prepare_new_conf_tempfile(self, content: str, result: ApplyResult) -> Optional[str]:
        """新しいsmb.conf内容を一時ファイルに書き出す"""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.conf', prefix='smb_new_',
                delete=False, dir=tempfile.gettempdir(), encoding='utf-8'
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            os.chmod(tmp_path, 0o644)
            return tmp_path
        except Exception as e:
            result.errors.append(f"一時ファイルの書き出しに失敗: {e}")
            return None

    def _get_backup_path_info(self, now) -> tuple[str, str]:
        """バックアップファイル名とパスを生成する"""
        timestamp_str = now.strftime(const.BACKUP_DATETIME_FORMAT)
        filename = f"{const.BACKUP_PREFIX}{timestamp_str}{const.BACKUP_EXTENSION}"
        path = os.path.join(self._backup_manager.backup_dir, filename)
        return filename, path

    def _build_apply_config(self, backup_path: str, tmp_new_path: str,
                            samba_users, enable_users, create_dirs) -> dict:
        """バックエンドへ渡すJSON設定を組み立てる"""
        config = {
            "backup_dest": backup_path,
            "new_conf_path": tmp_new_path,
            "restart_smbd": True,
            "samba_users": [],
            "enable_users": enable_users or [],
            "create_dirs": [],
        }
        if samba_users:
            for u in samba_users:
                config["samba_users"].append({"username": u.get("username", ""), "password": u.get("password", "")})
        if create_dirs:
            for d in create_dirs:
                config["create_dirs"].append({"path": d, "owner": "nobody", "group": "nogroup", "mode": "0777"})
        return config

    def _write_json_tempfile(self, config: dict, tmp_new_path: str, result: ApplyResult) -> Optional[str]:
        """JSON設定を一時ファイルに書き出す"""
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', prefix='smb_apply_',
                delete=False, dir=tempfile.gettempdir(), encoding='utf-8'
            ) as tmp:
                json.dump(config, tmp, ensure_ascii=False)
                tmp_path = tmp.name
            os.chmod(tmp_path, 0o600)
            return tmp_path
        except Exception as e:
            result.errors.append(f"設定ファイルの作成に失敗: {e}")
            self._cleanup_temp(tmp_new_path)
            return None

    def _parse_helper_result(self, helper_result, result: ApplyResult):
        """ヘルパースクリプトの実行結果を解析する"""
        if helper_result.returncode == 0 and helper_result.stdout.strip():
            try:
                data = json.loads(helper_result.stdout.strip())
                result.success = data.get("success", False)
                result.steps = data.get("steps", [])
                result.errors = data.get("errors", [])
            except json.JSONDecodeError:
                if "OK" in helper_result.stdout:
                    result.success = True
                    result.steps.append(helper_result.stdout.strip())
                else:
                    result.errors.append(helper_result.stdout.strip())
        else:
            error_msg = helper_result.stderr or helper_result.stdout or "不明なエラー"
            result.errors.append(f"適用処理に失敗しました:\n{error_msg}")

    def _update_backup_history(self, filename: str, now, category: str, comment: str):
        """バックアップ履歴に新しいエントリを追加する"""
        self._backup_manager.register_backup_metadata(filename, now, category, comment)

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
