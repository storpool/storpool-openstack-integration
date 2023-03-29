"""Test the routines for parsing the component definitions."""

import functools
import json
import pathlib
from unittest import mock

from typing import Any, NamedTuple

import pytest

from sp_variant import variant as spvariant

from sp_osi import defs
from sp_osi import parse


class BadParseCase(NamedTuple):
    """A test case for a bad components file."""

    data: Any
    """The structure within the components.json file."""

    error: str
    """A substring of the expected error message."""


_BAD_CASES = [
    BadParseCase(data=None, error="no path at all"),
    BadParseCase(data=5, error="'int' object"),
    BadParseCase(data={}, error="'format'"),
    BadParseCase(
        data={"format": {"version": {"major": 42, "minor": 0}}}, error="Unsupported format version"
    ),
    BadParseCase(
        data={"format": {"version": {"major": 0, "minor": 1}}, "components": 7},
        error="'int' object",
    ),
    BadParseCase(
        data={
            "format": {"version": {"major": 0, "minor": 1}},
            "components": {"cinder": {"hello": "goodbye"}},
        },
        error="'detect_files_order'",
    ),
    BadParseCase(
        data={
            "format": {"version": {"major": 0, "minor": 1}},
            "components": {"cinder": {"detect_files_order": ["meow"]}},
        },
        error="'branches'",
    ),
    BadParseCase(
        data={
            "format": {"version": {"major": 0, "minor": 1}},
            "components": {
                "cinder": {"detect_files_order": ["meow"], "branches": {"alpha": {"1.0": {}}}}
            },
        },
        error="'comment'",
    ),
]
"""A set of test cases that should make `read_components()` fail."""

_GOOD_CASE = {
    "format": {
        "version": {
            "major": 0,
            "minor": 42,
        },
    },
    "something": ["and", "something", "else"],
    "components": {
        "steering": {
            "detect_files_order": ["parts/wheel.py"],
            "branches": {
                "alpha": {
                    "1.616": {
                        "comment": "To the left, to the right...",
                        "files": {
                            "parts/wheel.py": {
                                "sha256": "checksum goes here",
                            },
                        },
                        "outdated": False,
                        "weird field": "weird value",
                    },
                    "1.42": {
                        "comment": "Step it up, step it up...",
                        "files": {
                            "parts/wheel.py": {
                                "sha256": "a different checksum goes here",
                            },
                        },
                        "outdated": True,
                        "cloud": 9,
                    },
                }
            },
        }
    },
}
"""A test case that should be parsed successfully."""


@functools.lru_cache()
def _empty_config() -> defs.Config:
    """Return a mostly-empty set of sp_osi configuration settings."""
    return defs.Config(
        all_components=defs.ComponentsTop(components={}),
        components=[],
        no_divert=False,
        noop=False,
        utf8_env={},
        variant=spvariant.detect_variant(),
        verbose=False,
    )


@pytest.mark.parametrize("tcase", _BAD_CASES)
def test_parse_bad(tcase: BadParseCase) -> None:
    """Fail with the expected message."""

    def mock_read_text(path: pathlib.Path, *, encoding: str) -> str:
        """Mock reading the file, return the test data."""
        assert path == pathlib.Path("defs/components.json")
        assert encoding == "UTF-8"

        if tcase.data is None:
            raise FileNotFoundError("No path, no path at all")

        return json.dumps(tcase.data, indent=2)

    cfg = _empty_config()
    with mock.patch("pathlib.Path.read_text", new=mock_read_text), pytest.raises(
        parse.OSIParseError
    ) as err:
        parse.read_components(cfg)

    assert tcase.error in str(err.value)


def test_parse_good() -> None:
    """Parse some components, ignore fields that we do not know about."""

    def mock_read_text(path: pathlib.Path, *, encoding: str) -> str:
        """Mock reading the file, return the test data."""
        assert path == pathlib.Path("defs/components.json")
        assert encoding == "UTF-8"

        return json.dumps(_GOOD_CASE, indent=2)

    cfg = _empty_config()
    with mock.patch("pathlib.Path.read_text", new=mock_read_text):
        res = parse.read_components(cfg)

    assert sorted(res.components["steering"].branches["alpha"].keys()) == ["1.42", "1.616"]
