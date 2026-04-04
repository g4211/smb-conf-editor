# -*- coding: utf-8 -*-
"""
システムユーティリティモジュール
システム情報の取得（ユーザー一覧、ネットワーク情報、コマンド存在確認等）を提供する。
"""

import ipaddress
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from . import constants as const


# Sambaユーザーの状態定数
SAMBA_STATUS_UNREGISTERED = 0  # 未登録
SAMBA_STATUS_ENABLED = 1       # 有効
SAMBA_STATUS_DISABLED = 2      # 無効

# ステータスの表示ラベル
SAMBA_STATUS_LABELS = {
    SAMBA_STATUS_UNREGISTERED: "[未] 未登録",
    SAMBA_STATUS_ENABLED: "[有] 有効",
    SAMBA_STATUS_DISABLED: "[無] 無効",
}


@dataclass
class SystemUser:
    """システムユーザー情報"""
    username: str          # ユーザー名
    uid: int               # ユーザーID
    samba_status: int = 0  # 0=未登録, 1=有効, 2=無効

    @property
    def is_samba_user(self) -> bool:
        """Sambaユーザーとして登録されているか（後方互換）"""
        return self.samba_status != SAMBA_STATUS_UNREGISTERED

    @property
    def is_samba_enabled(self) -> bool:
        """Sambaユーザーとして有効か"""
        return self.samba_status == SAMBA_STATUS_ENABLED


def get_system_users() -> list[SystemUser]:
    """
    一般ユーザー（UID >= 1000）の一覧を取得する。
    /etc/passwd から読み取り、nobody は除外する。
    """
    users = []
    try:
        with open("/etc/passwd", "r", encoding="utf-8") as f:
            for line in f:
                # /etc/passwd の各行をパース（ユーザー名:パスワード:UID:GID:...）
                parts = line.strip().split(":")
                if len(parts) >= 3:
                    username = parts[0]
                    try:
                        uid = int(parts[2])
                    except ValueError:
                        continue
                    # UID が 1000 以上で、nobody 以外のユーザーを追加
                    if uid >= const.MIN_USER_UID and username != "nobody":
                        users.append(SystemUser(
                            username=username,
                            uid=uid,
                            samba_status=0  # 後で更新する
                        ))
    except IOError as e:
        print(f"警告: /etc/passwd の読み込みに失敗しました: {e}")
    return users


