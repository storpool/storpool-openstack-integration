# SPDX-FileCopyrightText: 2021 - 2024  StorPool <support@storpool.com>
# SPDX-License-Identifier: BSD-2-Clause
"""Build the hierarchical structure of variant definitions."""

from __future__ import annotations

import pathlib
import re
from typing import TYPE_CHECKING, NamedTuple

from . import defs


if TYPE_CHECKING:
    from typing import Any, Callable, Final, TypeVar

    _TNamedTuple = TypeVar("_TNamedTuple", bound=NamedTuple)


CMD_NOOP: Final[list[str]] = ["true"]

_VARIANT_DEF: Final[list[defs.Variant | defs.VariantUpdate]] = [
    defs.Variant(
        name="DEBIAN13",
        descr="Debian 13.x (trixie/unstable)",
        parent="",
        family="debian",
        detect=defs.Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"""^
                    PRETTY_NAME= .*
                    Debian \s+ GNU/Linux \s+
                    (?: trixie | 13 ) (?: \s | / )
                """,
                re.X,
            ),
            os_id="debian",
            os_version_regex=re.compile(r"^13$"),
        ),
        supported=defs.Supported(repo=False),
        commands=defs.Commands(
            package=defs.CommandsPackage(
                update_db=["apt-get", "-q", "-y", "update"],
                install=[
                    "env",
                    "DEBIAN_FRONTEND=noninteractive",
                    "apt-get",
                    "-q",
                    "-y",
                    "--no-install-recommends",
                    "install",
                    "--",
                ],
                list_all=[
                    "dpkg-query",
                    "-W",
                    "-f",
                    r"${Package}\t${Version}\t${Architecture}\t${db:Status-Abbrev}\n",
                    "--",
                ],
                purge=[
                    "env",
                    "DEBIAN_FRONTEND=noninteractive",
                    "apt-get",
                    "-q",
                    "-y",
                    "purge",
                    "--",
                ],
                remove=[
                    "env",
                    "DEBIAN_FRONTEND=noninteractive",
                    "apt-get",
                    "-q",
                    "-y",
                    "remove",
                    "--",
                ],
                remove_impl=[
                    "env",
                    "DEBIAN_FRONTEND=noninteractive",
                    "dpkg",
                    "-r",
                    "--",
                ],
            ),
            pkgfile=defs.CommandsPkgFile(
                dep_query=[
                    "sh",
                    "-c",
                    'dpkg-deb -f -- "$pkg" "Depends" | sed -e "s/ *, */,/g" | tr "," "\\n"',
                ],
                install=[
                    "sh",
                    "-c",
                    "env DEBIAN_FRONTEND=noninteractive apt-get install "
                    "--no-install-recommends --reinstall -y "
                    "-o DPkg::Options::=--force-confnew "
                    "-- $packages",
                ],
            ),
        ),
        min_sys_python="3.11",
        repo=defs.DebRepo(
            vendor="debian",
            codename="unstable",
            sources="debian/repo/storpool.sources",
            keyring="debian/repo/storpool-keyring.gpg",
            req_packages=["ca-certificates"],
        ),
        package={
            "BINDINGS_PYTHON": "python3",
            "BINDINGS_PYTHON_CONFGET": "python3-confget",
            "BINDINGS_PYTHON_SIMPLEJSON": "python3-simplejson",
            "CGROUP": "cgroup-tools",
            "CPUPOWER": "linux-cpupower",
            "LIBSSL": "libssl3",
            "MCELOG": "bash",
        },
        systemd_lib="lib/systemd/system",
        file_ext="deb",
        initramfs_flavor="update-initramfs",
        builder=defs.Builder(
            alias="debian13",
            base_image="debian:unstable",
            branch="debian/unstable",
            kernel_package="linux-headers",
            utf8_locale="C.UTF-8",
        ),
    ),
    defs.VariantUpdate(
        name="DEBIAN12",
        descr="Debian 12.x (bookworm)",
        parent="DEBIAN13",
        detect=defs.Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"""^
                    PRETTY_NAME= .*
                    Debian \s+ GNU/Linux \s+
                    (?: bookworm | 12 ) (?: \s | / )
                """,
                re.X,
            ),
            os_id="debian",
            os_version_regex=re.compile(r"^12$"),
        ),
        updates={
            "supported": {"repo": True},
            "repo": {"codename": "bookworm"},
            "builder": {
                "alias": "debian12",
                "base_image": "debian:bookworm",
                "branch": "debian/bookworm",
            },
        },
    ),
    defs.VariantUpdate(
        name="DEBIAN11",
        descr="Debian 11.x (bullseye)",
        parent="DEBIAN12",
        detect=defs.Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"""^
                    PRETTY_NAME= .*
                    Debian \s+ GNU/Linux \s+
                    (?: bullseye | 11 ) (?: \s | / )
                """,
                re.X,
            ),
            os_id="debian",
            os_version_regex=re.compile(r"^11$"),
        ),
        updates={
            "min_sys_python": "3.9",
            "repo": {"codename": "bullseye"},
            "package": {
                "LIBSSL": "libssl1.1",
            },
            "builder": {
                "alias": "debian11",
                "base_image": "debian:bullseye",
                "branch": "debian/bullseye",
            },
        },
    ),
    defs.VariantUpdate(
        name="DEBIAN10",
        descr="Debian 10.x (buster)",
        parent="DEBIAN11",
        detect=defs.Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"""^
                    PRETTY_NAME= .*
                    Debian \s+ GNU/Linux \s+
                    (?: buster | 10 ) (?: \s | / )
                """,
                re.X,
            ),
            os_id="debian",
            os_version_regex=re.compile(r"^10$"),
        ),
        updates={
            "supported": {"repo": False},
            "repo": {
                "codename": "buster",
            },
            "min_sys_python": "3.7",
            "package": {
                "BINDINGS_PYTHON": "python",
                "BINDINGS_PYTHON_CONFGET": "python-confget",
                "BINDINGS_PYTHON_SIMPLEJSON": "python-simplejson",
            },
            "builder": {
                "alias": "debian10",
                "base_image": "debian:buster",
                "branch": "debian/buster",
            },
        },
    ),
    defs.VariantUpdate(
        name="UBUNTU2404",
        descr="Ubuntu 24.04 LTS (Noble Numbat)",
        parent="DEBIAN13",
        detect=defs.Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"^ PRETTY_NAME= .* Ubuntu \s+ .* Noble ",
                re.X,
            ),
            os_id="ubuntu",
            os_version_regex=re.compile(r"^24\.04$"),
        ),
        updates={
            "supported": {"repo": False},
            "repo": {
                "vendor": "ubuntu",
                "codename": "noble",
            },
            "min_sys_python": "3.12",
            "package": {
                "CPUPOWER": "linux-tools-generic",
            },
            "builder": {
                "alias": "ubuntu-24.04",
                "base_image": "ubuntu:noble",
                "branch": "ubuntu/noble",
            },
        },
    ),
    defs.VariantUpdate(
        name="UBUNTU2204",
        descr="Ubuntu 22.04 LTS (Jammy Jellyfish)",
        parent="UBUNTU2404",
        detect=defs.Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"^ PRETTY_NAME= .* (?: Ubuntu \s+ 22 \. 04 | Mint \s+ 21 ) ",
                re.X,
            ),
            os_id="ubuntu",
            os_version_regex=re.compile(r"^22\.04$"),
        ),
        updates={
            "supported": {"repo": True},
            "min_sys_python": "3.10",
            "repo": {
                "vendor": "ubuntu",
                "codename": "jammy",
            },
            "builder": {
                "alias": "ubuntu-22.04",
                "base_image": "ubuntu:jammy",
                "branch": "ubuntu/jammy",
            },
        },
    ),
    defs.VariantUpdate(
        name="UBUNTU2004",
        descr="Ubuntu 20.04 LTS (Focal Fossa)",
        parent="UBUNTU2204",
        detect=defs.Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"^ PRETTY_NAME= .* (?: Ubuntu \s+ 20 \. 04 | Mint \s+ 20 ) ",
                re.X,
            ),
            os_id="ubuntu",
            os_version_regex=re.compile(r"^20\.04$"),
        ),
        updates={
            "supported": {"repo": True},
            "repo": {
                "vendor": "ubuntu",
                "codename": "focal",
            },
            "package": {
                "LIBSSL": "libssl1.1",
            },
            "min_sys_python": "3.8",
            "builder": {
                "alias": "ubuntu-20.04",
                "base_image": "ubuntu:focal",
                "branch": "ubuntu/focal",
            },
        },
    ),
    defs.VariantUpdate(
        name="UBUNTU1804",
        descr="Ubuntu 18.04 LTS (Bionic Beaver)",
        parent="UBUNTU2004",
        detect=defs.Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"^ PRETTY_NAME= .* Ubuntu \s+ 18 \. 04 ",
                re.X,
            ),
            os_id="ubuntu",
            os_version_regex=re.compile(r"^18\.04$"),
        ),
        updates={
            "repo": {
                "codename": "bionic",
            },
            "min_sys_python": "3.6",
            "package": {
                "BINDINGS_PYTHON": "python",
                "BINDINGS_PYTHON_CONFGET": "python-confget",
                "BINDINGS_PYTHON_SIMPLEJSON": "python-simplejson",
            },
            "builder": {
                "alias": "ubuntu-18.04",
                "base_image": "ubuntu:bionic",
                "branch": "ubuntu/bionic",
            },
        },
    ),
    defs.Variant(
        name="ALMA9",
        descr="AlmaLinux 9.x",
        parent="",
        family="redhat",
        detect=defs.Detect(
            filename="/etc/redhat-release",
            regex=re.compile(r"^ AlmaLinux \s .* \s 9 \. [0-9]", re.X),
            os_id="almalinux",
            os_version_regex=re.compile(r"^9(?:$|\.[0-9])"),
        ),
        supported=defs.Supported(repo=False),
        commands=defs.Commands(
            package=defs.CommandsPackage(
                update_db=CMD_NOOP,
                install=[
                    "dnf",
                    "--disablerepo=*",
                    "--enablerepo=appstream",
                    "--enablerepo=baseos",
                    "--enablerepo=crb",
                    "--enablerepo=storpool-contrib",
                    "install",
                    "-q",
                    "-y",
                    "--",
                ],
                list_all=[
                    "rpm",
                    "-qa",
                    "--qf",
                    r"%{Name}\t%{EVR}\t%{Arch}\tii\n",
                    "--",
                ],
                purge=[
                    "yum",
                    "remove",
                    "-q",
                    "-y",
                    "--",
                ],
                remove=[
                    "yum",
                    "remove",
                    "-q",
                    "-y",
                    "--",
                ],
                remove_impl=[
                    "rpm",
                    "-e",
                    "--",
                ],
            ),
            pkgfile=defs.CommandsPkgFile(
                dep_query=[
                    "sh",
                    "-c",
                    'rpm -qpR -- "$pkg"',
                ],
                install=[
                    "sh",
                    "-c",
                    """
unset to_install to_reinstall
for f in $packages; do
    package="$(rpm -qp "$f")"
    if rpm -q -- "$package"; then
        to_reinstall="$to_reinstall ./$f"
    else
        to_install="$to_install ./$f"
    fi
done

if [ -n "$to_install" ]; then
    dnf install -y --disablerepo='*' --enablerepo=appstream,baseos,crb,storpool-contrib --setopt=localpkg_gpgcheck=0 -- $to_install
fi
if [ -n "$to_reinstall" ]; then
    dnf reinstall -y --disablerepo='*' --enablerepo=appstream,baseos,crb,storpool-contrib --setopt=localpkg_gpgcheck=0 -- $to_reinstall
fi
""",  # noqa: E501
                ],
            ),
        ),
        min_sys_python="3.9",
        repo=defs.YumRepo(
            yumdef="redhat/repo/storpool-centos.repo",
            keyring="redhat/repo/RPM-GPG-KEY-StorPool",
        ),
        package={
            "KMOD": "kmod",
            "LIBCGROUP": "bash",
            "LIBUDEV": "systemd-libs",
            "OPENSSL": "openssl-libs",
            "PERL_AUTODIE": "perl-autodie",
            "PERL_FILE_PATH": "perl-File-Path",
            "PERL_LWP_PROTO_HTTPS": "perl-LWP-Protocol-https",
            "PERL_SYS_SYSLOG": "perl-Sys-Syslog",
            "PYTHON_SIMPLEJSON": "bash",
            "PROCPS": "procps-ng",
            "UDEV": "systemd",
        },
        systemd_lib="usr/lib/systemd/system",
        file_ext="rpm",
        initramfs_flavor="mkinitrd",
        builder=defs.Builder(
            alias="alma9",
            base_image="almalinux:9",
            branch="",
            kernel_package="kernel-core",
            utf8_locale="C.UTF-8",
        ),
    ),
    defs.VariantUpdate(
        name="ALMA8",
        descr="AlmaLinux 8.x",
        parent="ALMA9",
        detect=defs.Detect(
            filename="/etc/redhat-release",
            regex=re.compile(r"^ AlmaLinux \s .* \s 8 \. (?: [4-9] | [1-9][0-9] )", re.X),
            os_id="almalinux",
            os_version_regex=re.compile(r"^8(?:$|\.[4-9]|\.[1-9][0-9])"),
        ),
        updates={
            "supported": {"repo": True},
            "package": {
                "LIBCGROUP": "libcgroup-tools",
                "PYTHON_SIMPLEJSON": "python2-simplejson",
            },
            "min_sys_python": "3.6",
            "commands": {
                "package": {
                    "install": [
                        "dnf",
                        "--disablerepo=*",
                        "--enablerepo=appstream",
                        "--enablerepo=baseos",
                        "--enablerepo=powertools",
                        "--enablerepo=storpool-contrib",
                        "install",
                        "-q",
                        "-y",
                        "--",
                    ],
                },
                "pkgfile": {
                    "install": [
                        "sh",
                        "-c",
                        """
unset to_install to_reinstall
for f in $packages; do
    package="$(rpm -qp "$f")"
    if rpm -q -- "$package"; then
        to_reinstall="$to_reinstall ./$f"
    else
        to_install="$to_install ./$f"
    fi
done

if [ -n "$to_install" ]; then
    dnf install -y --disablerepo='*' --enablerepo=appstream,baseos,storpool-contrib,powertools --setopt=localpkg_gpgcheck=0 -- $to_install
fi
if [ -n "$to_reinstall" ]; then
    dnf reinstall -y --disablerepo='*' --enablerepo=appstream,baseos,storpool-contrib,powertools --setopt=localpkg_gpgcheck=0 -- $to_reinstall
fi
""",  # noqa: E501
                    ],
                },
            },
            "builder": {
                "alias": "alma8",
                "base_image": "almalinux:8",
                "branch": "",
            },
        },
    ),
    defs.VariantUpdate(
        name="CENTOS9",
        descr="CentOS Stream 9.x",
        parent="ALMA9",
        detect=defs.Detect(
            filename="/etc/redhat-release",
            regex=re.compile(r"^ CentOS Stream release 9", re.X),
            os_id="centos",
            os_version_regex=re.compile(r"^9(?:$|\.[4-9]|\.[1-9][0-9])"),
        ),
        updates={
            "builder": {
                "alias": "centos9",
                "base_image": "quay.io/centos/centos:stream9",
                "branch": "centos/9",
            },
        },
    ),
    defs.VariantUpdate(
        name="CENTOS8",
        descr="CentOS 8.x",
        parent="ALMA8",
        detect=defs.Detect(
            filename="/etc/redhat-release",
            regex=re.compile(r"^ CentOS \s .* \s 8 \. (?: [3-9] | (?: [12][0-9] ) )", re.X),
            os_id="centos",
            os_version_regex=re.compile(r"^8(?:$|\.[4-9]|\.[1-9][0-9])"),
        ),
        updates={
            "builder": {
                "alias": "centos8",
                "base_image": "centos:8",
                "branch": "centos/8",
            },
        },
    ),
    defs.VariantUpdate(
        name="CENTOS7",
        descr="CentOS 7.x",
        parent="CENTOS8",
        detect=defs.Detect(
            filename="/etc/redhat-release",
            regex=re.compile(r"^ (?: CentOS | Virtuozzo ) \s .* \s 7 \.", re.X),
            os_id="centos",
            os_version_regex=re.compile(r"^7(?:$|\.[0-9])"),
        ),
        updates={
            "commands": {
                "package": {
                    "install": [
                        "yum",
                        "--disablerepo=*",
                        "--enablerepo=base",
                        "--enablerepo=updates",
                        "--enablerepo=storpool-contrib",
                        "install",
                        "-q",
                        "-y",
                    ],
                },
                "pkgfile": {
                    "install": [
                        """
unset to_install to_reinstall
for f in $packages; do
    package="$(rpm -qp "$f")"
    if rpm -q -- "$package"; then
        to_reinstall="$to_reinstall ./$f"
    else
        to_install="$to_install ./$f"
    fi
done

if [ -n "$to_install" ]; then
    yum install -y --disablerepo='*' --enablerepo=base,updates,storpool-contrib --setopt=localpkg_gpgcheck=0 -- $to_install
fi
if [ -n "$to_reinstall" ]; then
    yum reinstall -y --disablerepo='*' --enablerepo=base,updates,storpool-contrib --setopt=localpkg_gpgcheck=0 -- $to_reinstall
fi
""",  # noqa: E501
                    ],
                },
            },
            "builder": {
                "alias": "centos7",
                "base_image": "centos:7",
                "branch": "centos/7",
                "kernel_package": "kernel",
                "utf8_locale": "en_US.utf8",
            },
        },
    ),
    defs.VariantUpdate(
        name="ORACLE7",
        descr="Oracle Linux 7.x",
        parent="CENTOS7",
        detect=defs.Detect(
            filename="/etc/oracle-release",
            regex=re.compile(r"^ Oracle \s+ Linux \s .* \s 7 \.", re.X),
            os_id="ol",
            os_version_regex=re.compile(r"^7(?:$|\.[0-9])"),
        ),
        updates={
            "builder": {
                "alias": "oracle7",
                "base_image": "IGNORE",
                "branch": "",
            },
        },
    ),
    defs.VariantUpdate(
        name="ORACLE8",
        descr="Oracle Linux 8.x",
        parent="ALMA8",
        detect=defs.Detect(
            filename="/etc/oracle-release",
            regex=re.compile(
                r"^ Oracle \s+ Linux \s+ Server \s+ release \s .* "
                r"\s 8 \. (?: [4-9] | [1-9][0-9] )",
                re.X,
            ),
            os_id="ol",
            os_version_regex=re.compile(r"^8(?:$|\.[4-9]|\.[1-9][0-9])"),
        ),
        updates={
            "commands": {
                "package": {
                    "install": [
                        "dnf",
                        "--disablerepo=*",
                        "--enablerepo=ol8_appstream",
                        "--enablerepo=ol8_baseos_latest",
                        "--enablerepo=ol8_codeready_builder",
                        "--enablerepo=storpool-contrib",
                        "install",
                        "-q",
                        "-y",
                        "--",
                    ],
                },
                "pkgfile": {
                    "install": [
                        "sh",
                        "-c",
                        """
unset to_install to_reinstall
for f in $packages; do
    package="$(rpm -qp "$f")"
    if rpm -q -- "$package"; then
        to_reinstall="$to_reinstall ./$f"
    else
        to_install="$to_install ./$f"
    fi
done

if [ -n "$to_install" ]; then
    dnf install -y --disablerepo='*' --enablerepo=ol8_appstream,ol8_baseos_latest,ol8_codeready_builder,storpool-contrib --setopt=localpkg_gpgcheck=0 -- $to_install
fi
if [ -n "$to_reinstall" ]; then
    dnf reinstall -y --disablerepo='*' --enablerepo=ol8_appstream,ol8_baseos_latest,ol8_codeready_builder,storpool-contrib --setopt=localpkg_gpgcheck=0 -- $to_reinstall
fi
""",  # noqa: E501
                    ],
                },
            },
            "builder": {
                "alias": "oracle8",
                "base_image": "oraclelinux:8",
                "branch": "",
            },
        },
    ),
    defs.VariantUpdate(
        name="RHEL8",
        descr="RedHat Enterprise Linux 8.x",
        parent="CENTOS8",
        detect=defs.Detect(
            filename="/etc/redhat-release",
            regex=re.compile(
                r"^ Red \s+ Hat \s+ Enterprise \s+ Linux \s .* "
                r"\s 8 \. (?: [4-9] | [1-9][0-9] )",
                re.X,
            ),
            os_id="rhel",
            os_version_regex=re.compile(r"^8(?:$|\.[4-9]|\.[1-9][0-9])"),
        ),
        updates={
            "commands": {
                "package": {
                    "install": [
                        "dnf",
                        "--disablerepo=*",
                        "--enablerepo=appstream",
                        "--enablerepo=baseos",
                        "--enablerepo=storpool-contrib",
                        "--enablerepo=codeready-builder-for-rhel-8-x86_64-rpms",
                        "install",
                        "-q",
                        "-y",
                        "--",
                    ],
                },
                "pkgfile": {
                    "install": [
                        "sh",
                        "-c",
                        """
unset to_install to_reinstall
for f in $packages; do
    package="$(rpm -qp "$f")"
    if rpm -q -- "$package"; then
        to_reinstall="$to_reinstall ./$f"
    else
        to_install="$to_install ./$f"
    fi
done

if [ -n "$to_install" ]; then
    dnf install -y --disablerepo='*' --enablerepo=appstream,baseos,storpool-contrib,codeready-builder-for-rhel-8-x86_64-rpms --setopt=localpkg_gpgcheck=0 -- $to_install
fi
if [ -n "$to_reinstall" ]; then
    dnf reinstall -y --disablerepo='*' --enablerepo=appstream,baseos,storpool-contrib,codeready-builder-for-rhel-8-x86_64-rpms --setopt=localpkg_gpgcheck=0 -- $to_reinstall
fi
""",  # noqa: E501
                    ],
                },
            },
            "builder": {
                "alias": "rhel8",
                "base_image": "redhat/ubi8:reg",
                "branch": "",
            },
        },
    ),
    defs.VariantUpdate(
        name="ROCKY9",
        descr="Rocky Linux 9.x",
        parent="ALMA9",
        detect=defs.Detect(
            filename="/etc/redhat-release",
            regex=re.compile(
                r"^ Rocky \s+ Linux \s .* \s 9 \. [0-9]",
                re.X,
            ),
            os_id="rocky",
            os_version_regex=re.compile(r"^8(?:$|\.[0-9])"),
        ),
        updates={
            "builder": {
                "alias": "rocky9",
                "base_image": "rockylinux:9",
                "branch": "",
            },
        },
    ),
    defs.VariantUpdate(
        name="ROCKY8",
        descr="Rocky Linux 8.x",
        parent="CENTOS8",
        detect=defs.Detect(
            filename="/etc/redhat-release",
            regex=re.compile(
                r"^ Rocky \s+ Linux \s .* \s 8 \. (?: [4-9] | [1-9][0-9] )",
                re.X,
            ),
            os_id="rocky",
            os_version_regex=re.compile(r"^8(?:$|\.[4-9]|\.[1-9][0-9])"),
        ),
        updates={
            "builder": {
                "alias": "rocky8",
                "base_image": "rockylinux:8",
                "branch": "",
            },
        },
    ),
]

