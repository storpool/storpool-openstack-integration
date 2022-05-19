"""Parse and validate the components definition file."""

import json
import pathlib
import re

from typing import Any, Dict, List  # noqa: H301

from . import defs
from . import util


RE_COMP_NAME = re.compile(r" ^ [a-z_]+ $ ", re.X)

RE_BRANCH_NAME = re.compile(r" ^ [a-z]+ $ ", re.X)

RE_VERSION_STRING = re.compile(
    r""" ^
    (?: 0 | [1-9][0-9]* )
    (?:
        \.
        (?: 0 | [1-9][0-9]* )
    ){5}
    $ """,
    re.X,
)


class OSIParseError(defs.OSIError):
    """An error that occurred while parsing a file."""

    def __init__(self, path: pathlib.Path, msg: str) -> None:
        """Record the file path and the error message."""
        super().__init__(f"Could not parse the components file {path}: {msg}")
        self.osi_path = path
        self.osi_msg = msg


def read_components(cfg: defs.Config) -> defs.ComponentsTop:
    """Read the component definitions."""

    def parse_comp_version(vdef: Dict[str, Any]) -> defs.ComponentVersion:
        """Parse a single component version definition."""
        return defs.ComponentVersion(
            comment=vdef["comment"],
            files={
                pathlib.Path(path): defs.ComponentFile(sha256=str(fdata["sha256"]))
                for path, fdata in vdef["files"].items()
            },
            outdated=bool(vdef["outdated"]),
        )

    def parse_component(cdef: Dict[str, Any]) -> defs.Component:
        """Parse a single component definition."""
        return defs.Component(
            detect_files_order=[pathlib.Path(path) for path in cdef["detect_files_order"]],
            branches={
                name: {version: parse_comp_version(vdata) for version, vdata in value.items()}
                for name, value in cdef["branches"].items()
            },
        )

    cpath = pathlib.Path("defs/components.json")
    cfg.diag(f"Trying to parse {cpath}")
    try:
        cdata = json.loads(cpath.read_text(encoding="UTF-8"))
    except OSError as err:
        raise OSIParseError(cpath, f"Could not read the file contents: {err}") from err
    except UnicodeDecodeError as err:
        raise OSIParseError(
            cpath, f"Could not parse the file contents as valid UTF-8: {err}"
        ) from err
    except ValueError as err:
        raise OSIParseError(
            cpath, f"Could not parse the file contents as valid JSON: {err}"
        ) from err

    try:
        vmajor, vminor = (
            cdata["format"]["version"]["major"],
            cdata["format"]["version"]["minor"],
        )
        cfg.diag(f"Got config format {vmajor}.{vminor}")
        if vmajor != 0:
            raise OSIParseError(cpath, f"Unsupported format version {vmajor}")
        return defs.ComponentsTop(
            components={name: parse_component(value) for name, value in cdata["components"].items()}
        )
    except TypeError as err:
        raise OSIParseError(cpath, f"Could not parse the components data: {err}") from err


def validate(cfg: defs.Config) -> List[str]:
    """Validate the components data, return a list of errors."""
    res = []  # type: List[str]

    def check_branch(
        comp_name: str, branch_name: str, branch: Dict[str, defs.ComponentVersion]
    ) -> None:
        """Validate versions within a single branch."""
        uptodate_files = {}  # type: Dict[pathlib.Path, str]

        if not RE_BRANCH_NAME.match(branch_name):
            res.append(f"{comp_name}: Invalid branch name: {branch_name}")

        for ver, version in sorted(branch.items()):
            if not RE_VERSION_STRING.match(ver):
                res.append(f"{comp_name}/{branch_name}: Invalid version string: " "{ver}")

            if not version.outdated:
                found = {
                    path: fdata.sha256
                    for path, fdata in (
                        (
                            util.get_driver_path(comp_name, branch_name, relpath.name),
                            fdata,
                        )
                        for relpath, fdata in sorted(version.files.items())
                    )
                    if path is not None
                }
                bad_cksum = {
                    path: cksum
                    for path, cksum in found.items()
                    if util.file_sha256sum(path) != cksum
                }
                if bad_cksum:
                    bad_files = " ".join(sorted(str(path) for path in bad_cksum.keys()))
                    res.append(f"{comp_name}/{branch_name}/{ver}: Bad checksum for {bad_files}")

                if not uptodate_files:
                    uptodate_files = found
                elif uptodate_files != found:
                    res.append(
                        (
                            f"{comp_name}/{branch_name}: All the up-to-date versions should "
                            f"define the same set of files with the same checksums"
                        )
                    )

            if not any(not version.outdated for version in branch.values()):
                res.append(f"{comp_name}/{branch_name}: No non-outdated versions")

    def check_component(comp_name: str, comp: defs.Component) -> None:
        """Validate the definition of a single component."""
        if not RE_COMP_NAME.match(comp_name):
            res.append(f"Invalid component name: {comp_name}")

        for branch_name, branch in sorted(comp.branches.items()):
            check_branch(comp_name, branch_name, branch)

    for comp_name, comp in sorted(cfg.all_components.components.items()):
        check_component(comp_name, comp)

    return res
