# SPDX-FileCopyrightText: 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Test the partial utf8-locale implementation."""

import os
import re
import subprocess

from sp_osi import u8loc


_RE_U8LOC = re.compile(
    r""" ^
    (?: [A-Za-z0-9_-]+ )
    \.
    (?: UTF-8 | utf8 )
    $ """,
    re.X,
)
"""Match the detected locale name."""


def test_u8loc() -> None:
    """Detect a UTF-8-capable locale, test it."""
    u8env = u8loc.detect()
    assert sorted(u8env.keys()) == ["LANGUAGE", "LC_ALL"]
    assert not u8env["LANGUAGE"]
    assert _RE_U8LOC.match(u8env["LC_ALL"])

    subenv = dict(os.environ)
    subenv.update(u8env)
    # Python 3.6 does not have `capture_output=True` yet.
    # The safe single-byte encoding is there in case the locale is not
    # defined and the locale(1) tool outputs some weird error message.
    res = subprocess.run(
        ["locale", "-c", "charmap"],
        bufsize=0,
        encoding="ISO-8859-15",
        env=subenv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if res.returncode != 0 or res.stderr:
        # We only allow this one to not really be defined.
        assert u8env["LC_ALL"] == "C.UTF-8", repr((res, u8env))
    else:
        assert res.stdout == "LC_CTYPE\nUTF-8\n", repr((res, u8env))
