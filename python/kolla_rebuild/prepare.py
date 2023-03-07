# SPDX-FileCopyrightText: 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Download files into the data directory."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

import jinja2
import requests

from kolla_rebuild import defs


if TYPE_CHECKING:
    import pathlib
    from typing import IO, Final


GITHUB_PROJECT: Final = "storpool-openstack-integration"
"""The name of the StorPool repository on GitHub."""

GITHUB_SLUG: Final = "release"
"""The GitHub release/tag slug."""

GITHUB_BASE: Final = (
    f"https://github.com/storpool/{GITHUB_PROJECT}/archive/refs/tags/{GITHUB_SLUG}/"
)
"""The base URL to download the GitHub release file from."""

REQ_TIMEOUT: Final = (30, 600)
"""The request timeout: 30 seconds to connect, 10 minutes to download the file."""

SP_BASENAME: Final = f"{GITHUB_PROJECT}-{GITHUB_SLUG}"
"""The base of the release tarball's filename."""

SP_EXT: Final = ".tar.gz"
"""The filename extension of the release tarball."""

LEGACY_RELEASES = ("yoga",)

NON_LEGACY_RELEASES = ("zed", "antelope", "master")

ALL_RELEASES = (*LEGACY_RELEASES, *NON_LEGACY_RELEASES)


def pack_osi_release(cfg: defs.Config, basename: str, tarball: pathlib.Path) -> None:
    """Create an archive containing the current Git HEAD files."""
    cmd: Final[list[pathlib.Path | str]] = [
        "git",
        "archive",
        "--format=tar",
        f"--prefix={basename}/",
        "-o",
        tarball,
        "--",
        "HEAD",
    ]
    cmdstr: Final = shlex.join(str(word) for word in cmd)
    try:
        subprocess.run(cmd, check=True, cwd=cfg.topdir)
    except (OSError, subprocess.CalledProcessError) as err:
        sys.exit(
            f"Could not create the {tarball} archive for the {cfg.topdir} Git HEAD: "
            f"`{cmdstr}` failed: {err}"
        )


def download_osi_release(cfg: defs.Config, tarball: pathlib.Path) -> None:
    """Download the sp-osi release tarball from GitHub."""

    def write_out_and_rename(tmpfile: IO[bytes]) -> bool:
        """Read the response data, write it out to the file, rename it when done."""
        cfg.diag_("Storing the HTTP response into a temporary file")
        while True:
            try:
                cbuf = resp.raw.read(32768)
            except (OSError, requests.HTTPError) as err:
                sys.exit(f"Could not download {url} to {tarball}: read error: {err}")
            if not cbuf:
                break
            try:
                tmpfile.write(cbuf)
            except OSError as err:
                sys.exit(f"Could not download {url} to {tarball}: write error: {err}")

        try:
            tmpfile.flush()
        except OSError as err:
            sys.exit(f"Could not download {url} to {tarball}: flush error: {err}")

        cfg.diag(lambda: f"Renaming the temporary file to {tarball}")
        try:
            os.rename(tmpfile.name, tarball)  # noqa: PTH104
        except OSError as err:
            sys.exit(f"Could not download {url} to {tarball}: rename error: {err}")

        return True

    url: Final = f"{GITHUB_BASE}{cfg.sp_osi_version}{SP_EXT}"
    cfg.diag(lambda: f"Sending a GET request for {url}")
    try:
        resp: Final = requests.get(url, stream=True, timeout=REQ_TIMEOUT)
    except (OSError, requests.HTTPError) as err:
        sys.exit(f"Could not send a request for {url}: {err}")
    cfg.diag(lambda: f"HTTP response: {resp.status_code} {resp.reason}")
    try:
        resp.raise_for_status()
    except requests.HTTPError as err:
        sys.exit(f"Could not download {url}: {err}")

    renamed = False
    with tempfile.NamedTemporaryFile(
        dir=tarball.parent, prefix=f"osi-{cfg.sp_osi_version}.", delete=False
    ) as tmpfile:
        try:
            renamed = write_out_and_rename(tmpfile)
        finally:
            if not renamed:
                try:
                    os.unlink(tmpfile)  # noqa: PTH108
                except OSError as err:
                    sys.exit(f"Could not remove the {tmpfile} temporary file: {err}")


def prepare_data_files(cfg: defs.Config, datadir: pathlib.Path) -> defs.DataFiles:
    """Check whether the data files are there."""
    basename: Final = f"{SP_BASENAME}-{cfg.sp_osi_version}"
    filename: Final = f"{basename}{SP_EXT}"
    tarball: Final = datadir / filename
    cfg.diag(lambda: f"Preparing {tarball}")

    if not datadir.is_dir():
        if datadir.exists() or datadir.is_symlink():
            sys.exit(f"Not a directory: {datadir}")
        cfg.diag(lambda: f"Creating the {datadir} directory")
        try:
            datadir.mkdir(mode=0o755)
        except OSError as err:
            sys.exit(f"Could not create the {datadir} directory: {err}")

    if cfg.sp_osi_version.endswith(defs.VERSION_WIP_SUFFIX):
        if tarball.is_symlink() or tarball.exists() and not tarball.is_dir():
            tarball.unlink()

        pack_osi_release(cfg, basename, tarball)
    elif not tarball.is_file():
        if tarball.exists() or tarball.is_symlink():
            sys.exit(f"Not a regular file: {tarball}")

        download_osi_release(cfg, tarball)
    else:
        cfg.diag(lambda: f"Found {tarball}")

    return defs.DataFiles(basename=basename, datadir=datadir, tarball=tarball)


def build_dockerfile(
    cfg: defs.Config, files: defs.DataFiles, kolla_component: str, kolla_service: str
) -> defs.BuildSource:
    """Render the Jinja template."""
    legacy_names: Final = cfg.release in LEGACY_RELEASES
    kolla_distro: Final = "ubuntu" if legacy_names else "ubuntu-jammy"
    kolla_container_name = (
        f"{kolla_distro}-binary-{kolla_component}-{kolla_service}:{cfg.release}"
        if legacy_names
        else f"{kolla_component}-{kolla_service}:{cfg.release}-{kolla_distro}"
    )

    jenv: Final = jinja2.Environment(
        autoescape=jinja2.select_autoescape(),
        loader=jinja2.FileSystemLoader(cfg.topdir / defs.DOCKER_DIR),
        undefined=jinja2.StrictUndefined,
    )
    jvars: Final = {
        "container_name": kolla_container_name,
        "component": kolla_component,
        "registry": defs.KOLLA_REGISTRY,
        "release": cfg.release,
        "sp_osi_name": files.basename,
        "sp_osi_filename": files.tarball.name,
        "sp_osi_version": cfg.sp_osi_version,
    }
    return defs.BuildSource(
        registry=defs.KOLLA_REGISTRY,
        container_name=kolla_container_name,
        dockerfile=jenv.get_template("Dockerfile.j2").render(**jvars) + "\n",
    )
