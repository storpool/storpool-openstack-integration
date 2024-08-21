# SPDX-FileCopyrightText: 2021 - 2024  StorPool <support@storpool.com>
# SPDX-License-Identifier: BSD-2-Clause
"""Yet Another INI-style-file Parser."""

from __future__ import annotations

import pathlib
import re
import typing

from . import defs


if typing.TYPE_CHECKING:
    from typing import Final


class VariantYAIError(defs.VariantError):
    """An error that occurred while parsing an INI-like file."""


_RE_YAIP_LINE = re.compile(
    r"""
    ^ (?:
        (?P<comment> \s* (?: \# .* )? )
        |
        (?:
            (?P<varname> [A-Za-z0-9_]+ )
            =
            (?P<full>
                (?P<oquot> ["'] )?
                (?P<quoted> .*? )
                (?P<cquot> ["'] )?
            )
        )
    ) $ """,
    re.X,
)

_SINGLE_QUOTE = "'"


class YAIParser:
    """Yet another INI-like file parser, this time for /etc/os-release."""

    filename: pathlib.Path
    data: dict[str, str]

    def __init__(self, filename: str) -> None:
        """Initialize a YAIParser object: store the filename."""
        self.filename = pathlib.Path(filename)
        self.data = {}

    def parse_line(self, line: str | bytes) -> tuple[str, str] | None:
        """Convert a single var=value line to a string, then parse it."""
        if isinstance(line, str):
            return self._parse_line_str(line)

        try:
            str_line: Final = line.decode("UTF-8")
        except UnicodeDecodeError as err:
            raise VariantYAIError(
                f"Invalid {self.filename} line, not a valid UTF-8 string: {line!r}: {err}",
            ) from err
        return self._parse_line_str(str_line)

    def _parse_line_quoted_single(
        self,
        line: str,
        varname: str,
        quoted: str,
        cquot: str,
    ) -> tuple[str, str] | None:
        """Parse a value enclosed in single quotes."""
        if _SINGLE_QUOTE in quoted:
            raise VariantYAIError(
                f"Weird {self.filename} line, the quoted content "
                f"contains the quote character: {line!r}",
            )
        if cquot != _SINGLE_QUOTE:
            raise VariantYAIError(
                f"Weird {self.filename} line, open/close quote mismatch: {line!r}",
            )

        return (varname, quoted)

    def _parse_line_unquoted(self, line: str, varname: str, quoted: str) -> tuple[str, str] | None:
        """Escape any characters preceded by a backslash."""
        res = ""
        while quoted:
            try:
                idx = quoted.index("\\")
            except ValueError:
                res += quoted
                break

            if idx == len(quoted) - 1:
                raise VariantYAIError(
                    f"Weird {self.filename} line, backslash at "
                    f"the end of the quoted string: {line!r}",
                )
            res += quoted[:idx] + quoted[idx + 1]
            quoted = quoted[idx + 2 :]

        return (varname, res)

    def _parse_line_str(self, line: str) -> tuple[str, str] | None:
        """Parse a single var=value line."""
        if not (mline := _RE_YAIP_LINE.match(line)):
            raise VariantYAIError(f"Unexpected {self.filename} line: {line!r}")
        if mline.group("comment") is not None:
            return None

        varname, oquot, cquot, quoted, full = (
            mline.group("varname"),
            mline.group("oquot"),
            mline.group("cquot"),
            mline.group("quoted"),
            mline.group("full"),
        )

        if oquot == _SINGLE_QUOTE:
            return self._parse_line_quoted_single(line, varname, quoted, cquot)

        if oquot is None:
            quoted = full
        elif cquot != oquot:
            raise VariantYAIError(
                f"Weird {self.filename} line, open/close quote mismatch: {line!r}",
            )

        return self._parse_line_unquoted(line, varname, quoted)

    def parse(self) -> dict[str, str]:
        """Parse a file, store and return the result."""
        contents: Final = self.filename.read_text(encoding="UTF-8")
        data: Final = {}
        for line in contents.splitlines():
            if (res := self.parse_line(line)) is None:
                continue
            data[res[0]] = res[1]

        self.data = data
        return data

    def get(self, key: str | bytes) -> str | None:
        """Get a value parsed from the configuration file."""
        key_str: Final = key.decode("UTF-8") if isinstance(key, bytes) else key
        return self.data.get(key_str)
