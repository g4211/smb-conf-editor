#!/bin/bash
# -*- coding: utf-8 -*-
# =============================================================================
# smb-helper.sh - Samba設定エディター用ヘルパースクリプト
# pkexec経由でroot権限が必要な操作を実行する
# 使い方: pkexec /path/to/smb-helper.sh <command> [args...]
# =============================================================================

set -euo pipefail

# Sambaの設定ファイルパス
SMB_CONF="/etc/samba/smb.conf"

# 使い方を表示する関数
show_usage() {
    echo "使い方: $0 <command> [args...]"
    echo ""
    echo "コマンド一覧:"
    echo "  apply-all <json_config>       - 全操作をバッチ実行（推奨）"
    echo "  copy-conf <dest>              - smb.confを指定先にコピー"
    echo "  write-conf <source>           - 一時ファイルからsmb.confへ置換"
    echo "  test-conf <filepath>          - testparmで構文チェック"
    echo "  restart-smbd                  - smbdを再起動"
    echo "  add-samba-user <username>     - Sambaユーザーを追加（stdinからパスワード読み取り）"
    echo "  list-samba-users              - Sambaユーザー一覧を表示"
    echo "  set-permissions <path> <owner> <group> <mode>"
    echo "                                - 所有者・パーミッションを設定"
    echo "  restore-conf <backup_file>    - バックアップからsmb.confを復元"
    echo "  backup-conf <dest>            - smb.confをバックアップ先にコピー"
    echo "  read-conf                     - smb.confの内容を標準出力に出力"
    echo "  mkdir-share <path>            - 共有ディレクトリを作成"
}

