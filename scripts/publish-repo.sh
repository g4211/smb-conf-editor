#!/bin/bash
# =============================================================================
# APTリポジトリ公開スクリプト
# debパッケージをビルドし、GitHub Pages上のAPTリポジトリに公開する
#
# 使い方:
#   bash scripts/publish-repo.sh          # ビルド＆公開
#   bash scripts/publish-repo.sh --init   # 初回セットアップ（リポジトリのクローン）
# =============================================================================

set -e

# === 設定 ===
GITHUB_USER="g4211"
REPO_NAME="apt-repo"
GPG_KEY_EMAIL="guzumi@gmail.com"
ORIGIN_LABEL="g4211"
REPO_DESCRIPTION="g4211 APTリポジトリ"

# === パスの設定 ===
# スクリプトのディレクトリからプロジェクトルートを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# APTリポジトリはプロジェクトの兄弟ディレクトリに配置
REPO_DIR="$(cd "$PROJECT_DIR/.." && pwd)/$REPO_NAME"

# === 必須ツールの確認 ===
check_tools() {
    local missing=()
    for cmd in dpkg-scanpackages apt-ftparchive gpg git gzip; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        echo "エラー: 以下のツールが見つかりません: ${missing[*]}" >&2
        echo "インストール: sudo apt install dpkg-dev apt-utils gnupg git" >&2
        exit 1
    fi
}

# === GPG鍵の確認 ===
check_gpg_key() {
    if ! gpg --list-secret-keys "$GPG_KEY_EMAIL" &>/dev/null; then
        echo "エラー: GPG秘密鍵が見つかりません: $GPG_KEY_EMAIL" >&2
        echo "gpg --full-generate-key で鍵を生成してください。" >&2
        exit 1
    fi
}

# === 初回セットアップ ===
init_repo() {
    echo "=== APTリポジトリの初回セットアップ ==="

    if [ -d "$REPO_DIR" ]; then
        echo "リポジトリは既に存在します: $REPO_DIR"
        echo "再初期化する場合は、先にディレクトリを削除してください。"
        exit 1
    fi

    # リポジトリをクローン
    echo "GitHubからリポジトリをクローン中..."
    cd "$(dirname "$REPO_DIR")"
    git clone "git@github.com:${GITHUB_USER}/${REPO_NAME}.git"

    # 公開鍵をエクスポート
    echo "GPG公開鍵をエクスポート中..."
    gpg --armor --export "$GPG_KEY_EMAIL" > "$REPO_DIR/KEY.gpg"

    # ユーザー向けインストールスクリプトを作成
    cat <<'INSTALL_EOF' > "$REPO_DIR/install.sh"
#!/bin/bash
# =============================================================================
# smb-conf-editor APTリポジトリ追加スクリプト
# このスクリプトを実行すると、APTリポジトリが追加され、
# apt install でsmb-conf-editorをインストールできるようになります
# =============================================================================

set -e

REPO_URL="https://g4211.github.io/apt-repo"
KEYRING_PATH="/etc/apt/keyrings/g4211-apt-repo.gpg"
LIST_PATH="/etc/apt/sources.list.d/g4211-apt-repo.list"

echo "=== smb-conf-editor APTリポジトリの追加 ==="

# キーリングディレクトリの作成
sudo mkdir -p /etc/apt/keyrings

# GPG公開鍵のダウンロードとインストール
echo "GPG公開鍵をインストール中..."
curl -fsSL "${REPO_URL}/KEY.gpg" | sudo gpg --dearmor -o "$KEYRING_PATH"

# APTソースリストの作成
echo "APTソースリストを作成中..."
echo "deb [signed-by=${KEYRING_PATH}] ${REPO_URL} ./" | sudo tee "$LIST_PATH" > /dev/null

# パッケージリストの更新
echo "パッケージリストを更新中..."
sudo apt update

echo ""
echo "=== セットアップ完了！ ==="
echo "以下のコマンドでインストールできます:"
echo "  sudo apt install smb-conf-editor"
echo ""
echo "アンインストール:"
echo "  sudo apt remove smb-conf-editor"
echo ""
echo "リポジトリの削除:"
echo "  sudo rm $KEYRING_PATH $LIST_PATH"
echo "  sudo apt update"
INSTALL_EOF
    chmod +x "$REPO_DIR/install.sh"

    # README.mdを作成
    cat <<'README_EOF' > "$REPO_DIR/README.md"
# g4211 APTリポジトリ

Ubuntu向けのパッケージを配布するAPTリポジトリです。

## 提供パッケージ

| パッケージ名 | 説明 |
|---|---|
| smb-conf-editor | Samba設定エディター - GUIでsmb.confを編集 |

## インストール方法

### ワンライナー（推奨）

```bash
curl -fsSL https://g4211.github.io/apt-repo/install.sh | bash
```

### 手動セットアップ

```bash
# 1. GPG公開鍵のインストール
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://g4211.github.io/apt-repo/KEY.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/g4211-apt-repo.gpg

# 2. APTソースリストの追加
echo "deb [signed-by=/etc/apt/keyrings/g4211-apt-repo.gpg] https://g4211.github.io/apt-repo ./" | sudo tee /etc/apt/sources.list.d/g4211-apt-repo.list

# 3. パッケージリストの更新とインストール
sudo apt update
sudo apt install smb-conf-editor
```

## リポジトリの削除

```bash
sudo rm /etc/apt/keyrings/g4211-apt-repo.gpg /etc/apt/sources.list.d/g4211-apt-repo.list
sudo apt update
```
README_EOF

    echo ""
    echo "=== 初回セットアップ完了！ ==="
    echo "リポジトリの場所: $REPO_DIR"
    echo ""
    echo "次の手順:"
    echo "  1. このスクリプトを引数なしで再実行してパッケージを公開してください"
    echo "     bash scripts/publish-repo.sh"
    echo "  2. GitHubでPages設定を有効にしてください"
    echo "     Settings > Pages > Source: Deploy from a branch > Branch: main, / (root)"
}

