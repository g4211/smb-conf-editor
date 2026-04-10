# タスクリスト: ファイル配置整理 & build-deb.sh 改善

## ファイル配置整理

- [x] `helpers/com.github.smb-conf-editor.policy` を削除（polkit統一）
- [x] `setup-polkit.sh` を `scripts/` に移動（パス参照を更新）
- [x] ルートの `config.json` を削除
- [x] `README.md` のプロジェクト構成・手順を更新
- [x] `.gitignore` から `config.json` エントリを削除

## build-deb.sh 改善

### 重要度：高
- [x] #1: `policykit-1` → `polkitd, pkexec` に変更
- [x] #2: `copyright` ファイルの生成を追加
- [x] #3: `Description` を短い説明+長い説明に拡充
- [x] #4: `postinst` スクリプトを追加

### 重要度：中
- [x] #5: `pip` の存在確認を追加
- [x] #6: `fakeroot` の存在確認を追加
- [x] #7: `postrm` で `remove` 時にPolkitポリシー削除
- [x] #8: `Installed-Size` フィールドを追加
- [x] #9: `Homepage` フィールドを追加

### 重要度：低
- [x] #10: アイコンを `hicolor` にも配置
- [x] #11: `changelog` ファイルの生成を追加
- [x] #12: ビルドツールの依存チェック関数を追加

## 検証
- [x] build-deb.sh のビルドテスト → 成功
- [x] パッケージメタデータの確認 → 正常
- [x] パッケージ内のファイル配置の確認 → 正常
