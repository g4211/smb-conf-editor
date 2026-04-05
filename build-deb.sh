#!/bin/bash
# DEBパッケージビルドスクリプト

# エラー発生時に停止
set -e

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# バージョンの抽出 (constants.pyからAPP_VERSIONを読み取る)
VERSION=$(grep -oP 'APP_VERSION\s*=\s*"\K[^"]+' smb_editor/constants.py || echo "1.1.0")

PKG_NAME="smb-conf-editor_${VERSION}_all"
BUILD_DIR="build_deb/$PKG_NAME"

echo "Building Debian package: $PKG_NAME"

# 古いディレクトリをクリーンアップ
rm -rf "build_deb"
mkdir -p "$BUILD_DIR"

# === 1. パッケージ情報 (DEBIAN/control) ===
mkdir -p "$BUILD_DIR/DEBIAN"
cat <<EOF > "$BUILD_DIR/DEBIAN/control"
Package: smb-conf-editor
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-tk, policykit-1
Maintainer: Developer <dev@example.com>
Description: Samba Configuration Editor
 A GUI tool for configuring Samba shares and settings on Ubuntu.
EOF

# === 2. アプリ本体の配置 (/opt) ===
APP_DIR="$BUILD_DIR/opt/smb-conf-editor"
mkdir -p "$APP_DIR"
# 必要なファイルをコピー
cp -r main.py smb_editor helpers "$APP_DIR/"

# 権限変更
chmod +x "$APP_DIR/main.py"
chmod +x "$APP_DIR/helpers/smb-helper.sh"

# === 3. Python依存ライブラリのバンドル (/opt/smb-conf-editor/vendor) ===
echo "Pythonライブラリをバンドルしています..."
if [ -f "requirements.txt" ]; then
    # vendorへpip install (--ignore-installed を付けてシステム環境から切り離す)
    python3 -m pip install --target "$APP_DIR/vendor" --ignore-installed -r requirements.txt
fi

# === 4. 実行コマンド配置 (/usr/bin) ===
mkdir -p "$BUILD_DIR/usr/bin"
cat <<EOF > "$BUILD_DIR/usr/bin/smb-conf-editor"
#!/bin/sh
exec /usr/bin/python3 /opt/smb-conf-editor/main.py "\$@"
EOF
chmod +x "$BUILD_DIR/usr/bin/smb-conf-editor"

# === 5. Polkitルールの配置 (/usr/share/polkit-1/actions) ===
POLKIT_DIR="$BUILD_DIR/usr/share/polkit-1/actions"
mkdir -p "$POLKIT_DIR"
cp packaging/com.smbconfeditor.helper.policy "$POLKIT_DIR/"
chmod 644 "$POLKIT_DIR/com.smbconfeditor.helper.policy"

# === 6. Desktopエントリの配置 (/usr/share/applications) ===
APPS_DIR="$BUILD_DIR/usr/share/applications"
mkdir -p "$APPS_DIR"
cp packaging/smb-conf-editor.desktop "$APPS_DIR/"
chmod 644 "$APPS_DIR/smb-conf-editor.desktop"

# === 7. DEBファイルの作成 ===
echo "パッケージを作成中..."
dpkg-deb --build "$BUILD_DIR"

echo "======================================"
echo "ビルド成功！"
echo "作成されたファイル: build_deb/${PKG_NAME}.deb"
echo "インストール方法: sudo apt install ./build_deb/${PKG_NAME}.deb"
echo "======================================"
