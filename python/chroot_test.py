#!/usr/bin/python3
"""Test the StorPool OpenStack integration in a chroot environment."""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import os
import pathlib
import subprocess
import sys

from typing import TYPE_CHECKING

import cfg_diag
import utf8_locale


if TYPE_CHECKING:
    from typing import Iterator, List, Union

    PathList = List[Union[str, os.PathLike[str]]]  # pylint: disable=unsubscriptable-object


SUPPORTED_RELEASES = ("victoria", "wallaby", "xena", "yoga")
DEFAULT_RELEASES = SUPPORTED_RELEASES


@dataclasses.dataclass(frozen=True)
class Config(cfg_diag.Config):
    """Runtime configuration for the chroot tester."""

    chroot: str
    installed: str | None
    releases: list[str]
    utf8_env: dict[str, str]


@dataclasses.dataclass(frozen=True)
class Chroot:
    """A representation of a chroot environment for running commands in."""

    sid: str
    mountpoint: pathlib.Path
    utf8_env: dict[str, str]

    def _get_command(self, command: PathList, cwd: pathlib.Path) -> PathList:
        """Augment a command to run in the schroot session."""
        base: PathList = [
            "schroot",
            "-r",
            "-c",
            self.sid,
            "-u",
            "root",
            "-d",
            str(cwd),
            "--",
            "env",
            "LC_ALL=C.UTF-8",
            "LANGUAGE=",
        ]
        return base + command

    def check_output(self, command: PathList, *, cwd: pathlib.Path = pathlib.Path("/")) -> str:
        """Run a command in the chroot session, return its output."""
        return subprocess.check_output(
            self._get_command(command, cwd), encoding="UTF-8", env=self.utf8_env
        )

    def run(
        self,
        command: PathList,
        *,
        check: bool = True,
        cwd: pathlib.Path = pathlib.Path("/"),
    ) -> subprocess.CompletedProcess[str]:
        """Run a command in the chroot session; check=True by default!"""
        return subprocess.run(
            self._get_command(command, cwd),
            check=check,
            encoding="UTF-8",
            env=self.utf8_env,
        )


def parse_args() -> Config:
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(prog="chroot_test")
    parser.add_argument(
        "-c",
        "--chroot",
        type=str,
        required=True,
        help="the name of the chroot environment to instantiate",
    )
    parser.add_argument(
        "-I",
        "--installed",
        action="store_true",
        help="is the first listed OpenStack release installed",
    )
    parser.add_argument(
        "-r",
        "--releases",
        type=str,
        default=",".join(DEFAULT_RELEASES),
        help="the comma-separated list of OpenStack release names to test",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="verbose operation; display diagnostic output"
    )

    args = parser.parse_args()

    rels = args.releases.split(",")
    bad_rels = [name for name in rels if name not in SUPPORTED_RELEASES]
    if bad_rels:
        sys.exit(f"Unrecognized release names: {' '.join(bad_rels)}")

    return Config(
        chroot=args.chroot,
        installed=rels[0] if args.installed else None,
        releases=rels,
        utf8_env=utf8_locale.get_utf8_env(),
        verbose=args.verbose,
    )


def start_chroot(cfg: Config) -> str:
    """Start a chroot session."""
    print(f"Starting a {cfg.chroot} chroot session")
    try:
        lines = subprocess.check_output(
            ["schroot", "-b", "-c", cfg.chroot], encoding="UTF-8", env=cfg.utf8_env
        ).splitlines()
    except (OSError, subprocess.CalledProcessError) as err:
        sys.exit(f"Could not start a {cfg.chroot!r} chroot session: {err}")

    if len(lines) != 1:
        # Try to stop a chroot pointed to by the first line anyway
        if lines:
            try:
                subprocess.run(["schroot", "-e", "-c", lines[0]], check=True, env=cfg.utf8_env)
            except (OSError, subprocess.CalledProcessError) as err:
                print(
                    f"Could not stop the (maybe invalid) {lines[0]!r} chroot: {err}",
                    file=sys.stderr,
                )
        sys.exit(f"Unexpected `schroot -b -c {cfg.chroot!r}` output: {lines!r}")

    return lines[0]


