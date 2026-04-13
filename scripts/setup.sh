#!/bin/bash
# =============================================================================
# セットアップスクリプト
# GitHubからクローン/ダウンロードしたソースから、アプリを実行可能にする
#
# 実行する処理:
#   1. Python依存パッケージの確認とインストール（sv_ttk → vendor/）
#   2. Polkitポリシーの登録（パスワード入力不要化）
#   3. アイコンのインストール（~/.local/share/icons/hicolor/）
#   4. デスクトップエントリの作成（~/.local/share/applications/）
#
# 使い方:
#   bash scripts/setup.sh             # セットアップ（通常）
#   bash scripts/setup.sh --uninstall # セットアップの解除
# =============================================================================

set -e

# === パスの設定 ===
# scripts/ の親ディレクトリをプロジェクトルートとして取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 各ファイルのパス
HELPER_PATH="$PROJECT_DIR/helpers/smb-helper.sh"
MAIN_PY="$PROJECT_DIR/main.py"
ICON_SRC="$PROJECT_DIR/packaging/smb-conf-editor.png"
REQUIREMENTS="$PROJECT_DIR/requirements.txt"
VENDOR_DIR="$PROJECT_DIR/vendor"

# インストール先のパス（ユーザーローカル）
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
DESKTOP_FILE="$DESKTOP_DIR/smb-conf-editor.desktop"
ICON_FILE="$ICON_DIR/smb-conf-editor.png"

# Polkit関連のパス
POLKIT_ACTION_ID="com.smbconfeditor.helper.pkexec"
POLKIT_DEST_DIR="/usr/share/polkit-1/actions"
POLKIT_DEST_FILE="$POLKIT_DEST_DIR/com.smbconfeditor.helper.policy"

# =============================================================================
# アンインストール処理
# =============================================================================
uninstall() {
    echo "=== smb-conf-editor セットアップの解除 ==="
    echo ""

    # デスクトップエントリの削除
    if [ -f "$DESKTOP_FILE" ]; then
        rm -f "$DESKTOP_FILE"
        echo "✅ デスクトップエントリを削除しました"
    else
        echo "-- デスクトップエントリは存在しません（スキップ）"
    fi

    # アイコンの削除
    if [ -f "$ICON_FILE" ]; then
        rm -f "$ICON_FILE"
        echo "✅ アイコンを削除しました"
    else
        echo "-- アイコンは存在しません（スキップ）"
    fi

    # アイコンキャッシュの更新
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    fi

    # デスクトップデータベースの更新
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    # Polkitポリシーの削除
    if [ -f "$POLKIT_DEST_FILE" ]; then
        echo ""
        echo "Polkitポリシーを削除するには管理者権限が必要です。"
        pkexec sh -c "rm -f '$POLKIT_DEST_FILE'"
        if [ $? -eq 0 ]; then
            echo "✅ Polkitポリシーを削除しました"
        else
            echo "⚠ Polkitポリシーの削除に失敗またはキャンセルされました"
        fi
    else
        echo "-- Polkitポリシーは存在しません（スキップ）"
    fi

    # vendorディレクトリの削除
    if [ -d "$VENDOR_DIR" ]; then
        rm -rf "$VENDOR_DIR"
        echo "✅ vendorディレクトリを削除しました"
    fi

    echo ""
    echo "=== セットアップの解除が完了しました ==="
}