def get_samba_users_with_status(helper_path: str) -> dict[str, int]:
    """
    Sambaユーザーの一覧とステータスを取得する。
    pkexec経由でヘルパースクリプトを使用して pdbedit -Lw を実行する。
    戻り値: {ユーザー名: ステータス(1=有効, 2=無効)} の辞書
    """
    try:
        # ヘルパースクリプト経由で pdbedit -Lw を実行
        result = subprocess.run(
            ["pkexec", helper_path, "list-samba-users"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            samba_users = {}
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split(":")
                username = parts[0].strip()
                if not username:
                    continue
                # pdbedit -Lw 形式: username:UID:LM:NT:[FLAGS]:LCT
                # FLAGS: [U ] = 有効, [DU ] = 無効
                if len(parts) >= 5:
                    flags = parts[4].strip()
                    if 'D' in flags:
                        samba_users[username] = SAMBA_STATUS_DISABLED
                    else:
                        samba_users[username] = SAMBA_STATUS_ENABLED
                else:
                    # フラグなし = 有効とみなす
                    samba_users[username] = SAMBA_STATUS_ENABLED
            return samba_users
        else:
            print(f"警告: Sambaユーザー一覧の取得に失敗しました: {result.stderr}")
            return {}
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"警告: Sambaユーザー一覧の取得に失敗しました: {e}")
        return {}


# 後方互換
def get_samba_users(helper_path: str) -> list[str]:
    """Sambaユーザー名の一覧を取得する（後方互換）"""
    return list(get_samba_users_with_status(helper_path).keys())


def get_network_addresses() -> list[str]:
    """
    自分が所属するネットワークアドレスを取得する。
    ip addr show の出力からネットワークアドレスを計算する。
    """
    networks = []
    try:
        # ip -4 addr show でIPv4アドレス情報を取得
        result = subprocess.run(
            ["ip", "-4", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # "inet x.x.x.x/y" 形式のアドレスを抽出
            pattern = re.compile(r'inet\s+(\d+\.\d+\.\d+\.\d+/\d+)')
            for match in pattern.finditer(result.stdout):
                addr_str = match.group(1)
                try:
                    # ネットワークアドレスを計算
                    interface = ipaddress.IPv4Interface(addr_str)
                    network = interface.network
                    # ループバックアドレスを除外
                    if not interface.ip.is_loopback:
                        networks.append(str(network))
                except ValueError:
                    continue
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"警告: ネットワーク情報の取得に失敗しました: {e}")
    return networks


def check_command_exists(command: str) -> bool:
    """指定されたコマンドがシステムにインストールされているか確認する"""
    return shutil.which(command) is not None


def check_samba_installed() -> dict[str, bool]:
    """
    Sambaの各コンポーネントがインストールされているか確認する。
    戻り値: コマンド名 → インストール状況の辞書
    """
    required_commands = ["testparm", "smbpasswd", "systemctl", "pkexec"]
    results = {}
    for cmd in required_commands:
        results[cmd] = check_command_exists(cmd)
    return results


def check_smb_conf_exists(path: str = None) -> bool:
    """smb.confファイルが存在するか確認する"""
    if path is None:
        path = const.SMB_CONF_PATH
    return os.path.isfile(path)


def get_log_files(log_dir: str) -> list[str]:
    """
    指定されたログディレクトリ内のログファイル一覧を取得する。
    戻り値: ファイル名のリスト（ソート済み）
    """
    log_files = []
    try:
        if os.path.isdir(log_dir):
            for filename in sorted(os.listdir(log_dir)):
                filepath = os.path.join(log_dir, filename)
                # ファイルのみ（ディレクトリは除外）
                if os.path.isfile(filepath):
                    log_files.append(filename)
    except PermissionError:
        print(f"警告: ログディレクトリ '{log_dir}' へのアクセス権限がありません")
    except IOError as e:
        print(f"警告: ログファイル一覧の取得に失敗しました: {e}")
    return log_files


def read_log_file(filepath: str, tail_lines: int = 100) -> Optional[str]:
    """
    ログファイルの内容を読み取る。
    tail_lines > 0 の場合、末尾N行のみ返す。0 の場合は全文を返す。
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if tail_lines > 0 and len(lines) > tail_lines:
            # 末尾N行のみ返す
            return "".join(lines[-tail_lines:])
        return "".join(lines)
    except PermissionError:
        return f"エラー: ファイル '{filepath}' への読み取り権限がありません"
    except IOError as e:
        return f"エラー: ファイルの読み取りに失敗しました: {e}"


# === ホスト名の正規表現パターン ===
# RFC準拠のホスト名（英数字、ハイフン、ドットで構成）
_HOSTNAME_RE = re.compile(
    r'^\.?[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*\.?$'
)


def validate_host_entry(entry: str) -> bool:
    """
    hosts allow の1エントリが有効かどうかを検証する。
    Sambaのhosts allowで許可される形式:
    - IPv4アドレス: 192.168.1.1
    - IPv4ネットワーク（CIDR）: 192.168.1.0/24
    - IPv4ネットワーク（部分）: 192.168.1.（末尾ドット = サブネット指定）
    - IPv6アドレス: ::1, fe80::1
    - IPv6ネットワーク: fe80::/10
    - ホスト名: localhost, myhost.domain.com
    - ドメイン名: .example.com（先頭ドット = ドメイン全体を許可）
    """
    entry = entry.strip()
    if not entry:
        return False

    # EXCEPT キーワード自体は有効
    if entry.upper() == "EXCEPT":
        return True

    # IPv4 末尾ドットの部分記法（例: 192.168.1.）
    if re.match(r'^\d+\.(\d+\.)*$', entry):
        parts = entry.rstrip('.').split('.')
        if 1 <= len(parts) <= 3:
            return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
        return False

    # IPv4/IPv6 CIDR記法（例: 192.168.1.0/24, fe80::/10）
    if '/' in entry:
        try:
            ipaddress.IPv4Network(entry, strict=False)
            return True
        except ValueError:
            pass
        try:
            ipaddress.IPv6Network(entry, strict=False)
            return True
        except ValueError:
            return False

    # IPv4アドレス
    try:
        ipaddress.IPv4Address(entry)
        return True
    except ValueError:
        pass

    # IPv6アドレス
    try:
        ipaddress.IPv6Address(entry)
        return True
    except ValueError:
        pass

    # ホスト名 / ドメイン名（.example.com や localhost 等）
    # ただし数字とドットのみの文字列はIPアドレスとして扱う
    # （999.999.999.999 等の無効なIPがホスト名として通るのを防止）
    if re.match(r'^[\d.]+$', entry):
        return False
    if _HOSTNAME_RE.match(entry):
        return True

    return False


def validate_hosts_allow(text: str) -> tuple[bool, list[str]]:
    """
    hosts allow の入力値全体を検証する。
    EXCEPT構文もサポートする。
    戻り値: (全て有効か, エラーメッセージのリスト)
    """
    errors = []
    lines = text.strip().split('\n')
    for i, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        # 1行に複数のエントリがスペース区切りで含まれる場合を考慮
        tokens = line.split()
        for token in tokens:
            if not validate_host_entry(token):
                errors.append(f"行 {i}: 無効なアドレス/ホスト名: '{token}'")
    return (len(errors) == 0, errors)


# 後方互換性のためのエイリアス
def validate_ip_address(ip_str: str) -> bool:
    """IPアドレス/ネットワーク記法が有効かどうかを検証する（後方互換）"""
    return validate_host_entry(ip_str)


def find_missing_path_part(path: str) -> tuple[str, str]:
    """
    パスの中で存在しない部分を特定する。
    戻り値: (存在する最長プレフィックス, 存在しない部分)
    例: /srv/samba/share → ("/srv", "samba/share")  （/srv/sambaが存在しない場合）
    """
    path = os.path.normpath(path)
    parts = path.split(os.sep)

    # ルートから順にチェック
    existing_prefix = ""
    for i in range(1, len(parts) + 1):
        check_path = os.sep.join(parts[:i]) or os.sep
        if os.path.exists(check_path):
            existing_prefix = check_path
        else:
            # ここから存在しない
            missing_part = os.sep.join(parts[i - 1:])
            return existing_prefix, missing_part

    # 全て存在する
    return path, ""
