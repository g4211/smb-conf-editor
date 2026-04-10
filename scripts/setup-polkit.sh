#!/bin/bash

# プロジェクトルートディレクトリの絶対パスを取得（scripts/ の親ディレクトリ）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HELPER_PATH="$PROJECT_DIR/helpers/smb-helper.sh"

if [ ! -f "$HELPER_PATH" ]; then
    echo "エラー: $HELPER_PATH が見つかりません。"
    exit 1
fi

POLICY_FILE="/tmp/com.smbconfeditor.helper.policy"
DEST_DIR="/usr/share/polkit-1/actions"

# ポリシーXMLファイルを一時的に生成
cat <<EOF > "$POLICY_FILE"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="com.smbconfeditor.helper.pkexec">
    <description>Run SMB Config Editor Helper</description>
    <message>Authentication is required to run SMB Config Editor Helper</message>
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

echo "以下のスクリプトにパスワードなしのroot実行権限をPolkitシステムへ登録します:"
echo "パス: $HELPER_PATH"
echo ""
echo "システムファイルの書き換えを行うため、1度だけパスワードを入力してください。"

# ポリシーファイルをシステムディレクトリに配置する
pkexec sh -c "cp '$POLICY_FILE' '$DEST_DIR/com.smbconfeditor.helper.policy' && chmod 644 '$DEST_DIR/com.smbconfeditor.helper.policy'"

if [ $? -eq 0 ]; then
    echo ""
    echo "成功しました！"
    echo "今後、Samba設定エディターで[適用]ボタン等を押した際にパスワード入力は求められません。"
    echo "※もし今後このアプリのフォルダを移動させた場合は、移動先でもう一度このスクリプトを実行してください。"
else
    echo ""
    echo "エラー: ポリシーの登録に失敗またはキャンセルされました。"
fi

# 一時ファイルを削除
rm -f "$POLICY_FILE"
