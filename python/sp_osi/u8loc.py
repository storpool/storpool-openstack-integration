"""A simplified version of the utf8-locale library."""

import os
import subprocess

from typing import Dict


_LANGS = ["C", "en_US", "en_GB", "en_AU", "en_CA", "de_DE", "de_CH"]
"""A set of locale language codes to look for."""

_ENCODINGS = ["UTF-8", "utf8"]
"""The possible encoding suffixes for the locale name."""


def detect() -> Dict[str, str]:
    """Detect a locale that is suitable for ensuring UTF-8 output."""

    def build(locname: str) -> Dict[str, str]:
        """Build the LC_ALL/LANGUAGE dictionary to return."""
        return {"LC_ALL": locname, "LANGUAGE": ""}

    cenv = dict(os.environ)
    cenv.update({"LC_ALL": "C", "LANGUAGE": ""})
    avail = set(
        subprocess.check_output(
            ["locale", "-a"], bufsize=0, encoding="ISO-8859-15", env=cenv
        ).splitlines()
    )

    for lang in _LANGS:
        for enc in _ENCODINGS:
            locname = f"{lang}.{enc}"
            if locname in avail:
                return build(locname)

    # Fall back to one that POSIX says should be there, although it really isn't...
    return build("C.UTF-8")
