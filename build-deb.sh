#!/bin/bash
# =============================================================================
# DEBパッケージビルドスクリプト
# Samba設定エディターのDebianパッケージを作成する
# =============================================================================

set -e
cd "$(dirname "$0")"

# === ビルドツールの依存チェック ===
# 必要なコマンドがインストールされているか確認する
check_build_dependencies() {
    local missing=()
    # 必須コマンドの一覧をチェック
    for cmd in dpkg-deb fakeroot python3 gzip; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    # python3 -m pip が利用可能か確認
    if ! python3 -m pip --version &>/dev/null 2>&1; then
        missing+=("python3-pip")
    fi
    # 不足しているツールがあればエラーを表示して終了
    if [ ${#missing[@]} -gt 0 ]; then
        echo "エラー: 以下のビルドツールが見つかりません: ${missing[*]}" >&2
        echo "インストール方法: sudo apt install ${missing[*]}" >&2
        exit 1
    fi
}

# ビルドツールの依存チェックを実行
check_build_dependencies

# === バージョン情報の取得 ===
# constants.py からアプリケーションバージョンを読み取る
VERSION=$(grep -oP 'APP_VERSION\s*=\s*"\K[^"]+' smb_editor/constants.py || echo "1.1.0")
PKG_NAME="smb-conf-editor"
BUILD_DIR="build_deb/${PKG_NAME}_${VERSION}_all"

echo "================================================"
echo "DEBパッケージビルド: ${PKG_NAME} v${VERSION}"
echo "================================================"

# 前回のビルド成果物を削除
rm -rf "build_deb"
# DEBIANメタデータディレクトリを作成
mkdir -p "$BUILD_DIR/DEBIAN"

# =============================================================================
# 1. control ファイルの生成
# =============================================================================
# Installed-Sizeは後で追記する
cat <<EOF > "$BUILD_DIR/DEBIAN/control"
Package: $PKG_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-tk, polkitd, pkexec
Maintainer: Developer <dev@example.com>
Homepage: https://github.com/smb-conf-editor
Description: Samba設定エディター - GUIでsmb.confを編集
 Ubuntu向けのSamba設定ファイル（/etc/samba/smb.conf）を
 GUIで編集するPythonアプリケーションです。
 .
 主な機能:
  - 共有フォルダの追加・編集・削除
  - globalセクション（workgroup, hosts allow等）の設定
  - 外部エディターによるsmb.confの直接編集
  - Sambaログファイルの閲覧（検索・自動更新機能付き）
  - 設定変更時の自動バックアップと復元
  - バックアップと現在の設定の差分表示
  - Sambaユーザーの登録・解除・有効化・無効化
EOF

# =============================================================================
# 2. postinst スクリプトの生成（インストール後に実行）
# =============================================================================
cat <<'EOF' > "$BUILD_DIR/DEBIAN/postinst"
#!/bin/sh
set -e

# Polkitデーモンにポリシーの再読込を通知する
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet polkit 2>/dev/null; then
    systemctl reload polkit 2>/dev/null || true
fi

echo ""
echo "smb-conf-editor のインストールが完了しました。"
echo "アプリケーションメニューから「Samba設定エディター」を起動できます。"
exit 0
EOF
# postinst に実行権限を付与
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# =============================================================================
# 3. postrm スクリプトの生成（アンインストール後に実行）
# =============================================================================
cat <<'EOF' > "$BUILD_DIR/DEBIAN/postrm"
#!/bin/sh
set -e

case "$1" in
    remove)
        # パッケージ削除時：Polkitポリシーファイルを削除する
        rm -f /usr/share/polkit-1/actions/com.smbconfeditor.helper.policy
        # Polkitデーモンにポリシーの再読込を通知する
        if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet polkit 2>/dev/null; then
            systemctl reload polkit 2>/dev/null || true
        fi
        ;;
    purge)
        # 完全削除時：アプリケーションディレクトリを完全に削除する
        rm -rf /usr/lib/smb-conf-editor
        # Polkitポリシーファイルも念のため削除する
        rm -f /usr/share/polkit-1/actions/com.smbconfeditor.helper.policy
        ;;
esac
exit 0
EOF
# postrm に実行権限を付与
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# =============================================================================
# 4. アプリケーションファイルの配置 (/usr/lib)
# =============================================================================
LIB_DIR="$BUILD_DIR/usr/lib/smb-conf-editor"
mkdir -p "$LIB_DIR"
# メインスクリプト、Pythonパッケージ、ヘルパースクリプトをコピー
cp -r main.py smb_editor helpers "$LIB_DIR/"

# Pythonライブラリのバンドル（vendorディレクトリに配置）
if [ -f "requirements.txt" ]; then
    echo "Python依存パッケージをバンドル中..."
    # --no-cache-dir: キャッシュを使わずクリーンにインストール
    # --root-user-action=ignore: sudo実行時のroot警告を抑制
    python3 -m pip install --target "$LIB_DIR/vendor" --ignore-installed --no-cache-dir --root-user-action=ignore -r requirements.txt