# 引数チェック
if [ $# -lt 1 ]; then
    show_usage
    exit 1
fi

# コマンドの取得
COMMAND="$1"
shift

case "$COMMAND" in
    # ==========================================================
    # apply-all: 全操作をバッチ実行（パスワード入力が1回で済む）
    # ==========================================================
    apply-all)
        if [ $# -lt 1 ]; then
            echo "エラー: JSON設定ファイルを指定してください" >&2
            exit 1
        fi
        CONFIG_JSON="$1"
        if [ ! -f "$CONFIG_JSON" ]; then
            echo "エラー: 設定ファイルが見つかりません: ${CONFIG_JSON}" >&2
            exit 1
        fi

        # python3でJSONをパースして各操作を実行
        # 結果をJSON形式で標準出力に出力
        python3 - "$CONFIG_JSON" << 'PYTHON_EOF'
import json
import subprocess
import shutil
import sys
import os

def run_cmd(cmd, stdin_data=None):
    """コマンドを実行し、結果を返す"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            input=stdin_data, timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def main():
    config_path = sys.argv[1]
    with open(config_path, "r") as f:
        config = json.load(f)

    results = {"success": True, "steps": [], "errors": []}
    smb_conf = "/etc/samba/smb.conf"

    # === ステップ1: 現在のsmb.confをバックアップ ===
    backup_dest = config.get("backup_dest", "")
    if backup_dest:
        try:
            shutil.copy2(smb_conf, backup_dest)
            os.chmod(backup_dest, 0o644)
            results["steps"].append("バックアップ作成完了")
        except Exception as e:
            results["errors"].append(f"バックアップ作成失敗: {e}")
            results["success"] = False
            print(json.dumps(results, ensure_ascii=False))
            sys.exit(1)

    # === ステップ2: Sambaユーザー追加 ===
    samba_users = config.get("samba_users", [])
    for user_info in samba_users:
        username = user_info.get("username", "")
        password = user_info.get("password", "")
        if username and password:
            stdin_data = f"{password}\n{password}\n"
            rc, out, err = run_cmd(["smbpasswd", "-a", "-s", username], stdin_data)
            if rc != 0:
                results["errors"].append(f"Sambaユーザー '{username}' の追加失敗: {err}")
                results["success"] = False
                print(json.dumps(results, ensure_ascii=False))
                sys.exit(1)
            results["steps"].append(f"Sambaユーザー '{username}' 追加完了")

    # === ステップ2.5: Sambaユーザー有効化 ===
    enable_users = config.get("enable_users", [])
    for username in enable_users:
        if username:
            rc, out, err = run_cmd(["smbpasswd", "-e", username])
            if rc != 0:
                results["errors"].append(f"Sambaユーザー '{username}' の有効化失敗: {err}")
                results["success"] = False
                print(json.dumps(results, ensure_ascii=False))
                sys.exit(1)
            results["steps"].append(f"Sambaユーザー '{username}' 有効化完了")

    # === ステップ3: 新しいsmb.confの構文チェック ===
    new_conf_path = config.get("new_conf_path", "")
    if new_conf_path and os.path.isfile(new_conf_path):
        rc, out, err = run_cmd(["testparm", "-s", new_conf_path])
        if rc != 0:
            # testparmのエラー詳細を取得
            rc2, out2, err2 = run_cmd(["testparm", "-s", new_conf_path])
            error_detail = err2 or err or out2 or out
            results["errors"].append(f"構文チェック失敗:\n{error_detail}")
            results["success"] = False
            print(json.dumps(results, ensure_ascii=False))
            sys.exit(1)
        results["steps"].append("構文チェック合格")

        # === ステップ4: smb.confをアトミック置換 ===
        try:
            temp_dest = "/etc/samba/.smb.conf.tmp"
            shutil.copy2(new_conf_path, temp_dest)
            os.chown(temp_dest, 0, 0)
            os.chmod(temp_dest, 0o644)
            os.rename(temp_dest, smb_conf)
            results["steps"].append("smb.conf更新完了")
        except Exception as e:
            results["errors"].append(f"smb.conf更新失敗: {e}")
            results["success"] = False
            # バックアップから復元を試みる
            if backup_dest and os.path.isfile(backup_dest):
                try:
                    shutil.copy2(backup_dest, smb_conf)
                    results["steps"].append("バックアップから復元しました")
                except:
                    pass
            print(json.dumps(results, ensure_ascii=False))
            sys.exit(1)

    # === ステップ5: smbd再起動 ===
    if config.get("restart_smbd", True):
        rc, out, err = run_cmd(["systemctl", "restart", "smbd"])
        if rc != 0:
            results["errors"].append(f"smbd再起動失敗: {err}")
            # 再起動失敗は致命的ではないので続行
        else:
            results["steps"].append("smbd再起動完了")

    # === ステップ6: 共有ディレクトリの作成とパーミッション設定 ===
    create_dirs = config.get("create_dirs", [])
    for dir_info in create_dirs:
        dir_path = dir_info.get("path", "")
        owner = dir_info.get("owner", "nobody")
        group = dir_info.get("group", "nogroup")
        mode = dir_info.get("mode", "0777")
        if dir_path:
            try:
                os.makedirs(dir_path, exist_ok=True)
                # 所有者設定
                import pwd, grp
                uid = pwd.getpwnam(owner).pw_uid
                gid = grp.getgrnam(group).gr_gid
                os.chown(dir_path, uid, gid)
                os.chmod(dir_path, int(mode, 8))
                results["steps"].append(f"ディレクトリ '{dir_path}' 作成・設定完了")
            except Exception as e:
                results["errors"].append(f"ディレクトリ '{dir_path}' 設定失敗: {e}")

    # エラーがあっても主要な操作が成功していれば部分的成功とする
    if results["errors"] and results["success"]:
        results["success"] = True  # 主要操作は成功

    print(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()
PYTHON_EOF
        ;;

    # smb.confを指定先にコピーする
    copy-conf)
        if [ $# -lt 1 ]; then
            echo "エラー: コピー先を指定してください" >&2
            exit 1
        fi
        DEST="$1"
        cp "$SMB_CONF" "$DEST"
        chmod 644 "$DEST"
        echo "OK: smb.confを ${DEST} にコピーしました"
        ;;

    # 一時ファイルからsmb.confへアトミック置換する
    write-conf)
        if [ $# -lt 1 ]; then
            echo "エラー: ソースファイルを指定してください" >&2
            exit 1
        fi
        SOURCE="$1"
        if [ ! -f "$SOURCE" ]; then
            echo "エラー: ソースファイルが見つかりません: ${SOURCE}" >&2
            exit 1
        fi
        TEMP_DEST="/etc/samba/.smb.conf.tmp"
        cp "$SOURCE" "$TEMP_DEST"
        chown root:root "$TEMP_DEST"
        chmod 644 "$TEMP_DEST"
        mv "$TEMP_DEST" "$SMB_CONF"
        echo "OK: smb.confを更新しました"
        ;;

    # testparmで構文チェックする
    test-conf)
        if [ $# -lt 1 ]; then
            FILEPATH="$SMB_CONF"
        else
            FILEPATH="$1"
        fi
        testparm -s "$FILEPATH" > /dev/null 2>&1
        RESULT=$?
        if [ $RESULT -eq 0 ]; then
            echo "OK: 構文チェックに合格しました"
        else
            echo "エラー: 構文チェックに失敗しました" >&2
            testparm -s "$FILEPATH" 2>&1 || true
            exit 1
        fi
        ;;

    # smbdを再起動する
    restart-smbd)
        systemctl restart smbd
        echo "OK: smbdを再起動しました"
        ;;

    # Sambaユーザーを追加する（stdinからパスワードを読み取り）
    add-samba-user)
        if [ $# -lt 1 ]; then
            echo "エラー: ユーザー名を指定してください" >&2
            exit 1
        fi
        USERNAME="$1"
        smbpasswd -a -s "$USERNAME"
        RESULT=$?
        if [ $RESULT -eq 0 ]; then
            echo "OK: Sambaユーザー '${USERNAME}' を追加しました"
        else
            echo "エラー: Sambaユーザーの追加に失敗しました" >&2
            exit 1
        fi
        ;;

    # Sambaユーザー一覧を表示する（-Lw形式でフラグも出力）
    list-samba-users)
        pdbedit -Lw 2>/dev/null || echo ""
        ;;

    # Sambaユーザーを有効化する
    enable-samba-user)
        if [ $# -lt 1 ]; then
            echo "エラー: ユーザー名を指定してください" >&2
            exit 1
        fi
        USERNAME="$1"
        smbpasswd -e "$USERNAME"
        RESULT=$?
        if [ $RESULT -eq 0 ]; then
            echo "OK: Sambaユーザー '${USERNAME}' を有効化しました"
        else
            echo "エラー: Sambaユーザーの有効化に失敗しました" >&2
            exit 1
        fi
        ;;

    # Sambaユーザーを無効化する
    disable-samba-user)
        if [ $# -lt 1 ]; then
            echo "エラー: ユーザー名を指定してください" >&2
            exit 1
        fi
        USERNAME="$1"
        smbpasswd -d "$USERNAME"
        RESULT=$?
        if [ $RESULT -eq 0 ]; then
            echo "OK: Sambaユーザー '${USERNAME}' を無効化しました"
        else
            echo "エラー: Sambaユーザーの無効化に失敗しました" >&2
            exit 1
        fi
        ;;

    # Sambaユーザーの登録を解除する
    remove-samba-user)
        if [ $# -lt 1 ]; then
            echo "エラー: ユーザー名を指定してください" >&2
            exit 1
        fi
        USERNAME="$1"
        smbpasswd -x "$USERNAME"
        RESULT=$?
        if [ $RESULT -eq 0 ]; then
            echo "OK: Sambaユーザー '${USERNAME}' の登録を解除しました"
        else
            echo "エラー: Sambaユーザーの登録解除に失敗しました" >&2
            exit 1
        fi
        ;;

    # 所有者・パーミッションを設定する
    set-permissions)
        if [ $# -lt 4 ]; then
            echo "エラー: パス、所有者、グループ、パーミッションを指定してください" >&2
            exit 1
        fi
        TARGET_PATH="$1"
        OWNER="$2"
        GROUP="$3"
        MODE="$4"
        if [ ! -d "$TARGET_PATH" ]; then
            echo "エラー: ディレクトリが見つかりません: ${TARGET_PATH}" >&2
            exit 1
        fi
        chown -R "${OWNER}:${GROUP}" "$TARGET_PATH"
        chmod -R "$MODE" "$TARGET_PATH"
        echo "OK: ${TARGET_PATH} のパーミッションを設定しました"
        ;;

    # バックアップからsmb.confを復元する
    restore-conf)
        if [ $# -lt 1 ]; then
            echo "エラー: バックアップファイルを指定してください" >&2
            exit 1
        fi
        BACKUP_FILE="$1"
        if [ ! -f "$BACKUP_FILE" ]; then
            echo "エラー: バックアップファイルが見つかりません: ${BACKUP_FILE}" >&2
            exit 1
        fi
        TEMP_DEST="/etc/samba/.smb.conf.tmp"
        cp "$BACKUP_FILE" "$TEMP_DEST"
        chown root:root "$TEMP_DEST"
        chmod 644 "$TEMP_DEST"
        mv "$TEMP_DEST" "$SMB_CONF"
        echo "OK: smb.confを復元しました"
        ;;

    # smb.confをバックアップ先にコピーする
    backup-conf)
        if [ $# -lt 1 ]; then
            echo "エラー: バックアップ先を指定してください" >&2
            exit 1
        fi
        DEST="$1"
        cp "$SMB_CONF" "$DEST"
        chmod 644 "$DEST"
        echo "OK: smb.confを ${DEST} にバックアップしました"
        ;;

    # smb.confの内容を標準出力に出力する
    read-conf)
        cat "$SMB_CONF"
        ;;

    # 共有ディレクトリを作成する
    mkdir-share)
        if [ $# -lt 1 ]; then
            echo "エラー: ディレクトリパスを指定してください" >&2
            exit 1
        fi
        TARGET_PATH="$1"
        if [ ! -d "$TARGET_PATH" ]; then
            mkdir -p "$TARGET_PATH"
            echo "OK: ディレクトリ '${TARGET_PATH}' を作成しました"
        else
            echo "OK: ディレクトリ '${TARGET_PATH}' は既に存在します"
        fi
        chown nobody:nogroup "$TARGET_PATH"
        chmod 0777 "$TARGET_PATH"
        echo "OK: パーミッションを設定しました"
        ;;

    # 不明なコマンド
    *)
        echo "エラー: 不明なコマンド: ${COMMAND}" >&2
        show_usage
        exit 1
        ;;
esac
