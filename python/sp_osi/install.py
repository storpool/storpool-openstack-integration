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
        super().__init__(
            "Could not install {src} to {dst}: {err}".format(src=src, dst=dst, err=err)
        )
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
        raise defs.OSIError(
            "Files consistency error: went from {det!r} to {wanted!r}".format(
                det=det, wanted=wanted
            )
        )

    found = [
        ver
        for ver in cfg.all_components.components[name].branches[det.branch].items()
        if {fname: fdata.sha256 for fname, fdata in ver[1].files.items()} == wanted
    ]
    if len(found) != 1 or found[0][1].outdated:
        raise defs.OSIError(
            (
                "Files consistency error: went from {det!r} to {wanted!r} and "
                "then found {found!r}"
            ).format(det=det, wanted=wanted, found=found)
        )

    return found[0]


def install(cfg: defs.Config, name: str, det: detect.DetectedComponent) -> bool:
    """Install (or not) a component's files, return True if anything changed."""
    version = det.data
    if not version.outdated:
        print("Nothing to do for {name} at {path}".format(name=name, path=det.path))
        return False

    wanted_ver, wanted = find_wanted_version(cfg, name, det)
    print(
        "About to replace {name} {current_ver} with {name} {wanted_ver}".format(
            name=name, current_ver=det.version, wanted_ver=wanted_ver
        )
    )
    for fname, fdata in sorted(wanted.files.items()):
        src = util.get_driver_path(name, det.branch, fname.name)
        if src is None:
            continue

        dst = det.path / name / fname
        print("- {src} -> {dst}".format(src=src, dst=dst))

        cksum = util.file_sha256sum(src)
        if cksum != fdata.sha256:
            raise OSIInstallError(
                src,
                dst,
                "Checksum mismatch for the {src} file: expected {expected!r}, got {cksum!r}".format(
                    src=src, expected=fdata.sha256, cksum=cksum
                ),
            )

        target = divert.ensure_diverted(cfg, dst)
        try:
            dstat = dst.stat() if cfg.noop else target.stat()
            dst_data = (dstat.st_uid, dstat.st_gid, dstat.st_mode & 0o7777)
        except FileNotFoundError:
            dst_data = (0, 0, 0o644)
        except OSError as err:
            raise OSIInstallError(
                src,
                dst,
                "Could not examine the destination file {dst}: {err}".format(dst=dst, err=err),
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
                        "{mode:03o}".format(mode=dst_data[2]),
                        "--",
                        src,
                        dst,
                    ],
                    env=cfg.utf8_env,
                )
            except (OSError, subprocess.CalledProcessError) as err:
                raise OSIInstallError(
                    src, dst, "Could not run install(8): {err}".format(err=err)
                ) from err

            cksum = util.file_sha256sum(dst)
            if cksum != fdata.sha256:
                raise OSIInstallError(
                    src,
                    dst,
                    (
                        "Checksum mismatch for the {dst} file after the installation: "
                        "expected {expected!r}, got {cksum!r}"
                    ).format(dst=dst, expected=fdata.sha256, cksum=cksum),
                )
        else:
            print(
                "- install -o {uid} -g {gid} -m {mode:03o} -- {src} {dst}".format(
                    uid=dst_data[0], gid=dst_data[1], mode=dst_data[2], src=src, dst=dst
                )
            )

    return True


def uninstall(cfg: defs.Config, name: str, det: detect.DetectedComponent) -> bool:
    """Restore (or not) a component's files, return True if anything changed."""
    version = det.data
    print(
        "About to restore {name} files currently updated to {current_ver}".format(
            name=name, current_ver=det.version
        )
    )
    for fname, fdata in sorted(version.files.items()):
        src = det.path / name / fname
        dst = divert.get_diverted_name(src)
        if not dst.is_file():
            continue
        print("- {dst} -> {src}".format(src=src, dst=dst))

        cksum = util.file_sha256sum(src)
        if cksum != fdata.sha256:
            raise OSIInstallError(
                src,
                dst,
                "Checksum mismatch for the {src} file: expected {expected!r}, got {cksum!r}".format(
                    src=src, expected=fdata.sha256, cksum=cksum
                ),
            )

        if not cfg.noop:
            try:
                src.unlink()
            except OSError as err:
                raise OSIInstallError(
                    src,
                    dst,
                    "Could not remove the patched file {src}: {err}".format(src=src, err=err),
                ) from err
        else:
            print("Would remove the patched file {src}".format(src=src))

        divert.ensure_undiverted(cfg, src)

    return True