fi

# =============================================================================
# 5. 実行ラッパースクリプトの生成 (/usr/bin)
# =============================================================================
mkdir -p "$BUILD_DIR/usr/bin"
cat <<'EOF' > "$BUILD_DIR/usr/bin/smb-conf-editor"
#!/bin/sh
# バンドルされたライブラリにPythonパスを通して起動する
export PYTHONPATH="/usr/lib/smb-conf-editor/vendor:$PYTHONPATH"
exec /usr/bin/python3 /usr/lib/smb-conf-editor/main.py "$@"
EOF

# =============================================================================
# 6. デスクトップエントリ・アイコン・Polkitポリシーの配置
# =============================================================================

# --- Polkitポリシーファイル ---
mkdir -p "$BUILD_DIR/usr/share/polkit-1/actions"
[ -f packaging/com.smbconfeditor.helper.policy ] && \
    cp packaging/com.smbconfeditor.helper.policy "$BUILD_DIR/usr/share/polkit-1/actions/"

# --- デスクトップエントリ ---
mkdir -p "$BUILD_DIR/usr/share/applications"
[ -f packaging/smb-conf-editor.desktop ] && \
    cp packaging/smb-conf-editor.desktop "$BUILD_DIR/usr/share/applications/"

# --- アイコン（pixmaps - 後方互換） ---
mkdir -p "$BUILD_DIR/usr/share/pixmaps"
[ -f packaging/smb-conf-editor.png ] && \
    cp packaging/smb-conf-editor.png "$BUILD_DIR/usr/share/pixmaps/"

# --- アイコン（hicolor - FHS準拠） ---
# デスクトップ環境が標準で参照するアイコンテーマディレクトリに配置
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps"
[ -f packaging/smb-conf-editor.png ] && \
    cp packaging/smb-conf-editor.png "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps/"

# =============================================================================
# 7. ドキュメントの配置 (/usr/share/doc)
# =============================================================================
DOC_DIR="$BUILD_DIR/usr/share/doc/$PKG_NAME"
mkdir -p "$DOC_DIR"

# --- copyrightファイルの生成（Debianポリシー必須） ---
cat <<EOF > "$DOC_DIR/copyright"
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

Files: *
Copyright: $(date +%Y) Developer
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
EOF

# --- changelogファイルの生成（gzip圧縮） ---
cat <<EOF | gzip -9 > "$DOC_DIR/changelog.Debian.gz"
$PKG_NAME ($VERSION) stable; urgency=low

  * バージョン $VERSION リリース

 -- Developer <dev@example.com>  $(date -R)
EOF

# =============================================================================
# 8. 権限の一括修正
# =============================================================================
echo "権限を修正中..."
# 全てのディレクトリを 755 (drwxr-xr-x) に設定
find "$BUILD_DIR" -type d -exec chmod 755 {} +
# 全てのファイルを 644 (-rw-r--r--) に設定
find "$BUILD_DIR" -type f -exec chmod 644 {} +
# 実行が必要なファイルに 755 権限を付与
chmod 755 "$BUILD_DIR/DEBIAN/postinst"
chmod 755 "$BUILD_DIR/DEBIAN/postrm"
chmod 755 "$BUILD_DIR/usr/bin/smb-conf-editor"
chmod 755 "$LIB_DIR/main.py"
# helpers 内のシェルスクリプトも実行可能にする
find "$LIB_DIR/helpers" -type f -name "*.sh" -exec chmod 755 {} +

# =============================================================================
# 9. Installed-Size の算出と control への追記
# =============================================================================
# パッケージのインストールサイズ（KB）を算出して control に追加
INSTALLED_SIZE=$(du -sk "$BUILD_DIR" | cut -f1)
echo "Installed-Size: $INSTALLED_SIZE" >> "$BUILD_DIR/DEBIAN/control"

# =============================================================================
# 10. パッケージの作成
# =============================================================================
echo "fakeroot でパッケージを作成中..."
fakeroot dpkg-deb --build "$BUILD_DIR"

# =============================================================================
# 11. ビルド成果物の所有者を修正（sudo実行時の対応）
# =============================================================================
# sudo経由で実行された場合、build_deb/ の所有者がrootになるため
# 元のユーザーに所有権を戻す
if [ -n "$SUDO_USER" ]; then
    echo "ビルド成果物の所有者を ${SUDO_USER} に変更中..."
    chown -R "$SUDO_USER:$(id -gn "$SUDO_USER")" "build_deb"
fi

echo ""
echo "======================================"
echo "✅ ビルド成功！"
echo "作成されたファイル: build_deb/${PKG_NAME}_${VERSION}_all.deb"
echo "インストール方法: sudo apt install ./build_deb/${PKG_NAME}_${VERSION}_all.deb"
echo "======================================"
