# SPDX-FileCopyrightText: 2022, 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Replace files with updated StorPool versions as needed."""

import pathlib
import subprocess

from typing import Tuple

from . import defs
from . import detect
from . import divert
from . import util


class OSIInstallError(defs.OSIError):
    """An error that occurred during the installation of a file."""

    def __init__(self, src: pathlib.Path, dst: pathlib.Path, err: str) -> None:
        """Store the source and destination paths."""
        super().__init__(f"Could not install {src} to {dst}: {err}")
        self.osi_src = src
        self.osi_dst = dst


def find_wanted_version(
    cfg: defs.Config, name: str, det: detect.DetectedComponent
) -> Tuple[str, defs.ComponentVersion]:
    """Find a component version with the detected and replaced checksums."""
    print("Collecting information about the files to install")
    version = det.data
    wanted = {
        fname: (fdata.sha256 if src is None else util.file_sha256sum(src))
        for (fname, fdata, src) in (
            (fname, fdata, util.get_driver_path(name, det.branch, fname.name))
            for fname, fdata in version.files.items()
        )
    }
    if len(wanted) != len(version.files):
        raise defs.OSIError(f"Files consistency error: went from {det!r} to {wanted!r}")

    found = [
        ver
        for ver in cfg.all_components.components[name].branches[det.branch].items()
        if {fname: fdata.sha256 for fname, fdata in ver[1].files.items()} == wanted
    ]
    if len(found) != 1 or found[0][1].outdated:
        raise defs.OSIError(
            f"Files consistency error: went from {det!r} to {wanted!r} and then found {found!r}"
        )

    return found[0]


def install(cfg: defs.Config, name: str, det: detect.DetectedComponent) -> bool:
    """Install (or not) a component's files, return True if anything changed."""
    version = det.data
    if not version.outdated:
        print(f"Nothing to do for {name} at {det.path}")
        return False

    wanted_ver, wanted = find_wanted_version(cfg, name, det)
    print(f"About to replace {name} {det.version} with {name} {wanted_ver}")
    for fname, fdata in sorted(wanted.files.items()):
        src = util.get_driver_path(name, det.branch, fname.name)
        if src is None:
            continue

        dst = det.path / name / fname
        print(f"- {src} -> {dst}")

        cksum = util.file_sha256sum(src)
        if cksum != fdata.sha256:
            raise OSIInstallError(
                src,
                dst,
                f"Checksum mismatch for the {src} file: expected {fdata.sha256!r}, got {cksum!r}",
            )

        target = divert.ensure_diverted(cfg, dst)
        try:
            dstat = dst.stat() if cfg.noop else target.stat()
            dst_data = (dstat.st_uid, dstat.st_gid, dstat.st_mode & 0o7777)
        except FileNotFoundError:
            dst_data = (0, 0, 0o644)
        except OSError as err:
            raise OSIInstallError(
                src, dst, f"Could not examine the destination file {dst}: {err}"
            ) from err

        if not cfg.noop:
            try:
                subprocess.check_call(
                    [
                        "install",
                        "-o",
                        str(dst_data[0]),
                        "-g",
                        str(dst_data[1]),
                        "-m",
                        f"{dst_data[2]:03o}",
                        "--",
                        src,
                        dst,
                    ],
                    env=cfg.utf8_env,
                )
            except (OSError, subprocess.CalledProcessError) as err:
                raise OSIInstallError(src, dst, f"Could not run install(8): {err}") from err

            cksum = util.file_sha256sum(dst)
            if cksum != fdata.sha256:
                raise OSIInstallError(
                    src,
                    dst,
                    (
                        f"Checksum mismatch for the {dst} file after the installation: "
                        f"expected {fdata.sha256!r}, got {cksum!r}"
                    ),
                )
        else:
            print(
                f"- install -o {dst_data[0]} -g {dst_data[1]} -m {dst_data[2]:03o} -- {src} {dst}"
            )

    return True


def uninstall(cfg: defs.Config, name: str, det: detect.DetectedComponent) -> bool:
    """Restore (or not) a component's files, return True if anything changed."""
    version = det.data
    print(f"About to restore {name} files currently updated to {det.version}")
    for fname, fdata in sorted(version.files.items()):
        src = det.path / name / fname
        dst = divert.get_diverted_name(src)
        if not dst.is_file():
            continue
        print(f"- {dst} -> {src}")

        cksum = util.file_sha256sum(src)
        if cksum != fdata.sha256:
            raise OSIInstallError(
                src,
                dst,
                f"Checksum mismatch for the {src} file: expected {fdata.sha256!r}, got {cksum!r}",
            )

        if not cfg.noop:
            try:
                src.unlink()
            except OSError as err:
                raise OSIInstallError(
                    src, dst, f"Could not remove the patched file {src}: {err}"
                ) from err
        else:
            print(f"Would remove the patched file {src}")

        divert.ensure_undiverted(cfg, src)

    return True
