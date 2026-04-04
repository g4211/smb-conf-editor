# -*- coding: utf-8 -*-
"""
smb.conf 書き込みモジュール
パース済みのSmbConfigを変更し、ファイルに書き出す。
変更箇所のみを更新し、コメントや構造を保持する設計。
"""

import copy
from typing import Optional

from .smb_parser import SmbConfig, SmbSection, SmbLine


class SmbConfWriter:
    """smb.confの書き込みクラス"""

    def __init__(self, config: SmbConfig):
        """パース済みの設定データから書き込みオブジェクトを初期化する"""
        # 元の設定を変更しないようにディープコピーを作成
        self._config = copy.deepcopy(config)

    @property
    def config(self) -> SmbConfig:
        """現在の設定データを返す"""
        return self._config

    def update_param(self, section_name: str, key: str, value: str) -> bool:
        """
        指定セクション内のパラメータ値を更新する。
        パラメータが存在しない場合はセクション末尾に追加する。
        戻り値: 変更が行われた場合True
        """
        section = self._config.get_section(section_name)
        if section is None:
            return False

        key_lower = key.lower().strip()
        # 既存のパラメータ行を検索して更新
        for line in section.lines:
            if line.line_type == "param" and line.key == key_lower:
                # インデントを保持して行を再構成
                indent = line.indent if line.indent else "   "
                line.raw = f"{indent}{key_lower} = {value}"
                line.value = value
                return True

        # パラメータが見つからない場合はセクション末尾に追加
        self._add_param_to_section(section, key_lower, value)
        return True

    def remove_param(self, section_name: str, key: str) -> bool:
        """
        指定セクション内のパラメータを削除する。
        戻り値: 削除が行われた場合True
        """
        section = self._config.get_section(section_name)
        if section is None:
            return False

        key_lower = key.lower().strip()
        # 該当するパラメータ行を検索して削除
        original_count = len(section.lines)
        section.lines = [
            line for line in section.lines
            if not (line.line_type == "param" and line.key == key_lower)
        ]
        # 削除されたかどうかを返す
        return len(section.lines) < original_count

    def add_section(self, name: str, params: dict[str, str]) -> bool:
        """
        新しいセクションをファイル末尾に追加する。
        戻り値: 追加が成功した場合True
        """
        # 同名のセクションが既に存在する場合は追加しない
        if self._config.get_section(name) is not None:
            return False

        # セクションの行リストを構築
        lines = []

        # 空行を追加（前のセクションとの区切り）
        blank_line = SmbLine(raw="", line_number=0, line_type="blank")
        lines.append(blank_line)

        # セクションヘッダー行を作成
        header_line = SmbLine(
            raw=f"[{name}]",
            line_number=0,
            line_type="section",
            section_name=name,
        )
        lines.append(header_line)

        # パラメータ行を追加
        for key, value in params.items():
            param_line = SmbLine(
                raw=f"   {key} = {value}",
                line_number=0,
                line_type="param",
                key=key.lower(),
                value=value,
                indent="   ",
            )
            lines.append(param_line)

        # SmbSectionオブジェクトを作成
        new_section = SmbSection(
            name=name,
            name_lower=name.lower(),
            lines=lines,
            header_line=header_line,
        )

        # セクションリストに追加
        self._config.sections.append(new_section)
        return True

    def remove_section(self, name: str) -> bool:
        """
        指定した名前のセクションを削除する。
        戻り値: 削除が行われた場合True
        """
        name_lower = name.lower().strip()
        original_count = len(self._config.sections)
        self._config.sections = [
            s for s in self._config.sections
            if s.name_lower != name_lower
        ]
        return len(self._config.sections) < original_count

    def set_section_params(self, section_name: str, params: dict[str, str],
                           keep_unlisted: bool = True) -> bool:
        """
        セクションのパラメータをまとめて設定する。
        keep_unlisted=True の場合、paramsに含まれないパラメータは保持する。
        keep_unlisted=False の場合、paramsに含まれないパラメータは削除する。
        """
        section = self._config.get_section(section_name)
        if section is None:
            return False

        if not keep_unlisted:
            # 指定されていないパラメータを削除
            existing_keys = {line.key for line in section.lines if line.line_type == "param"}
            new_keys = {k.lower().strip() for k in params.keys()}
            for key_to_remove in existing_keys - new_keys:
                self.remove_param(section_name, key_to_remove)

        # パラメータを設定（存在すれば更新、なければ追加）
        for key, value in params.items():
            self.update_param(section_name, key, value)

        return True

    def generate_content(self) -> str:
        """変更後のsmb.conf全体の内容を文字列として生成する"""
        lines = []

        # プリアンブル（ファイル先頭のコメント・空行）を出力
        for line in self._config.preamble_lines:
            lines.append(line.raw)

        # 各セクションを出力
        for section in self._config.sections:
            for line in section.lines:
                lines.append(line.raw)

        # ファイル末尾に改行を追加
        content = "\n".join(lines)
        if not content.endswith("\n"):
            content += "\n"
        return content

    def write_to_file(self, filepath: str) -> None:
        """変更後の内容をファイルに書き出す"""
        content = self.generate_content()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def _add_param_to_section(self, section: SmbSection, key: str, value: str) -> None:
        """セクションの末尾（最後のパラメータ行の後）にパラメータを追加する"""
        # 最後のパラメータ行の位置を見つける
        insert_index = len(section.lines)
        for i in range(len(section.lines) - 1, -1, -1):
            if section.lines[i].line_type in ("param", "commented_param"):
                insert_index = i + 1
                break

        # 新しいパラメータ行を作成（セクション内の一般的なインデントを使用）
        indent = self._get_section_indent(section)
        new_line = SmbLine(
            raw=f"{indent}{key} = {value}",
            line_number=0,
            line_type="param",
            key=key.lower(),
            value=value,
            indent=indent,
        )
        # 指定位置に挿入
        section.lines.insert(insert_index, new_line)

    def _get_section_indent(self, section: SmbSection) -> str:
        """セクション内のパラメータ行で使われているインデントを取得する"""
        for line in section.lines:
            if line.line_type == "param" and line.indent:
                return line.indent
        # デフォルトのインデント（スペース3つ）
        return "   "