# =============================================================================
# セットアップ処理
# =============================================================================
setup() {
    echo "========================================"
    echo "  smb-conf-editor セットアップ"
    echo "========================================"
    echo ""
    echo "プロジェクト: $PROJECT_DIR"
    echo ""

    # --- 前提条件の確認 ---
    local errors=0

    # main.py の存在確認
    if [ ! -f "$MAIN_PY" ]; then
        echo "エラー: main.py が見つかりません: $MAIN_PY" >&2
        errors=1
    fi

    # ヘルパースクリプトの存在確認
    if [ ! -f "$HELPER_PATH" ]; then
        echo "エラー: smb-helper.sh が見つかりません: $HELPER_PATH" >&2
        errors=1
    fi

    # アイコンファイルの存在確認
    if [ ! -f "$ICON_SRC" ]; then
        echo "エラー: アイコンファイルが見つかりません: $ICON_SRC" >&2
        errors=1
    fi

    # python3 の確認
    if ! command -v python3 &>/dev/null; then
        echo "エラー: python3 がインストールされていません" >&2
        echo "  sudo apt install python3" >&2
        errors=1
    fi

    # python3-tk の確認
    if ! python3 -c "import tkinter" 2>/dev/null; then
        echo "エラー: python3-tk がインストールされていません" >&2
        echo "  sudo apt install python3-tk" >&2
        errors=1
    fi

    if [ $errors -ne 0 ]; then
        echo ""
        echo "上記のエラーを解決してから再実行してください。"
        exit 1
    fi

    # pip の確認（未インストールならインストール）
    if ! python3 -m pip --version &>/dev/null; then
        echo "python3-pip がインストールされていません。インストールします..."
        sudo apt install -y python3-pip
        # インストール後の再確認
        if ! python3 -m pip --version &>/dev/null; then
            echo "エラー: python3-pip のインストールに失敗しました" >&2
            exit 1
        fi
        echo "✅ python3-pip をインストールしました"
    fi

    # =========================================================================
    # 1. Python依存パッケージのインストール（vendor/）
    # =========================================================================
    echo "--- 1/4: Python依存パッケージの確認 ---"

    # sv_ttk がシステムにインストール済みか確認
    if python3 -c "import sv_ttk" 2>/dev/null; then
        echo "  sv_ttk: インストール済み（システム）"
    elif [ -d "$VENDOR_DIR" ] && python3 -c "import sys; sys.path.insert(0, '$VENDOR_DIR'); import sv_ttk" 2>/dev/null; then
        echo "  sv_ttk: インストール済み（vendor/）"
    else
        echo "  sv_ttk をインストール中..."
        if python3 -m pip install --target "$VENDOR_DIR" --no-cache-dir --root-user-action=ignore -r "$REQUIREMENTS" 2>/dev/null; then
            echo "  ✅ vendor/ にインストールしました"
        else
            # Ubuntu 24.04で--break-system-packagesが必要な場合のフォールバック
            python3 -m pip install --target "$VENDOR_DIR" --no-cache-dir --break-system-packages -r "$REQUIREMENTS" 2>/dev/null || {
                echo "エラー: sv_ttk のインストールに失敗しました" >&2
                echo "  手動でインストールしてください: pip3 install sv_ttk" >&2
                exit 1
            }
            echo "  ✅ vendor/ にインストールしました"
        fi
    fi

    # ヘルパースクリプトに実行権限を付与
    chmod +x "$HELPER_PATH"

    # =========================================================================
    # 2. Polkitポリシーの登録（パスワード入力不要化）
    # =========================================================================
    echo ""
    echo "--- 2/4: Polkitポリシーの登録 ---"

    # 一時的にポリシーXMLファイルを生成
    POLICY_TMPFILE=$(mktemp /tmp/smb-polkit-XXXXXX.policy)
    cat <<EOF > "$POLICY_TMPFILE"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="$POLKIT_ACTION_ID">
    <description>Run SMB Config Editor Helper</description>
    <message>Samba設定を反映するために管理者権限が必要です</message>
    <defaults>
      <allow_any>yes</allow_any>
      <allow_inactive>yes</allow_inactive>
      <allow_active>yes</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">$HELPER_PATH</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">false</annotate>
  </action>
</policyconfig>
EOF

    echo "  ヘルパースクリプト: $HELPER_PATH"
    echo "  パスワードなしでroot権限を実行できるようPolkitに登録します。"
    echo "  ※システムファイルの書き換えのため、1度だけパスワードを入力してください。"
    echo ""

    # pkexec でポリシーファイルをシステムディレクトリに配置
    if pkexec sh -c "cp '$POLICY_TMPFILE' '$POLKIT_DEST_FILE' && chmod 644 '$POLKIT_DEST_FILE'"; then
        echo "  ✅ Polkitポリシーを登録しました"
    else
        echo "  ⚠ Polkitポリシーの登録に失敗またはキャンセルされました"
        echo "  （アプリは動作しますが、操作のたびにパスワード入力が必要になります）"
    fi

    # 一時ファイルを削除
    rm -f "$POLICY_TMPFILE"

    # =========================================================================
    # 3. アイコンのインストール
    # =========================================================================
    echo ""
    echo "--- 3/4: アイコンのインストール ---"

    # アイコンディレクトリを作成
    mkdir -p "$ICON_DIR"
    # アイコンをコピー
    cp "$ICON_SRC" "$ICON_FILE"
    echo "  ✅ $ICON_FILE"

    # アイコンキャッシュを更新（GNOMEなどで即座に認識させるため）
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    fi

    # =========================================================================
    # 4. デスクトップエントリの作成
    # =========================================================================
    echo ""
    echo "--- 4/4: デスクトップエントリの作成 ---"

    # デスクトップエントリのディレクトリを作成
    mkdir -p "$DESKTOP_DIR"

    # vendorディレクトリが存在する場合、PYTHONPATHを設定する起動コマンドを生成
    if [ -d "$VENDOR_DIR" ]; then
        EXEC_CMD="env PYTHONPATH=$VENDOR_DIR:\$PYTHONPATH /usr/bin/python3 $MAIN_PY"
    else
        EXEC_CMD="/usr/bin/python3 $MAIN_PY"
    fi

    # デスクトップエントリを書き出す
    cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=Samba設定エディター
Name[ja]=Samba設定エディター
Comment=Configure Samba file sharing
Comment[ja]=Sambaのファイル共有設定を編集します
Exec=$EXEC_CMD
Icon=smb-conf-editor
Terminal=false
Type=Application
Categories=Settings;System;Network;
StartupNotify=true
StartupWMClass=smb-conf-editor
EOF

    echo "  ✅ $DESKTOP_FILE"

    # デスクトップデータベースを更新
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    # =========================================================================
    # 完了メッセージ
    # =========================================================================
    echo ""
    echo "========================================"
    echo "✅ セットアップ完了！"
    echo "========================================"
    echo ""
    echo "アプリケーションメニューに「Samba設定エディター」が追加されました。"
    echo ""
    echo "コマンドラインからの起動:"
    echo "  python3 $MAIN_PY"
    echo ""
    echo "セットアップの解除:"
    echo "  bash $SCRIPT_DIR/setup.sh --uninstall"
    echo ""
    echo "※このフォルダを移動した場合は、移動先で再度このスクリプトを実行してください。"
}

# =============================================================================
# メイン処理
# =============================================================================
case "${1:-}" in
    --uninstall)
        uninstall
        ;;
    --help|-h)
        echo "使い方:"
        echo "  $0              セットアップを実行"
        echo "  $0 --uninstall  セットアップを解除"
        echo "  $0 --help       このヘルプを表示"
        ;;
    "")
        setup
        ;;
    *)
        echo "エラー: 不明なオプション: $1" >&2
        echo "$0 --help でヘルプを表示" >&2
        exit 1
        ;;
esac
