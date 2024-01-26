# SPDX-FileCopyrightText: 2023, 2024  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Update Kolla containers as needed to support the StorPool backend."""

from __future__ import annotations

import dataclasses
import datetime
import pathlib
import shlex
import subprocess
import sys
import tempfile
from typing import TYPE_CHECKING

import click

from kolla_rebuild import defs
from kolla_rebuild import find
from kolla_rebuild import prepare


if TYPE_CHECKING:
    from typing import Final


ALL_CONTAINERS: Final = [
    defs.Container(name="cinder-volume", extra_components=[]),
    defs.Container(name="nova-compute", extra_components=["os_brick"]),
    defs.Container(name="glance-api", extra_components=["os_brick"]),
]

"""The known containers that we want to rebuild."""

DEFAULT_RELEASE: Final = "master"
"""The default OpenStack release (or "master") to rebuild the containers for."""

DEFAULT_CONTAINERS: Final = [cont.name for cont in ALL_CONTAINERS]
"""The components to build containers for by default."""


@dataclasses.dataclass(frozen=True)
class Config(defs.Config):
    """Runtime configuration for the kolla-rebuild command-line tool."""

    tag_suffix: str
    """The suffix to append to the Docker image tag."""


def _build_tag_suffix() -> str:
    """Use the current date, add ".0", to build a suffix for the Docker tag."""
    now = datetime.datetime.now(tz=datetime.timezone.utc).astimezone()
    return now.strftime(".%Y%m%d.0")


def build_config(
    *,
    quiet: bool,
    release: str,
    sp_osi: str | None,
    tag_suffix: str | None,
    topdir: pathlib.Path | None,
) -> Config:
    """Prepare the runtime configuration object."""

    def osi_version() -> str:
        """Determine the sp-osi version to use; parse "wip" in a special way."""
        if sp_osi is None:
            return find.find_sp_osi_version(topdir=topdir)

        if sp_osi == "wip":
            return find.find_sp_osi_version(topdir=topdir) + defs.VERSION_WIP_SUFFIX

        return sp_osi

    return Config(
        topdir=find.find_topdir(topdir=topdir),
        release=release,
        sp_osi_version=osi_version(),
        tag_suffix=tag_suffix if tag_suffix is not None else _build_tag_suffix(),
        verbose=not quiet,
    )


def get_containers(container_names: list[str]) -> list[defs.Container]:
    """Find the containers corresponding to the provided names."""
    containers: list[defs.Container] = []
    for container_name in container_names:
        container = None
        for cont in ALL_CONTAINERS:
            if container_name == cont.name:
                container = cont
        if container is None:
            sys.exit(
                f"Unrecognized container: {container_name}, "
                f"must be one or more of {' '.join([c.name for c in ALL_CONTAINERS])}"
            )
        containers.append(container)

    return containers


@click.command(
    name="kolla-rebuild", help="rebuild Kolla containers for the StorPool Cinder backend"
)
@click.option(
    "-c",
    "--container",
    type=str,
    multiple=True,
    default=DEFAULT_CONTAINERS,
    help="the OpenStack component containers to rebuild",
)
@click.option(
    "-d",
    "--topdir",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, resolve_path=True, path_type=pathlib.Path
    ),
    help="the path to the storpool-openstack-integration repository",
)
@click.option("--no-cache", is_flag=True, help="flush the Docker build cache")
@click.option("--pull", is_flag=True, help="update the upstream container image before rebuilding")
@click.option("-q", "--quiet", is_flag=True, help="quiet operation; no diagnostic output")
@click.option(
    "-r",
    "--release",
    type=str,
    default=DEFAULT_RELEASE,
    help="the OpenStack release to rebuild the containers for",
)
@click.option(
    "-s",
    "--sp-osi",
    type=str,
    help="the storpool-openstack-integration version to use instead of the last released one",
)
@click.option(
    "-T",
    "--tag-suffix",
    type=str,
    help="the suffix to add to the built image tag (default: .currentdate.0)",
)
def main(
    *,
    container: list[str],
    no_cache: bool,
    pull: bool,
    quiet: bool,
    release: str,
    sp_osi: str | None,
    tag_suffix: str | None,
    topdir: pathlib.Path | None,
) -> None:
    """Parse command-line options, gather files, invoke docker-build."""

    def build_component(container: defs.Container) -> None:
        """Rebuild the container for a single component."""
        parts: Final = container.name.split("-", maxsplit=1)
        if len(parts) != 2:  # noqa: PLR2004  # this will go away with match/case
            sys.exit(f"Internal error: build_component() invoked with {container=!r}")
        kolla_component, kolla_service = parts
        build: Final = prepare.build_dockerfile(
            cfg, files, kolla_component, kolla_service, container.extra_components
        )

        with tempfile.NamedTemporaryFile(
            mode="wt", encoding="UTF-8", prefix="Dockerfile."
        ) as dockerfile:
            dockerfile.write(build.dockerfile)
            dockerfile.flush()
            subprocess.check_call(["ls", "-l", "--", dockerfile.name])
            subprocess.check_call(["cat", "--", dockerfile.name])

            cmd: Final[list[str | pathlib.Path]] = [
                "docker",
                "build",
                "-t",
                f"storpool/{build.container_name}{cfg.tag_suffix}",
                "--rm",
                *(["--no-cache"] if no_cache else []),
                *(["--pull"] if pull else []),
                "-f",
                dockerfile.name,
                "--",
                datadir,
            ]
            cmd_str: Final = shlex.join(str(word) for word in cmd)
            cfg.diag(lambda: f"Running `{cmd_str}`")
            try:
                subprocess.run(cmd, check=True)
            except (OSError, subprocess.CalledProcessError) as err:
                sys.exit(f"Could not run `{cmd_str}`: {err}")

    if release not in prepare.ALL_RELEASES:
        sys.exit(
            f"Unsupported release {release!r}, must be one of {' '.join(prepare.ALL_RELEASES)}"
        )
    release = prepare.RELEASE_ALIASES.get(release, release)
    cfg: Final = build_config(
        quiet=quiet, release=release, sp_osi=sp_osi, tag_suffix=tag_suffix, topdir=topdir
    )
    containers = get_containers(container)
    datadir: Final = cfg.topdir / defs.DATA_DIR
    files: Final = prepare.prepare_data_files(cfg, datadir)

    for cont in containers:
        build_component(cont)


if __name__ == "__main__":
    main()  # pylint: disable=missing-kwoa
