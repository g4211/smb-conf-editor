# -*- coding: utf-8 -*-
"""
smb.conf パーサーモジュール
smb.confファイルを解析し、コメントや空行を含む全構造を保持する。
セクション・パラメータの読み取りと、構造化されたデータの提供を行う。
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SmbLine:
    """smb.confの1行を表すデータクラス"""
    raw: str                    # 元の行テキスト（改行なし）
    line_number: int            # ファイル内の行番号（1始まり）
    line_type: str              # 行の種類: 'comment' | 'blank' | 'section' | 'param' | 'commented_param'
    key: str = ""               # パラメータ名（小文字正規化済み、param/commented_param時に設定）
    value: str = ""             # パラメータ値（param/commented_param時に設定）
    section_name: str = ""      # セクション名（section時に設定）
    indent: str = ""            # 行頭のインデント（空白文字）


@dataclass
class SmbSection:
    """smb.confの1セクションを表すデータクラス"""
    name: str                              # セクション名（小文字正規化なし、元の表記）
    name_lower: str                        # セクション名（小文字正規化済み）
    lines: list[SmbLine] = field(default_factory=list)   # セクション内の全行
    start_line: int = 0                    # ファイル内の開始行番号
    end_line: int = 0                      # ファイル内の終了行番号
    header_line: Optional[SmbLine] = None  # [section] ヘッダー行

    def get_param(self, key: str) -> Optional[str]:
        """セクション内のパラメータ値を取得する"""
        # キーを小文字に正規化して検索
        key_lower = key.lower().strip()
        for line in self.lines:
            # 有効なパラメータ行（コメントアウトされていない）のみ検索
            if line.line_type == "param" and line.key == key_lower:
                return line.value
        return None

    def get_all_params(self) -> dict[str, str]:
        """セクション内の全パラメータをdict形式で返す"""
        params = {}
        for line in self.lines:
            # 有効なパラメータ行のみを収集
            if line.line_type == "param":
                params[line.key] = line.value
        return params


@dataclass
class SmbConfig:
    """smb.conf全体を表すデータクラス"""
    # ファイル先頭のコメント・空行（最初のセクションヘッダーより前）
    preamble_lines: list[SmbLine] = field(default_factory=list)
    # セクションのリスト（出現順）
    sections: list[SmbSection] = field(default_factory=list)
    # 元のファイルパス
    filepath: str = ""

    def get_section(self, name: str) -> Optional[SmbSection]:
        """指定した名前のセクションを取得する"""
        name_lower = name.lower().strip()
        for section in self.sections:
            if section.name_lower == name_lower:
                return section
        return None

    def get_section_names(self) -> list[str]:
        """全セクション名のリストを返す"""
        return [s.name for s in self.sections]


class SmbConfParser:
    """smb.confのパーサークラス"""

    # セクションヘッダーの正規表現パターン（例: [global]、[shared folder]）
    _SECTION_RE = re.compile(r'^\s*\[([^\]]+)\]\s*$')
    # パラメータ行の正規表現パターン（例: workgroup = WORKGROUP）
    _PARAM_RE = re.compile(r'^(\s*)([\w\s]+?)\s*=\s*(.*?)\s*$')
    # コメントアウトされたパラメータ行の正規表現パターン（例: ; workgroup = WORKGROUP）
    _COMMENTED_PARAM_RE = re.compile(r'^(\s*)[;#]\s*([\w\s]+?)\s*=\s*(.*?)\s*$')

    def parse(self, filepath: str) -> SmbConfig:
        """smb.confファイルをパースしてSmbConfigを返す"""
        # ファイルを読み込む
        with open(filepath, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()

        # SmbConfigオブジェクトを初期化
        config = SmbConfig(filepath=filepath)
        # 現在処理中のセクション（None = プリアンブル部分）
        current_section: Optional[SmbSection] = None

        for line_num, raw_line in enumerate(raw_lines, start=1):
            # 末尾の改行を除去
            stripped = raw_line.rstrip('\n').rstrip('\r')
            # 行をパースしてSmbLineオブジェクトを作成
            smb_line = self._parse_line(stripped, line_num)

            if smb_line.line_type == "section":
                # 新しいセクションが始まった場合
                if current_section is not None:
                    # 前のセクションの終了行を設定
                    current_section.end_line = line_num - 1

                # 新しいセクションを作成
                current_section = SmbSection(
                    name=smb_line.section_name,
                    name_lower=smb_line.section_name.lower(),
                    start_line=line_num,
                    header_line=smb_line,
                )
                # ヘッダー行もセクションの行リストに含める
                current_section.lines.append(smb_line)
                # セクションリストに追加
                config.sections.append(current_section)
            elif current_section is not None:
                # セクション内の行として追加
                current_section.lines.append(smb_line)
            else:
                # プリアンブル部分（最初のセクションより前）の行
                config.preamble_lines.append(smb_line)

        # 最後のセクションの終了行を設定
        if current_section is not None:
            current_section.end_line = len(raw_lines)

        return config

    def parse_string(self, content: str, filepath: str = "<string>") -> SmbConfig:
        """文字列からsmb.confをパースする（テスト用）"""
        import tempfile
        import os
        # 一時ファイルに書き出してパース
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False,
                                         encoding='utf-8') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            config = self.parse(tmp_path)
            config.filepath = filepath
            return config
        finally:
            # 一時ファイルを削除
            os.unlink(tmp_path)

    def _parse_line(self, line: str, line_number: int) -> SmbLine:
        """1行をパースしてSmbLineを返す"""
        # 空行チェック
        if not line.strip():
            return SmbLine(
                raw=line,
                line_number=line_number,
                line_type="blank",
            )

        # セクションヘッダーチェック（例: [global]）
        section_match = self._SECTION_RE.match(line)
        if section_match:
            section_name = section_match.group(1).strip()
            return SmbLine(
                raw=line,
                line_number=line_number,
                line_type="section",
                section_name=section_name,
            )

        # コメント行チェック（# または ; で始まる行）
        stripped = line.lstrip()
        if stripped.startswith('#') or stripped.startswith(';'):
            # コメントアウトされたパラメータかどうかを確認
            commented_match = self._COMMENTED_PARAM_RE.match(line)
            if commented_match:
                indent = commented_match.group(1)
                key = commented_match.group(2).strip().lower()
                value = commented_match.group(3).strip()
                return SmbLine(
                    raw=line,
                    line_number=line_number,
                    line_type="commented_param",
                    key=key,
                    value=value,
                    indent=indent,
                )
            else:
                # 純粋なコメント行
                return SmbLine(
                    raw=line,
                    line_number=line_number,
                    line_type="comment",
                )

        # パラメータ行チェック（例: workgroup = WORKGROUP）
        param_match = self._PARAM_RE.match(line)
        if param_match:
            indent = param_match.group(1)
            key = param_match.group(2).strip().lower()
            value = param_match.group(3).strip()
            return SmbLine(
                raw=line,
                line_number=line_number,
                line_type="param",
                key=key,
                value=value,
                indent=indent,
            )

        # どれにも該当しない行はコメントとして扱う
        return SmbLine(
            raw=line,
            line_number=line_number,
            line_type="comment",
        )

    @staticmethod
    def get_share_sections(config: SmbConfig, system_sections: frozenset = None) -> list[SmbSection]:
        """共有フォルダセクションのみを返す（システムセクションを除外）"""
        from . import constants as const
        if system_sections is None:
            system_sections = const.SYSTEM_SECTIONS
        shares = []
        for section in config.sections:
            # システムセクションをフィルタリング
            if section.name_lower not in system_sections:
                shares.append(section)
        return shares