def get_chroot_config(cfg: Config, sid: str) -> Chroot:
    """Examine a chroot session."""

    def get_mount_point() -> pathlib.Path:
        """Figure out where the chroot environment is mounted."""
        sess_file = pathlib.Path("/var/lib/schroot/session") / sid
        if sess_file.is_file():
            lines = sess_file.read_text(encoding="UTF-8").splitlines()
            mountpoints = [
                parts[2]
                for parts in (line.partition("mount-location=") for line in lines)
                if parts[1] and parts[2] and not parts[0]
            ]
            if len(mountpoints) != 1:
                sys.exit(
                    f"Unexpected number of mount-location lines in {sess_file}: {mountpoints!r}"
                )
            mountpoint = pathlib.Path(mountpoints[0])
            if not mountpoint.is_absolute() or not mountpoint.is_dir():
                sys.exit(f"Weird mount-location in {sess_file}: {mountpoints[0]!r}")
            return mountpoint

        for base in (pathlib.Path("/run/schroot/mount"), pathlib.Path("/var/run/schroot/mount")):
            mountpoint = base / sid
            if mountpoint.is_dir():
                return mountpoint

        sys.exit(f"Could not determine the mount point for the {sid!r} chroot session")

    print(f"Examining the {sid} chroot session")
    return Chroot(sid=sid, mountpoint=get_mount_point(), utf8_env=cfg.utf8_env)


def stop_chroot(cfg: Config, sid: str) -> None:
    """End the chroot session."""
    print(f"Stopping the {sid} chroot session")
    try:
        subprocess.run(["schroot", "-e", "-c", sid], check=True, env=cfg.utf8_env)
    except (OSError, subprocess.CalledProcessError) as err:
        print(f"Could not stop the chroot: {err}", file=sys.stderr)


@contextlib.contextmanager
def run_chroot(cfg: Config) -> Iterator[Chroot]:
    """Run a chroot session as a context manager."""
    chroot_sid = None
    try:
        chroot_sid = start_chroot(cfg)
        chroot = get_chroot_config(cfg, chroot_sid)
        yield chroot
    finally:
        if chroot_sid is not None:
            stop_chroot(cfg, chroot_sid)


def prepare_chroot(cfg: Config, chroot: Chroot) -> pathlib.Path:
    """Copy the source files into the chroot."""
    print("Installing OS packages into the chroot")
    chroot.run(
        [
            "env",
            "DEBIAN_FRONTEND=noninteractive",
            "apt-get",
            "-y",
            "install",
            "python3",
            "software-properties-common",
        ]
    )

    destdir = pathlib.Path("/opt/osi")
    uid = os.getuid()
    gid = os.getuid()
    print(f"Creating the {destdir} directory in the chroot as {uid}:{gid}")
    chroot.run(["install", "-d", "-o", str(uid), "-g", str(gid), "-m", "755", "--", destdir])

    print("Copying the source files over")
    files = [
        line
        for line in subprocess.check_output(
            ["git", "ls-files", "-z"], encoding="UTF-8", env=cfg.utf8_env
        ).split("\0")
        if line
    ]

    print(f"Got {len(files)} files")
    with subprocess.Popen(
        ["tar", "-cf", "-", "--"] + files, stdout=subprocess.PIPE, env=cfg.utf8_env
    ) as tar_out:
        with subprocess.Popen(
            [
                "tar",
                "-xf",
                "-",
                "-C",
                str(chroot.mountpoint / (destdir.relative_to(pathlib.Path("/")))),
            ],
            stdin=tar_out.stdout,
            env=cfg.utf8_env,
        ) as tar_in:
            if tar_out.wait() != 0:
                sys.exit("Could not pack up the source directory")
            if tar_in.wait() != 0:
                sys.exit("Could not extract the files to the chroot directory")

    topfiles = sorted(set(pathlib.Path(line).parts[0] for line in files))
    print("Let us see what we have there")
    lines = sorted(chroot.check_output(["ls", "-A", "/opt/osi"]).splitlines())
    print(repr(lines))
    if lines != topfiles:
        sys.exit(f"Expected {topfiles!r}, got {lines!r}")

    print("And let us see how it looks from inside the directory")
    lines = sorted(chroot.check_output(["ls", "-A"], cwd=destdir).splitlines())
    print(repr(lines))
    if lines != topfiles:
        sys.exit(f"Expected {topfiles!r}, got {lines!r}")

    return destdir


def check_detect_nothing(_cfg: Config, chroot: Chroot, osipath: pathlib.Path) -> None:
    """Run the check within the thing and stuff."""
    print("Expecting 'no components installed'")
    res = chroot.run(["./sp-openstack", "-av", "detect"], check=False, cwd=osipath)
    if res.returncode != 1:
        sys.exit(f"Unexpected 'did not find anything' process result: {res!r}")


def install_openstack(chroot: Chroot, release: str) -> None:
    """Install components from the specified OpenStack release."""
    print(f"Adding the OpenStack {release} Ubuntu cloud archive repository")
    chroot.run(
        [
            "env",
            "DEBIAN_FRONTEND=noninteractive",
            "add-apt-repository",
            "-y",
            f"cloud-archive:{release}",
        ]
    )

    print("Installing the Cinder, Nova, and Glance libraries")
    chroot.run(
        [
            "env",
            "DEBIAN_FRONTEND=noninteractive",
            "apt-get",
            "-y",
            "install",
            "python3-cinder",
            "python3-nova",
            "python3-glance",
        ]
    )