VARIANTS: Final[dict[str, defs.Variant]] = {}

DETECT_ORDER: Final[list[defs.Variant]] = []


def _check_type(
    prefix: str,
    name: str,
    orig: Any,
    expected: type[Any] | tuple[type[Any], ...],
    tname: str,
) -> None:
    """Make sure the `orig` value is of the expected type."""
    if not isinstance(orig, expected):
        raise defs.VariantConfigError(f"{prefix}: {name} is not a {tname}")


def _update_dict(prefix: str, name: str, orig: Any, value: Any) -> Any:
    """Recurse into a tuple or replace a dictionary."""
    if isinstance(orig, tuple):
        return update_namedtuple(orig, value)  # type: ignore[type-var]  # argh

    if isinstance(orig, dict):
        orig.update(value)
        return orig

    raise defs.VariantConfigError(f"{prefix}: {name} is not a tuple")


def _update_string(prefix: str, name: str, orig: Any, value: Any) -> Any:
    """Replace a single string value."""
    _check_type(prefix, name, orig, str, "string")
    return value


def _update_bool(prefix: str, name: str, orig: Any, value: Any) -> Any:
    """Replace a single boolean value."""
    _check_type(prefix, name, orig, bool, "bool")
    return value


def _update_path(prefix: str, name: str, orig: Any, value: Any) -> Any:
    """Replace a single filesystem path."""
    if orig is not None:
        _check_type(prefix, name, orig, type(value), "path")
    return value


