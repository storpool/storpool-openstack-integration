# SPDX-FileCopyrightText: 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: Apache-2.0
"""Common definitions for the kolla-rebuild tool."""

from __future__ import annotations

import dataclasses
import pathlib
from typing import TYPE_CHECKING

import cfg_diag


if TYPE_CHECKING:
    from typing import Final


DOCKER_DIR: Final = pathlib.Path("kolla/docker")
"""The source subdirectory where our Docker definition files reside."""

DATA_DIR: Final = DOCKER_DIR / "data"
"""The directory where the Docker data files should be placed."""

KOLLA_REGISTRY: Final = "quay.io/openstack.kolla"
"""The Docker container registry to fetch the upstream Kolla containers from."""

VERSION_WIP_SUFFIX = ".wip"
"""The sp-osi version suffix that marks the "pack up the current source tree files" mode."""


@dataclasses.dataclass(frozen=True)
class Config(cfg_diag.Config):
    """Runtime configuration for the kolla-rebuild tool."""

    topdir: pathlib.Path
    """The sp-osi project's top-level source directory."""

    release: str
    """The OpenStack release to rebuild the containers for."""

    sp_osi_version: str
    """The sp-osi version to use within the container."""


@dataclasses.dataclass(frozen=True)
class DataFiles:
    """The files prepared in the Docker data directory."""

    basename: str
    """The full name of the sp-osi release."""

    datadir: pathlib.Path
    """The path to the data directory itself."""

    tarball: pathlib.Path
    """The full path to the sp-osi release tarball."""


@dataclasses.dataclass(frozen=True)
class BuildSource:
    """The information to be passed to `docker build`."""

    registry: str
    """The Docker container registry to fetch the upstream Kolla containers from."""

    container_name: str
    """The name of the container to fetch and rebuild."""

    dockerfile: str
    """The contents of the Dockerfile to rebuild with."""


@dataclasses.dataclass(frozen=True)
class Container:
    """A Kolla Container."""

    name: str
    """The name of the container, in a {component}-{service} format"""

    extra_components: list[str]
    """List of extra components inside the container"""
