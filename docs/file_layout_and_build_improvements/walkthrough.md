# ウォークスルー: ファイル配置整理 & build-deb.sh 改善

## 概要

プロジェクト内の非Pythonファイルの配置を整理し、`build-deb.sh` をDebianポリシーに準拠するよう全面改善した。

## 変更内容

### 1. ファイル配置の整理

| 変更 | 変更前 | 変更後 |
|------|--------|--------|
| Polkitポリシー統一 | `helpers/com.github.smb-conf-editor.policy` + `packaging/com.smbconfeditor.helper.policy` | `packaging/com.smbconfeditor.helper.policy` のみ |
| セットアップスクリプト移動 | `setup-polkit.sh`（ルート） | `scripts/setup-polkit.sh` |
| 不要ファイル削除 | `config.json`（ルート） | 削除（`~/.config/smb-conf-editor/config.json` を使用） |

#### `scripts/setup-polkit.sh` のパス修正

`scripts/` に移動したため、プロジェクトルートへの相対パス参照を修正：

```diff
-DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
-HELPER_PATH="$DIR/helpers/smb-helper.sh"
+SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
+PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
+HELPER_PATH="$PROJECT_DIR/helpers/smb-helper.sh"
```

### 2. build-deb.sh の改善（全12項目）

#### 重要度：高

- **#1**: 依存パッケージを `policykit-1` → `polkitd, pkexec` に変更（Ubuntu 24.04対応）
- **#2**: `/usr/share/doc/smb-conf-editor/copyright` を自動生成（MITライセンス全文）
- **#3**: `Description` を充実（短い説明 + 長い説明 + 機能一覧）
- **#4**: `postinst` スクリプトを追加（Polkitデーモンへの再読込通知）

#### 重要度：中

- **#5**: `python3 -m pip` の存在確認を `check_build_dependencies()` に追加
- **#6**: `fakeroot`, `dpkg-deb`, `gzip` の存在確認を追加
- **#7**: `postrm` で `remove` 時にPolkitポリシーファイルを削除する処理を追加
- **#8**: `du -sk` でパッケージサイズを算出し `Installed-Size` を `control` に追記
- **#9**: `Homepage` フィールドを `control` に追加

#### 重要度：低

- **#10**: アイコンを `/usr/share/icons/hicolor/256x256/apps/` にも配置（FHS準拠）
- **#11**: `changelog.Debian.gz` を `/usr/share/doc/` に生成
- **#12**: スクリプト冒頭で全ビルドツールの一括チェック関数を追加

### 3. その他の更新

- **README.md**: プロジェクト構成図、インストール手順をDEBパッケージ推奨に更新
- **.gitignore**: 不要な `config.json` エントリを削除

## 検証結果

- `build-deb.sh` のビルド → ✅ 成功
- `dpkg-deb --info` でメタデータ確認 → ✅ postinst, postrm, Homepage, Installed-Size, Description 全て正常
- `dpkg-deb --contents` でファイル配置確認 → ✅ polkit, hicolor, copyright, changelog 全て配置済み