# === パッケージの公開 ===
publish() {
    echo "================================================"
    echo "APTリポジトリへのパッケージ公開"
    echo "================================================"

    # リポジトリの存在確認
    if [ ! -d "$REPO_DIR/.git" ]; then
        echo "エラー: APTリポジトリが見つかりません: $REPO_DIR" >&2
        echo "先に --init で初回セットアップを実行してください:" >&2
        echo "  bash scripts/publish-repo.sh --init" >&2
        exit 1
    fi

    # --- 1. debパッケージのビルド ---
    echo ""
    echo "--- 1/6: debパッケージをビルド中... ---"
    cd "$PROJECT_DIR"
    bash build-deb.sh

    # debファイルを検索
    DEB_FILE=$(find build_deb -name "*.deb" -type f | head -1)
    if [ -z "$DEB_FILE" ]; then
        echo "エラー: debファイルが見つかりません" >&2
        exit 1
    fi
    DEB_BASENAME=$(basename "$DEB_FILE")
    echo "対象パッケージ: $DEB_BASENAME"

    # --- 2. リポジトリを最新に更新 ---
    echo ""
    echo "--- 2/6: リポジトリを更新中... ---"
    cd "$REPO_DIR"
    git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true

    # --- 3. debファイルをコピー（古いバージョンを削除） ---
    echo ""
    echo "--- 3/6: debファイルをリポジトリにコピー中... ---"
    # パッケージ名を取得してそのパッケージの古いdebを削除
    PKG_NAME=$(dpkg-deb --field "$PROJECT_DIR/$DEB_FILE" Package)
    rm -f "${REPO_DIR}/${PKG_NAME}_"*".deb"
    # 新しいdebをコピー
    cp "$PROJECT_DIR/$DEB_FILE" "$REPO_DIR/"

    # --- 4. Packagesファイルの生成 ---
    echo ""
    echo "--- 4/6: APTメタデータを生成中... ---"
    cd "$REPO_DIR"
    # Packagesファイルを生成（.debファイルをスキャン）
    dpkg-scanpackages --multiversion . 2>/dev/null > Packages
    gzip -9c Packages > Packages.gz

    # Releaseファイルを生成（チェックサム付き）
    apt-ftparchive release \
        -o APT::FTPArchive::Release::Origin="$ORIGIN_LABEL" \
        -o APT::FTPArchive::Release::Label="$REPO_DESCRIPTION" \
        -o APT::FTPArchive::Release::Suite="stable" \
        -o APT::FTPArchive::Release::Architectures="all" \
        . > Release

    # --- 5. GPG署名 ---
    echo ""
    echo "--- 5/6: GPG署名中... ---"
    # 既存の署名ファイルを削除
    rm -f Release.gpg InRelease
    # 分離署名（Release.gpg）
    gpg --default-key "$GPG_KEY_EMAIL" --batch --yes -abs -o Release.gpg Release
    # クリア署名（InRelease）
    gpg --default-key "$GPG_KEY_EMAIL" --batch --yes --clearsign -o InRelease Release
    # 公開鍵を更新
    gpg --armor --export "$GPG_KEY_EMAIL" > KEY.gpg

    # --- 6. コミット＆プッシュ ---
    echo ""
    echo "--- 6/6: GitHubにプッシュ中... ---"
    git add .
    git commit -m "パッケージ更新: ${DEB_BASENAME}"
    git push origin main 2>/dev/null || git push origin master

    echo ""
    echo "================================================"
    echo "✅ 公開完了！"
    echo "パッケージ: $DEB_BASENAME"
    echo "リポジトリURL: https://${GITHUB_USER}.github.io/${REPO_NAME}/"
    echo ""
    echo "ユーザーのインストール方法:"
    echo "  curl -fsSL https://${GITHUB_USER}.github.io/${REPO_NAME}/install.sh | bash"
    echo "  sudo apt install smb-conf-editor"
    echo "================================================"
}

# === メイン処理 ===
check_tools
check_gpg_key

case "${1:-}" in
    --init)
        init_repo
        ;;
    --help|-h)
        echo "使い方:"
        echo "  $0 --init   初回セットアップ（リポジトリのクローンと初期化）"
        echo "  $0          パッケージのビルドと公開"
        echo "  $0 --help   このヘルプを表示"
        ;;
    "")
        publish
        ;;
    *)
        echo "エラー: 不明なオプション: $1" >&2
        echo "$0 --help でヘルプを表示" >&2
        exit 1
        ;;
esac
