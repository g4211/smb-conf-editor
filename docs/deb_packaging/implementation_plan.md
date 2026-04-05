# DEBパッケージ作成スクリプトの実装計画

Ubuntu 24.04の環境において、Pythonスクリプトを手軽にインストール・利用できるようにするための`.deb`パッケージ作成スクリプト（`build-deb.sh`）を実装します。

## 対象の課題と修正方針

### 1. Python外部ライブラリ（`sv-ttk`）の依存解決
- **課題**: Ubuntu 24.04では「PEP 668」により、OS全体への`pip install`が制限されています。
- **解決策**: `.deb`パッケージ作成時に`sv-ttk`をパッケージ専用の`vendor/`ディレクトリにダウンロード（バンドル）して含める方式を採用します。これによりインストーラーが`pip`に依存せず、オフラインでもインストールが可能になります。

### 2. システムディレクトリの適正化
- アプリの本体は `/opt/smb-conf-editor/` 配下に配置します。
- 起動用のコマンドとして、`/usr/bin/smb-conf-editor` に実行用のスクリプト（またはシンボリックリンク）を配置します。

### 3. PolkitポリシーとDesktopエントリの同梱
- 既存の`setup-polkit.sh`は手動実行用でしたが、debパッケージ化に伴い、ポリシーファイル（`/usr/share/polkit-1/actions/com.smbconfeditor.helper.policy`）とデスクトップアイコン（`/usr/share/applications/smb-conf-editor.desktop`）をパッケージに直接含めます。
- インストールした瞬間に、パスワードなし実行やGUIのアプリケーション一覧への表示が完了するようにします。アイコンはシステムの組み込みアイコン（`preferences-system-network`など）を使用します。

## 修正のステップ

### 1. アプリケーション本体の動作修正 (`main.py`)
起動時に `os.path.join(app_dir, 'vendor')` を `sys.path` に追加する処理を追記し、パッケージにバンドルされたライブラリを優先的に読み込めるようにします。

### 2. パッケージング用スクリプトディレクトリ（新規）
プロジェクトルートに `packaging/` フォルダを作成し、以下のファイルを配置します。
- **`packaging/smb-conf-editor.desktop`**: Ubuntuのアプリーケーションランチャーに表示するための定義ファイル。
- **`packaging/com.smbconfeditor.helper.policy`**: Polkitポリシーファイル。インストール先である `/opt/smb-conf-editor/helpers/smb-helper.sh` をパスワードなしで実行可能にするためのルールを定義します。

### 3. ビルドスクリプト作成 (`build-deb.sh`)
実行すると以下の手順を自動で行い、`.deb`パッケージを生成するスクリプトをプロジェクト直下に作成します。
1. 作業ディレクトリ `build_deb/smb-conf-editor_<バージョン>_all/` を作成
2. `DEBIAN/control`、`DEBIAN/postinst` 等を自動生成
3. アプリケーション本体のソースコードを `opt/smb-conf-editor/` へコピー
4. `pip install --target build_deb/.../vendor -r requirements.txt` を実行し依存をバンドル
5. DesktopファイルとPolkit設定ファイルをシステム準拠のパスにコピー
6. 実行可能権限の調整
7. `dpkg-deb --build` で `.deb` ファイルを出力

## 確認プラン
1. `./build-deb.sh` を実行し、エラーなく `.deb` パッケージが作成されることを確認。
2. 作成されたパッケージの内容 (`dpkg-deb -c`) を確認。

上記の計画で、パッケージング用のスクリプト作成を進めてよろしいでしょうか？
