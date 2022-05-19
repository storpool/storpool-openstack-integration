"""Detect the currently-installed OpenStack component versions."""

import itertools
import pathlib
import subprocess

from typing import Dict, List, NamedTuple  # noqa: H301

from . import defs
from . import util


class NotFoundError(defs.OSIError):
    """A component was not found at all."""

    def __init__(self, component: str) -> None:
        """Store the component name."""
        super().__init__(f"Could not find a known {component} version")
        self.component = component


DetectedComponent = NamedTuple(
    "DetectedComponent",
    [
        ("name", str),
        ("path", pathlib.Path),
        ("branch", str),
        ("version", str),
        ("data", defs.ComponentVersion),
    ],
)


DetectedComponents = NamedTuple(
    "DetectedComponents", [("res", Dict[str, DetectedComponent]), ("consistent", bool)]
)


def get_python_paths(cfg: defs.Config) -> List[pathlib.Path]:
    """Get all the search paths for the Python 3 and 2 interpreters."""

    def query_program(prog: str) -> List[pathlib.Path]:
        """Query a Python interpreter for its search paths."""
        cfg.diag(f"Querying {prog} for its library search paths")
        cmd = [
            prog,
            "-c",
            "import sys; print('\\n'.join(path for path in sys.path if path))",
        ]
        cfg.diag(f"- about to execute {cmd!r}")
        try:
            return [
                pathlib.Path(line)
                for line in subprocess.check_output(
                    cmd, encoding="UTF-8", env=cfg.utf8_env
                ).splitlines()
            ]
        except FileNotFoundError:
            cfg.diag(f"Apparently there is no {prog} on this system")
            return []
        except (IOError, subprocess.CalledProcessError) as err:
            raise defs.OSIEnvError(f"Could not execute {cmd!r}: {err}") from err

    return list(itertools.chain(*(query_program(prog) for prog in ("python3", "python2"))))


def detect(cfg: defs.Config) -> DetectedComponents:
    """Detect the currently-installed OpenStack component versions."""

    def check_version(
        name: str,
        files: List[pathlib.Path],
        ver: defs.ComponentVersion,
        path: pathlib.Path,
    ) -> bool:
        """Check whether this exact version is at that path."""
        for relp in files:
            rpath = path / name / relp
            if not rpath.is_file():
                return False

            if util.file_sha256sum(rpath) != ver.files[relp].sha256:
                return False

        return True

    comps = cfg.all_components
    req = cfg.components
    cfg.diag(
        (
            f"Looking for OpenStack components: {' '.join(sorted(req))} "
            f"out of {' '.join(sorted(comps.components))}"
        )
    )

    pypaths = get_python_paths(cfg)
    res = {}  # type: Dict[str, DetectedComponent]
    for name, comp in ((name, comps.components[name]) for name in req):
        versions = list(
            itertools.chain(
                *(
                    [(branch_name, version, ver) for version, ver in sorted(branch.items())]
                    for branch_name, branch in sorted(comp.branches.items())
                )
            )
        )
        cfg.diag(f"Looking for {name}, {len(versions)} known versions")

        for path in pypaths:
            cfg.diag(f"- checking {path}")
            try:
                res[name] = next(
                    DetectedComponent(name, path, branch, version, ver)
                    for branch, version, ver in versions
                    if check_version(name, comp.detect_files_order, ver, path)
                )
                break
            except StopIteration:
                continue
        if name not in res:
            raise NotFoundError(component=name)

    return DetectedComponents(
        res=res, consistent=len(set(comp.branch for comp in res.values())) == 1
    )