def _update_list(prefix: str, name: str, orig: Any, value: Any) -> Any:
    """Replace a list of values."""
    _check_type(prefix, name, orig, list, "list")
    return value


_UPDATE_HANDLERS: tuple[tuple[type[Any], Callable[[str, str, Any, Any], Any]], ...] = (
    (dict, _update_dict),
    (str, _update_string),
    (bool, _update_bool),
    (pathlib.Path, _update_path),
    (list, _update_list),
)


def update_namedtuple(data: _TNamedTuple, updates: dict[str, Any]) -> _TNamedTuple:
    """Create a new named tuple with some updated values."""
    if not updates:
        return data
    fields: Final[tuple[str, ...]] = data._fields

    newv: Final = {name: getattr(data, name) for name in fields}
    prefix: Final = f"Internal error: could not update {newv} with {updates}"

    for name, value in updates.items():
        if name not in newv:
            raise defs.VariantConfigError(f"{prefix}: unexpected field {name}")
        orig = newv[name]

        for vtype, handler in _UPDATE_HANDLERS:
            if isinstance(value, vtype):
                newv[name] = handler(prefix, name, orig, value)
                break
        else:
            raise defs.VariantConfigError(
                f"{prefix}: weird {type(value).__name__} update for {name}",
            )

    updated: Final[_TNamedTuple] = type(data)(**newv)  # type: ignore[call-overload]
    return updated


