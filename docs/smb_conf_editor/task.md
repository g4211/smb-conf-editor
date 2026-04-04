# Samba設定エディター - 改善タスクリスト (v2)

## 改善1: パスワード入力のバッチ化（最高優先度）
- [x] smb-helper.sh に apply-all バッチコマンド追加
- [x] apply_manager.py を apply-all 対応に書き換え

## 改善2: [適用]ボタン統合 + UI用語改善
- [x] app.py - [適用][再読み込み][テーマ]をタブ上段に配置、統合適用ロジック
- [x] shares_tab.py - [適用]ボタン削除、用語変更（共有名/参照/読み取り専用）
- [x] global_tab.py - [適用]ボタン削除、用語変更
- [x] advanced_tab.py - 用語変更（エディターで編集/参照/確認）
- [x] history_tab.py - 用語変更（参照）
- [x] constants.py - カテゴリーラベル用語更新、バージョンを1.1.0に更新

## 改善3: 共有フォルダのcomment入力欄
- [x] shares_tab.py - comment入力欄追加、smb.confのcommentパラメータに書き込み
- [x] app.py - バックアップコメント自動生成（[共有名] コメント形式）

## 改善4: ディレクトリ存在確認（FocusOut時）
- [x] system_utils.py - find_missing_path_part() 関数追加
- [x] shares_tab.py - FocusOut時の確認ダイアログ、「📁 作成予定」ラベル表示
- [x] 「参照」で選んだディレクトリは作成予定を自動解除

## 改善5: hosts allowバリデーション拡張
- [x] system_utils.py - IPv6アドレス/ネットワーク対応
- [x] system_utils.py - ホスト名/ドメイン名対応
- [x] system_utils.py - EXCEPT構文対応
- [x] system_utils.py - 999.999.999.999 等の無効IPv4がホスト名に誤マッチしないガード

## 改善6: テスト・検証
- [x] 構文チェック（py_compile）: 8モジュール合格
- [x] バリデーションテスト: 12/12 合格
- [x] ディレクトリ存在チェックテスト: 合格
- [x] 全モジュールインポート: 19/19 成功
- [ ] GUI動作確認（デスクトップ環境で python3 main.py）

## 追加改善（UI/UX微調整＆Sambaユーザー管理）
- [x] `app.py` - [再読み込み]幅の調整とアイコン（🔄）への変更
- [x] `app.py` - emptyカードでの処理続行バグ修正、テーマ設定永続化＋OS対応
- [x] `system_utils.py` - 3状態(登録/有効/無効)管理の対応
- [x] `smb-helper.sh` - `enable-samba-user`, `disable-samba-user`, `remove-samba-user` 追加
- [x] `advanced_tab.py` - ツールタブに Sambaユーザー管理 UI を追加
- [x] `shares_tab.py` - 無効Sambaユーザーの自動有効化、凡例・アイコン改善