def check_diverted(chroot: Chroot, expected: bool) -> None:
    """Make sure dpkg-divert reports the correct files (possibly none)."""
    print("Checking for diverted Python library files")
    lines = chroot.check_output(
        ["dpkg-divert", "--list", "/usr/lib/python3/dist-packages/*"]
    ).splitlines()
    print("\n".join(lines))
    if expected and not lines:
        sys.exit("Expected some diverted Python files, found none")
    if not expected and lines:
        sys.exit(f"Did not expect any diverted Python files, found {lines!r}")


def check_detect(chroot: Chroot, osipath: pathlib.Path, release: str, outdated: bool) -> None:
    """Make sure that sp_osi detects the correct release."""
    print(
        # pylint: disable-next=consider-using-f-string
        "Expecting '{msg} OpenStack {release}'".format(
            msg="out of date" if outdated else "ok", release=release
        )
    )
    lines = chroot.check_output(["./sp-openstack", "-av", "detect"], cwd=osipath).splitlines()
    print("Got some output:")
    print("\n".join(lines))

    if not lines[0].startswith("Found "):
        sys.exit(f"Unexpected first line: {lines!r}")
    lines.pop(0)

    expected = [
        ["cinder", release]
        + (["out", "of", "date!"] if outdated else ["ok"])
        + ["/usr/lib/python3/dist-packages"],
        ["glance", release, "ok", "/usr/lib/python3/dist-packages"],
        ["nova", release, "ok", "/usr/lib/python3/dist-packages"],
    ]

    bad = False
    found = set()
    for line in lines:
        fields = line.split()
        if fields not in expected:
            print(f"Unexpected output line: {line!r}", file=sys.stderr)
            bad = True
            continue

        found.add(fields[0])

    if bad:
        sys.exit("Unexpected 'detect' output")
    if sorted(found) != ["cinder", "glance", "nova"]:
        sys.exit("Incomplete 'detect' output")


def install_sp_osi(chroot: Chroot, osipath: pathlib.Path, no_divert: bool = False) -> None:
    """Run `sp-openstack install` within the chroot."""
    print("Installing the updated OpenStack driver files")
    cmd: PathList = ["./sp-openstack", "-v"]
    if no_divert:
        cmd.append("-D")
    cmd.extend(["install", "cinder", "glance", "nova"])
    chroot.run(cmd, cwd=osipath)


def uninstall_sp_osi(chroot: Chroot, osipath: pathlib.Path, no_divert: bool = False) -> None:
    """Run `sp-openstack uninstall` within the chroot."""
    print("Restoring the original OpenStack driver files")
    cmd: PathList = ["./sp-openstack", "-v"]
    if no_divert:
        cmd.append("-D")
    cmd.extend(["uninstall", "cinder", "glance", "nova"])
    chroot.run(cmd, cwd=osipath)


def main() -> None:
    """Parse command-line arguments, run tests."""
    cfg = parse_args()

    with run_chroot(cfg) as chroot:
        cfg.diag(lambda: f"Got chroot mount point {chroot.mountpoint}")

        print("Checking whether we can run commands in the chroot session")
        chroot.run(["id"])
        lines = chroot.check_output(["find", "/opt"]).splitlines()
        if lines != ["/opt"]:
            sys.exit(f"Unexpected `find /opt` output: {lines!r}")

        check_diverted(chroot, False)
        osipath = prepare_chroot(cfg, chroot)

        check_diverted(chroot, False)
        if cfg.installed is not None:
            check_detect(chroot, osipath, cfg.installed, True)
        else:
            check_detect_nothing(cfg, chroot, osipath)

        for release in cfg.releases:
            if release != cfg.installed:
                check_diverted(chroot, False)
                install_openstack(chroot, release)

            check_diverted(chroot, False)
            check_detect(chroot, osipath, release, True)

            install_sp_osi(chroot, osipath)
            check_diverted(chroot, True)
            check_detect(chroot, osipath, release, False)

            uninstall_sp_osi(chroot, osipath)
            check_diverted(chroot, False)
            check_detect(chroot, osipath, release, True)

            install_sp_osi(chroot, osipath, no_divert=True)
            check_diverted(chroot, False)
            check_detect(chroot, osipath, release, False)

            uninstall_sp_osi(chroot, osipath, no_divert=True)
            check_diverted(chroot, False)
            check_detect(chroot, osipath, release, True)

        check_diverted(chroot, False)
        print("Everything seems to be in order!")


if __name__ == "__main__":
    main()