def merge_into_parent(
    cfg: defs.Config,
    parent: defs.Variant,
    child: defs.VariantUpdate,
) -> defs.Variant:
    """Merge a child's definitions into the parent."""
    cfg.diag(f"- merging {child.name} into {parent.name}")
    return update_namedtuple(
        defs.Variant(
            name=child.name,
            descr=child.descr,
            parent=parent.name,
            family=parent.family,
            detect=child.detect,
            supported=parent.supported,
            commands=parent.commands,
            repo=parent.repo,
            package=dict(parent.package),
            min_sys_python=parent.min_sys_python,
            systemd_lib=parent.systemd_lib,
            file_ext=parent.file_ext,
            initramfs_flavor=parent.initramfs_flavor,
            builder=parent.builder,
        ),
        child.updates,
    )


def build_variants(cfg: defs.Config) -> None:
    """Build the variant definitions from the parent/child relations."""
    # We really hope these asserts will not trigger, but let's leave them in for now.
    if VARIANTS:
        assert len(VARIANTS) == len(_VARIANT_DEF)  # noqa: S101
        assert DETECT_ORDER  # noqa: S101
        assert len(DETECT_ORDER) == len(_VARIANT_DEF)  # noqa: S101
        return
    assert not DETECT_ORDER  # noqa: S101

    cfg.diag("Building the list of variants")
    order: Final[list[str]] = []
    for var in _VARIANT_DEF:
        current = (
            merge_into_parent(cfg, VARIANTS[var.parent], var)
            if isinstance(var, defs.VariantUpdate)
            else var
        )
        VARIANTS[var.name] = current
        order.append(var.name)

    order.reverse()
    DETECT_ORDER.extend([VARIANTS[name] for name in order])
    cfg.diag("Detect order: {names}".format(names=" ".join(var.name for var in DETECT_ORDER)))
