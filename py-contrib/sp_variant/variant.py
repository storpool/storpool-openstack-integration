# Copyright (c) 2021, 2022  StorPool <support@storpool.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
"""
Support for different OS distributions and StorPool build variants.

NB: This should be the only file in the StorPool source that cannot
really depend on sp-python2 and sp-python2-modules being installed.

NB: This is a looong file. It has to be, since it needs to be
completely self-contained so that it may be copied over to
a remote host and executed there.
"""

# pylint: disable=too-many-lines

from __future__ import print_function

import argparse
import errno
import io
import json
import os
import re
import subprocess
import sys

try:
    from typing import (
        Any,  # noqa: H301
        Callable,
        Dict,
        Iterable,
        List,
        NamedTuple,
        Optional,
        Pattern,
        Text,
        Tuple,
        Type,
        TypeVar,
        Union,
        TYPE_CHECKING,
    )

    Detect = NamedTuple(  # pylint: disable=invalid-name
        "Detect",
        [
            ("filename", Text),
            ("regex", Pattern[Text]),
            ("os_id", Text),
            ("os_version_regex", Pattern[Text]),
        ],
    )

    CommandsPackage = NamedTuple(  # pylint: disable=invalid-name
        "CommandsPackage",
        [
            ("update_db", List[Text]),
            ("install", List[Text]),
            ("list_all", List[Text]),
            ("purge", List[Text]),
            ("remove", List[Text]),
            ("remove_impl", List[Text]),
        ],
    )

    CommandsPkgFile = NamedTuple(  # pylint: disable=invalid-name
        "CommandsPkgFile",
        [
            ("dep_query", List[Text]),
            ("install", List[Text]),
        ],
    )

    Commands = NamedTuple(  # pylint: disable=invalid-name
        "Commands",
        [
            ("package", CommandsPackage),
            ("pkgfile", CommandsPkgFile),
        ],
    )

    DebRepo = NamedTuple(  # pylint: disable=invalid-name
        "DebRepo",
        [
            ("codename", Text),
            ("vendor", Text),
            ("sources", Text),
            ("keyring", Text),
            ("req_packages", List[Text]),
        ],
    )

    YumRepo = NamedTuple(  # pylint: disable=invalid-name
        "YumRepo",
        [
            ("yumdef", Text),
            ("keyring", Text),
        ],
    )

    Builder = NamedTuple(  # pylint: disable=invalid-name
        "Builder",
        [
            ("alias", Text),
            ("base_image", Text),
            ("branch", Text),
            ("kernel_package", Text),
            ("utf8_locale", Text),
        ],
    )

    Variant = NamedTuple(  # pylint: disable=invalid-name
        "Variant",
        [
            ("name", Text),
            ("descr", Text),
            ("parent", Text),
            ("family", Text),
            ("detect", Detect),
            ("commands", Commands),
            ("min_sys_python", Text),
            ("repo", Union[DebRepo, YumRepo]),
            ("package", Dict[str, str]),
            ("systemd_lib", Text),
            ("file_ext", Text),
            ("initramfs_flavor", Text),
            ("builder", Builder),
        ],
    )

    VariantUpdate = NamedTuple(  # pylint: disable=invalid-name
        "VariantUpdate",
        [
            ("name", Text),
            ("descr", Text),
            ("parent", Text),
            ("detect", Detect),
            ("updates", Dict[str, Any]),
        ],
    )

    OSPackage = NamedTuple(  # pylint: disable=invalid-name
        "OSPackage",
        [
            ("name", Text),
            ("version", Text),
            ("arch", Text),
            ("status", Text),
        ],
    )

    RepoType = NamedTuple("RepoType", [("name", str), ("extension", str), ("url", str)])

    T = TypeVar("T")  # pylint: disable=invalid-name

    if TYPE_CHECKING:
        if sys.version_info[0] >= 3:
            # pylint: disable-next=protected-access,unsubscriptable-object
            SubPAction = argparse._SubParsersAction[argparse.ArgumentParser]
        else:
            # pylint: disable-next=protected-access
            SubPAction = argparse._SubParsersAction
except ImportError:
    import collections

    Detect = collections.namedtuple(  # type: ignore
        "Detect",
        [
            "filename",
            "regex",
            "os_id",
            "os_version_regex",
        ],
    )

    CommandsPackage = collections.namedtuple(  # type: ignore
        "CommandsPackage",
        ["update_db", "install", "list_all", "purge", "remove", "remove_impl"],
    )

    CommandsPkgFile = collections.namedtuple(  # type: ignore
        "CommandsPkgFile",
        [
            "dep_query",
            "install",
        ],
    )

    Commands = collections.namedtuple(  # type: ignore
        "Commands",
        [
            "package",
            "pkgfile",
        ],
    )

    DebRepo = collections.namedtuple(  # type: ignore
        "DebRepo",
        [
            "vendor",
            "codename",
            "sources",
            "keyring",
            "req_packages",
        ],
    )

    YumRepo = collections.namedtuple(  # type: ignore
        "YumRepo",
        [
            "yumdef",
            "keyring",
        ],
    )

    Builder = collections.namedtuple(  # type: ignore
        "Builder",
        [
            "alias",
            "base_image",
            "branch",
            "kernel_package",
            "utf8_locale",
        ],
    )

    Variant = collections.namedtuple(  # type: ignore
        "Variant",
        [
            "name",
            "descr",
            "parent",
            "family",
            "detect",
            "commands",
            "min_sys_python",
            "repo",
            "package",
            "systemd_lib",
            "file_ext",
            "initramfs_flavor",
            "builder",
        ],
    )

    VariantUpdate = collections.namedtuple(  # type: ignore
        "VariantUpdate",
        [
            "name",
            "descr",
            "parent",
            "detect",
            "updates",
        ],
    )

    OSPackage = collections.namedtuple(  # type: ignore
        "OSPackage", ["name", "version", "arch", "status"]
    )

    RepoType = collections.namedtuple("RepoType", ["name", "extension", "url"])  # type: ignore

if sys.version_info[0] >= 3:
    TextType = str
    BytesType = bytes
else:
    TextType = unicode  # noqa: F821  # pylint: disable=undefined-variable
    BytesType = str


VERSION = "2.2.0"
FORMAT_VERSION = (1, 3)


REPO_TYPES = [
    RepoType(name="contrib", extension="", url="https://repo.storpool.com/public/"),
    RepoType(
        name="staging",
        extension="-staging",
        url="https://repo.storpool.com/public/",
    ),
    RepoType(
        name="infra",
        extension="-infra",
        url="https://intrepo.storpool.com/repo/",
    ),
]


class Config(object):  # pylint: disable=too-few-public-methods
    """Basic configuration: a "verbose" field and a diag() method."""

    def __init__(
        self,  # type: Config
        args=None,  # type: Optional[List[Text]]
        command=None,  # type: Optional[Text]
        noop=False,  # type: bool
        repodir=None,  # type: Optional[Text]
        repotype=REPO_TYPES[0],  # type: RepoType
        verbose=False,  # type: bool
    ):  # type: (...) -> None
        """Store the verbosity setting."""
        # pylint: disable=too-many-arguments
        self.args = args
        self.command = command
        self.noop = noop
        self.repodir = repodir
        self.repotype = repotype
        self.verbose = verbose
        self._diag_to_stderr = True

    def diag(self, msg):
        # type: (Config, Text) -> None
        """Output a diagnostic message in verbose mode."""
        if self.verbose:
            print(msg, file=sys.stderr if self._diag_to_stderr else sys.stdout)


MINENC = "us-ascii"
SAFEENC = "Latin-1"

CMD_NOOP = ["true"]  # type: List[Text]

_RE_YAIP_LINE = re.compile(
    r"""
    ^ (?:
        (?P<comment> \s* (?: \# .* )? )
        |
        (?:
            (?P<varname> [A-Za-z0-9_]+ )
            =
            (?P<full>
                (?P<oquot> ["'] )?
                (?P<quoted> .*? )
                (?P<cquot> ["'] )?
            )
        )
    ) $ """,
    re.X,
)

_DEFAULT_CONFIG = Config()

_VARIANT_DEF = [
    Variant(
        name="DEBIAN12",
        descr="Debian 12.x (bookworm/unstable)",
        parent="",
        family="debian",
        detect=Detect(
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
        commands=Commands(
            package=CommandsPackage(
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
            pkgfile=CommandsPkgFile(
                dep_query=[
                    "sh",
                    "-c",
                    "dpkg-deb -f -- \"$pkg\" 'Depends' | sed -e 's/ *, */,/g' | tr ',' \"\\n\"",
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
        min_sys_python="3.9",
        repo=DebRepo(
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
            "LIBSSL": "libssl1.1",
            "MCELOG": "mcelog",
        },
        systemd_lib="lib/systemd/system",
        file_ext="deb",
        initramfs_flavor="update-initramfs",
        builder=Builder(
            alias="debian12",
            base_image="debian:unstable",
            branch="debian/unstable",
            kernel_package="linux-headers",
            utf8_locale="C.UTF-8",
        ),
    ),
    VariantUpdate(
        name="DEBIAN11",
        descr="Debian 11.x (bullseye)",
        parent="DEBIAN12",
        detect=Detect(
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
            "repo": {"codename": "bullseye"},
            "builder": {
                "alias": "debian11",
                "base_image": "debian:bullseye",
                "branch": "debian/bullseye",
            },
        },
    ),
    VariantUpdate(
        name="DEBIAN10",
        descr="Debian 10.x (buster)",
        parent="DEBIAN11",
        detect=Detect(
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
            "repo": {
                "codename": "buster",
            },
            "min_sys_python": "2.7",
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
    VariantUpdate(
        name="DEBIAN9",
        descr="Debian 9.x (stretch)",
        parent="DEBIAN10",
        detect=Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"""^
                    PRETTY_NAME= .*
                    Debian \s+ GNU/Linux \s+
                    (?: stretch | 9 ) (?: \s | / )
                """,
                re.X,
            ),
            os_id="debian",
            os_version_regex=re.compile(r"^9$"),
        ),
        updates={
            "repo": {
                "codename": "stretch",
                "req_packages": ["apt-transport-https", "ca-certificates"],
            },
            "builder": {
                "alias": "debian9",
                "base_image": "debian:stretch",
                "branch": "debian/stretch",
            },
        },
    ),
    VariantUpdate(
        name="UBUNTU2204",
        descr="Ubuntu 22.04 LTS (Jammy Jellyfish)",
        parent="DEBIAN12",
        detect=Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"^ PRETTY_NAME= .* (?: Ubuntu \s+ 22 \. 04 | Mint \s+ 22 ) ",
                re.X,
            ),
            os_id="ubuntu",
            os_version_regex=re.compile(r"^22\.04$"),
        ),
        updates={
            "repo": {
                "vendor": "ubuntu",
                "codename": "jammy",
            },
            "package": {
                "CPUPOWER": "linux-tools-generic",
                "MCELOG": "bash",
            },
            "builder": {
                "alias": "ubuntu-22.04",
                "base_image": "ubuntu:jammy",
                "branch": "ubuntu/jammy",
            },
        },
    ),
    VariantUpdate(
        name="UBUNTU2110",
        descr="Ubuntu 21.10 LTS (Impish Indri)",
        parent="UBUNTU2204",
        detect=Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"^ PRETTY_NAME= .* (?: Ubuntu \s+ 21 \. 10 | Mint \s+ 21 ) ",
                re.X,
            ),
            os_id="ubuntu",
            os_version_regex=re.compile(r"^21\.10$"),
        ),
        updates={
            "repo": {
                "vendor": "ubuntu",
                "codename": "impish",
            },
            "builder": {
                "alias": "ubuntu-21.10",
                "base_image": "ubuntu:impish",
                "branch": "ubuntu/impish",
            },
        },
    ),
    VariantUpdate(
        name="UBUNTU2004",
        descr="Ubuntu 20.04 LTS (Focal Fossa)",
        parent="UBUNTU2110",
        detect=Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"^ PRETTY_NAME= .* (?: Ubuntu \s+ 20 \. 04 | Mint \s+ 20 ) ",
                re.X,
            ),
            os_id="ubuntu",
            os_version_regex=re.compile(r"^20\.04$"),
        ),
        updates={
            "repo": {
                "vendor": "ubuntu",
                "codename": "focal",
            },
            "min_sys_python": "3.8",
            "builder": {
                "alias": "ubuntu-20.04",
                "base_image": "ubuntu:focal",
                "branch": "ubuntu/focal",
            },
        },
    ),
    VariantUpdate(
        name="UBUNTU1804",
        descr="Ubuntu 18.04 LTS (Bionic Beaver)",
        parent="UBUNTU2004",
        detect=Detect(
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
            "min_sys_python": "2.7",
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
    VariantUpdate(
        name="UBUNTU1604",
        descr="Ubuntu 16.04 LTS (Xenial Xerus)",
        parent="UBUNTU1804",
        detect=Detect(
            filename="/etc/os-release",
            regex=re.compile(
                r"^ PRETTY_NAME= .* Ubuntu \s+ 16 \. 04 ",
                re.X,
            ),
            os_id="ubuntu",
            os_version_regex=re.compile(r"^16\.04$"),
        ),
        updates={
            "repo": {
                "codename": "xenial",
                "req_packages": ["apt-transport-https", "ca-certificates"],
            },
            "package": {
                "LIBSSL": "libssl1.0.0",
                "mcelog": "mcelog",
            },
            "builder": {
                "alias": "ubuntu-16.04",
                "base_image": "ubuntu:xenial",
                "branch": "ubuntu/xenial",
            },
        },
    ),
    Variant(
        name="CENTOS8",
        descr="CentOS 8.x",
        parent="",
        family="redhat",
        detect=Detect(
            filename="/etc/redhat-release",
            regex=re.compile(r"^ CentOS \s .* \s 8 \. (?: [3-9] | (?: [12][0-9] ) )", re.X),
            os_id="centos",
            os_version_regex=re.compile(r"^8(?:$|\.[4-9]|\.[1-9][0-9])"),
        ),
        commands=Commands(
            package=CommandsPackage(
                update_db=CMD_NOOP,
                install=[
                    "dnf",
                    "--enablerepo=storpool-contrib",
                    "--enablerepo=powertools",
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
            pkgfile=CommandsPkgFile(
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
    dnf install -y --enablerepo=storpool-contrib,powertools --setopt=localpkg_gpgcheck=0 -- $to_install
fi
if [ -n "$to_reinstall" ]; then
    dnf reinstall -y --enablerepo=storpool-contrib,powertools --setopt=localpkg_gpgcheck=0 -- $to_reinstall
fi
""",  # noqa: E501  pylint: disable=line-too-long
                ],
            ),
        ),
        min_sys_python="2.7",
        repo=YumRepo(
            yumdef="redhat/repo/storpool-centos.repo",
            keyring="redhat/repo/RPM-GPG-KEY-StorPool",
        ),
        package={
            "KMOD": "kmod",
            "LIBCGROUP": "libcgroup-tools",
            "LIBUDEV": "systemd-libs",
            "OPENSSL": "openssl-libs",
            "PERL_AUTODIE": "perl-autodie",
            "PERL_FILE_PATH": "perl-File-Path",
            "PERL_LWP_PROTO_HTTPS": "perl-LWP-Protocol-https",
            "PERL_SYS_SYSLOG": "perl-Sys-Syslog",
            "PYTHON_SIMPLEJSON": "python2-simplejson",
            "PROCPS": "procps-ng",
            "UDEV": "systemd",
        },
        systemd_lib="usr/lib/systemd/system",
        file_ext="rpm",
        initramfs_flavor="mkinitrd",
        builder=Builder(
            alias="centos8",
            base_image="centos:8",
            branch="centos/8",
            kernel_package="kernel-core",
            utf8_locale="C.utf8",
        ),
    ),
    VariantUpdate(
        name="CENTOS7",
        descr="CentOS 7.x",
        parent="CENTOS8",
        detect=Detect(
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
    yum install -y --enablerepo=storpool-contrib --setopt=localpkg_gpgcheck=0 -- $to_install
fi
if [ -n "$to_reinstall" ]; then
    yum reinstall -y --enablerepo=storpool-contrib --setopt=localpkg_gpgcheck=0 -- $to_reinstall
fi
""",  # noqa: E501  pylint: disable=line-too-long
                    ],
                },
            },
            "builder": {
                "alias": "centos7",
                "base_image": "centos:7",
                "branch": "centos/7",
                "kernel_package": "kernel",
                "utf8_locale": "C",
            },
        },
    ),
    VariantUpdate(
        name="CENTOS6",
        descr="CentOS 6.x",
        parent="CENTOS7",
        detect=Detect(
            filename="/etc/redhat-release",
            regex=re.compile(r"^ CentOS \s .* \s 6 \.", re.X),
            os_id="centos",
            os_version_regex=re.compile(r"^6(?:$|\.[0-9])"),
        ),
        updates={
            "min_sys_python": "2.6",
            "package": {
                "KMOD": "module-init-tools",
                "LIBCGROUP": "libcgroup",
                "LIBUDEV": "libudev",
                "OPENSSL": "openssl",
                "PERL_AUTODIE": "perl",
                "PERL_FILE_PATH": "perl",
                "PERL_LWP_PROTO_HTTPS": "perl",
                "PERL_SYS_SYSLOG": "perl",
                "PYTHON_SIMPLEJSON": "python-simplejson",
                "PROCPS": "procps",
                "UDEV": "udev",
            },
            "builder": {
                "alias": "centos6",
                "base_image": "centos:6",
                "branch": "centos/6",
            },
        },
    ),
    VariantUpdate(
        name="ORACLE7",
        descr="Oracle Linux 7.x",
        parent="CENTOS7",
        detect=Detect(
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
    VariantUpdate(
        name="RHEL8",
        descr="RedHat Enterprise Linux 8.x",
        parent="CENTOS8",
        detect=Detect(
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
                        "--enablerepo=storpool-contrib",
                        "--enablerepo=codeready-builder-for-rhel-8-x86_64-rpms",
                        "install",
                        "-q",
                        "-y",
                        "--",
                    ]
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
    dnf install -y --enablerepo=storpool-contrib,codeready-builder-for-rhel-8-x86_64-rpms --setopt=localpkg_gpgcheck=0 -- $to_install
fi
if [ -n "$to_reinstall" ]; then
    dnf reinstall -y --enablerepo=storpool-contrib,codeready-builder-for-rhel-8-x86_64-rpms --setopt=localpkg_gpgcheck=0 -- $to_reinstall
fi
""",  # noqa: E501  pylint: disable=line-too-long
                    ]
                },
            },
            "builder": {
                "alias": "rhel8",
                "base_image": "redhat/ubi8:reg",
                "branch": "",
            },
        },
    ),
    VariantUpdate(
        name="ROCKY8",
        descr="Rocky Linux 8.x",
        parent="CENTOS8",
        detect=Detect(
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
                "base_image": "rockylinux/rockylinux:8",
                "branch": "",
            },
        },
    ),
    VariantUpdate(
        name="ALMA8",
        descr="AlmaLinux 8.x",
        parent="CENTOS8",
        detect=Detect(
            filename="/etc/redhat-release",
            regex=re.compile(r"^ AlmaLinux \s .* \s 8 \. (?: [4-9] | [1-9][0-9] )", re.X),
            os_id="alma",
            os_version_regex=re.compile(r"^8(?:$|\.[4-9]|\.[1-9][0-9])"),
        ),
        updates={
            "builder": {
                "alias": "alma8",
                "base_image": "almalinux/almalinux:8",
                "branch": "",
            },
        },
    ),
]  # type: (List[Union[Variant, VariantUpdate]])

VARIANTS = {}  # type: Dict[Text, Variant]

_DETECT_ORDER = []  # type: List[Variant]

CMD_LIST_BRIEF = [
    ("pkgfile", "install"),
]


class VariantError(Exception):
    """Base class for errors that occurred during variant processing."""


class VariantKeyError(VariantError):
    """A variant with an unknown name was requested."""


class VariantConfigError(VariantError):
    """Invalid parameters passed to the variant routines."""


class VariantFileError(VariantError):
    """A filesystem-related error occurred."""


class VariantRemoteError(VariantError):
    """An error occurred while communicating with a remote host."""

    def __init__(self, hostname, msg):
        # type: (VariantRemoteError, Text, Text) -> None
        """Store the hostname and the error message."""
        super(VariantRemoteError, self).__init__()
        self.hostname = hostname
        self.msg = msg

    def __str__(self):
        # type: () -> str
        """Return a human-readable representation of the error."""
        return "{host}: {err}".format(host=self.hostname, err=self.msg)


class VariantDetectError(VariantError):
    """An error that occurred during the detection of a variant."""


class _YAIParser(object):
    """Yet another INI-like file parser, this time for /etc/os-release."""

    def __init__(self, filename):
        # type: (_YAIParser, Text) -> None
        """Initialize a _YAIParser object: store the filename."""
        self.filename = filename
        self.data = {}  # type: Dict[TextType, TextType]

    def parse_line(
        self,  # type: _YAIParser
        line,  # type: Union[TextType, BytesType]
    ):  # type: (...) -> Optional[Tuple[TextType, TextType]]
        """Parse a single var=value line."""
        if isinstance(line, BytesType):
            try:
                line = line.decode("UTF-8")
            except UnicodeDecodeError as err:
                raise VariantError(
                    "Invalid {fname} line, not a valid UTF-8 string: {line!r}: {err}".format(
                        fname=self.filename, line=line, err=err
                    )
                )
        assert isinstance(line, TextType)

        mline = _RE_YAIP_LINE.match(line)
        if not mline:
            raise VariantError(
                "Unexpected {fname} line: {line!r}".format(fname=self.filename, line=line)
            )
        if mline.group("comment") is not None:
            return None

        varname, oquot, cquot, quoted, full = (
            mline.group("varname"),
            mline.group("oquot"),
            mline.group("cquot"),
            mline.group("quoted"),
            mline.group("full"),
        )

        if oquot == "'":
            if oquot in quoted:
                raise VariantError(
                    (
                        "Weird {fname} line, the quoted content "
                        "contains the quote character: {line!r}"
                    ).format(fname=self.filename, line=line)
                )
            if cquot != oquot:
                raise VariantError(
                    "Weird {fname} line, open/close quote mismatch: {line!r}".format(
                        fname=self.filename, line=line
                    )
                )

            return (varname, quoted)

        if oquot is None:
            quoted = full
        elif cquot != oquot:
            raise VariantError(
                "Weird {fname} line, open/close quote mismatch: {line!r}".format(
                    fname=self.filename, line=line
                )
            )

        res = TextType("")
        while quoted:
            try:
                idx = quoted.index("\\")
            except ValueError:
                res += quoted
                break

            if idx == len(quoted) - 1:
                raise VariantError(
                    (
                        "Weird {fname} line, backslash at the end of the quoted string: {line!r}"
                    ).format(fname=self.filename, line=line)
                )
            res += quoted[:idx] + quoted[idx + 1]
            quoted = quoted[idx + 2 :]

        return (varname, res)

    def parse(self):
        # type: (_YAIParser) -> Dict[TextType, TextType]
        """Parse a file, store and return the result."""
        with io.open(self.filename, mode="r", encoding="UTF-8") as infile:
            contents = infile.read()
        data = {}
        for line in contents.splitlines():
            res = self.parse_line(line)
            if res is None:
                continue
            data[res[0]] = res[1]

        self.data = data
        return data

    def get(self, key):
        # type: (_YAIParser, Union[TextType, BytesType]) -> Optional[TextType]
        """Get a value parsed from the configuration file."""
        if isinstance(key, BytesType):
            key = key.decode("UTF-8")
        assert isinstance(key, TextType)
        return self.data.get(key)


def update_namedtuple(data, updates):
    # type: (T, Dict[str, Any]) -> T
    """Create a new named tuple with some updated values."""
    if not updates:
        return data
    fields = getattr(data, "_fields")  # type: List[str]

    newv = dict((name, getattr(data, name)) for name in fields)
    prefix = "Internal error: could not update {newv} with {updates}".format(
        newv=newv, updates=updates
    )

    for name, value in updates.items():
        if name not in newv:
            raise VariantConfigError(
                "{prefix}: unexpected field {name}".format(prefix=prefix, name=name)
            )
        orig = newv[name]

        def check_type(
            name,  # type: str
            orig,  # type: Any
            expected,  # type: Union[Type[Any], Tuple[Type[Any], ...]]
            tname,  # type: str
        ):  # type: (...) -> None
            """Make sure the `orig` value is of the expected type."""
            if not isinstance(orig, expected):
                raise VariantConfigError(
                    "{prefix}: {name} is not a {tname}".format(
                        prefix=prefix, name=name, tname=tname
                    )
                )

        if isinstance(value, dict):
            if isinstance(orig, tuple):
                newv[name] = update_namedtuple(orig, value)
            elif isinstance(orig, dict):
                newv[name].update(value)
            else:
                raise VariantConfigError(
                    "{prefix}: {name} is not a tuple".format(prefix=prefix, name=name)
                )
        elif isinstance(
            value,
            (
                str,
                TextType,
            ),
        ):
            check_type(name, orig, (str, TextType), "string")
            newv[name] = value
        elif type(value).__name__ == "PosixPath":
            if orig is not None:
                check_type(name, orig, type(value), "path")
            newv[name] = value
        elif isinstance(value, list):
            check_type(name, orig, list, "list")
            newv[name] = value
        else:
            raise VariantConfigError(
                "{prefix}: weird {tname} update for {name}".format(
                    prefix=prefix,
                    tname=type(value).__name__,
                    name=name,
                )
            )

    updated = type(data)(**newv)
    return updated


def merge_into_parent(cfg, parent, child):
    # type: (Config, Variant, VariantUpdate) -> Variant
    """Merge a child's definitions into the parent."""
    cfg.diag("- merging {child} into {parent}".format(child=child.name, parent=parent.name))
    return update_namedtuple(
        Variant(
            name=child.name,
            descr=child.descr,
            parent=parent.name,
            family=parent.family,
            detect=child.detect,
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


def build_variants(cfg):
    # type: (Config) -> None
    """Build the variant definitions from the parent/child relations."""
    if VARIANTS:
        assert len(VARIANTS) == len(_VARIANT_DEF)
        assert _DETECT_ORDER
        assert len(_DETECT_ORDER) == len(_VARIANT_DEF)
        return
    assert not _DETECT_ORDER

    cfg.diag("Building the list of variants")
    order = []  # type: List[Text]
    for var in _VARIANT_DEF:
        if isinstance(var, VariantUpdate):
            current = merge_into_parent(cfg, VARIANTS[var.parent], var)
        else:
            current = var

        VARIANTS[var.name] = current
        order.append(var.name)

    order.reverse()
    _DETECT_ORDER.extend([VARIANTS[name] for name in order])
    cfg.diag("Detect order: {names}".format(names=" ".join(var.name for var in _DETECT_ORDER)))


def get_variant(name, cfg=_DEFAULT_CONFIG):
    # type: (Text, Config) -> Variant
    """Return the variant with the specified name."""
    build_variants(cfg)
    try:
        return VARIANTS[name]
    except KeyError:
        raise VariantKeyError("No variant named {name}".format(name=name))


def get_by_alias(alias, cfg=_DEFAULT_CONFIG):
    # type: (Text, Config) -> Variant
    """Return the variant with the specified name."""
    build_variants(cfg)
    for var in VARIANTS.values():
        if var.builder.alias == alias:
            return var
    raise VariantKeyError("No variant with alias {alias}".format(alias=alias))


def get_all_variants(cfg=_DEFAULT_CONFIG):
    # type: (Config) -> Dict[Text, Variant]
    """Return information about all the supported variants."""
    build_variants(cfg)
    return dict(VARIANTS)


def get_all_variants_in_order(cfg=_DEFAULT_CONFIG):
    # type: (Config) -> List[Variant]
    """Return information about all supported variants in detect order."""
    build_variants(cfg)
    return list(_DETECT_ORDER)


def detect_variant(cfg=_DEFAULT_CONFIG):
    # type: (Config) -> Variant
    """Detect the build variant for the current host."""
    build_variants(cfg)
    cfg.diag("Trying to detect the current hosts's build variant")

    try:
        data = _YAIParser("/etc/os-release").parse()
        os_id, os_version = data.get("ID"), data.get("VERSION_ID")
    except (IOError, OSError) as err:
        if err.errno != errno.ENOENT:
            raise
        os_id, os_version = None, None

    if os_id is not None and os_version is not None:
        cfg.diag(
            "Matching os-release id {os_id!r} version {os_version!r}".format(
                os_id=os_id, os_version=os_version
            )
        )
        for var in _DETECT_ORDER:
            cfg.diag("- trying {name}".format(name=var.name))
            if var.detect.os_id == os_id and var.detect.os_version_regex.match(os_version):
                cfg.diag("  - found it!")
                return var

    cfg.diag("Trying non-os-release-based heuristics")
    for var in _DETECT_ORDER:
        cfg.diag("- trying {name}".format(name=var.name))
        try:
            with io.open(var.detect.filename, mode="r", encoding=SAFEENC) as osf:
                cfg.diag("  - {fname}".format(fname=var.detect.filename))
                for line in (line.rstrip("\r\n") for line in osf.readlines()):
                    if var.detect.regex.match(line):
                        cfg.diag("  - found it: {line}".format(line=line))
                        return var
        except (IOError, OSError) as err:
            if err.errno != errno.ENOENT:
                raise VariantDetectError(
                    "Could not read the {fname} file: {err}".format(
                        fname=var.detect.filename, err=err
                    )
                )
            cfg.diag("  - no {fname}".format(fname=var.detect.filename))

    raise VariantDetectError("Could not detect the current host's build variant")


def list_all_packages(var, patterns=None):
    # type: (Variant, Optional[Iterable[str]]) -> List[OSPackage]
    """Parse the output of the "list installed packages" command."""
    cmd = var.commands.package.list_all
    if patterns is not None:
        cmd.extend(patterns)

    res = []
    for line in subprocess.check_output(cmd, shell=False).decode("UTF-8").splitlines():
        fields = line.split("\t")
        if len(fields) != 4:
            raise VariantFileError(
                "Unexpected line in the '{cmd}' output: {line}".format(
                    cmd=" ".join(cmd), line=repr(line)
                )
            )
        # This may need updating at some point, but it'll work for now
        if fields[3] != "ii":
            continue

        res.append(
            OSPackage(
                name=fields[0],
                version=fields[1],
                arch=fields[2],
                status="installed",
            )
        )

    return res


def cmd_detect(cfg):
    # type: (Config) -> None
    """Detect and output the build variant for the current host."""
    try:
        print(detect_variant(cfg=cfg).name)
    except VariantError as err:
        print(str(err), file=sys.stderr)
        sys.exit(1)


def copy_file(cfg, src, dstdir):
    # type: (Config, Text, Text) -> None
    """Use `install(8)` to install a configuration file."""
    dst = os.path.join(dstdir, os.path.basename(src))
    mode = "0644"
    cfg.diag("{src} -> {dst} [{mode}]".format(src=src, dst=dst, mode=mode))
    try:
        subprocess.check_call(
            [
                "install",
                "-o",
                "root",
                "-g",
                "root",
                "-m",
                mode,
                "--",
                src,
                dst,
            ],
            shell=False,
        )
    except subprocess.CalledProcessError as err:
        raise VariantFileError(
            "Could not copy {src} over to {dst}: {err}".format(src=src, dst=dst, err=err)
        )


def repo_add_extension(cfg, name):
    # type: (Config, Text) -> Text
    """Add the extension for the specified repository type."""
    parts = name.rsplit(".")
    if len(parts) != 2:
        raise VariantFileError(
            "Unexpected repository file name without an extension: {name}".format(name=name)
        )
    return "{stem}{extension}.{ext}".format(
        stem=parts[0], extension=cfg.repotype.extension, ext=parts[1]
    )


def repo_add_deb(cfg, var, vardir):
    # type: (Config, Variant, Text) -> None
    """Install the StorPool Debian-like repo configuration."""
    assert isinstance(var.repo, DebRepo)

    try:
        subprocess.check_call(var.commands.package.install + var.repo.req_packages, shell=False)
    except subprocess.CalledProcessError as err:
        raise VariantFileError(
            "Could not install the required packages {req}: {err}".format(
                req=" ".join(var.repo.req_packages), err=err
            )
        )

    copy_file(
        cfg,
        os.path.join(vardir, repo_add_extension(cfg, os.path.basename(var.repo.sources))),
        "/etc/apt/sources.list.d",
    )
    copy_file(
        cfg,
        os.path.join(vardir, os.path.basename(var.repo.keyring)),
        "/usr/share/keyrings",
    )

    try:
        subprocess.check_call(["apt-get", "update"], shell=False)
    except subprocess.CalledProcessError as err:
        raise VariantFileError("Could not update the APT database: {err}".format(err=err))


def repo_add_yum(cfg, var, vardir):
    # type: (Config, Variant, Text) -> None
    """Install the StorPool RedHat/CentOS-like repo configuration."""
    assert isinstance(var.repo, YumRepo)

    try:
        subprocess.check_call(
            [
                "yum",
                "--disablerepo=storpool-*'",
                "install",
                "-q",
                "-y",
                "ca-certificates",
            ],
            shell=False,
        )
    except subprocess.CalledProcessError as err:
        raise VariantFileError(
            "Could not install the required ca-certificates package: {err}".format(err=err)
        )

    copy_file(
        cfg,
        os.path.join(vardir, repo_add_extension(cfg, os.path.basename(var.repo.yumdef))),
        "/etc/yum.repos.d",
    )
    copy_file(
        cfg,
        os.path.join(vardir, os.path.basename(var.repo.keyring)),
        "/etc/pki/rpm-gpg",
    )

    if os.path.isfile("/usr/bin/rpmkeys"):
        try:
            subprocess.check_call(
                [
                    "rpmkeys",
                    "--import",
                    os.path.join("/etc/pki/rpm-gpg", os.path.basename(var.repo.keyring)),
                ],
                shell=False,
            )
        except subprocess.CalledProcessError as err:
            raise VariantFileError("Could not import the RPM PGP keys: {err}".format(err=err))

    try:
        subprocess.check_call(
            [
                "yum",
                "--disablerepo=*",
                "--enablerepo=storpool-{name}".format(name=cfg.repotype.name),
                "clean",
                "metadata",
            ],
            shell=False,
        )
    except subprocess.CalledProcessError as err:
        raise VariantFileError("Could not clean the Yum repository metadata: {err}".format(err=err))


def repo_add(cfg):
    # type: (Config) -> None
    """Install the StorPool repository configuration."""
    assert cfg.repodir is not None
    var = detect_variant(cfg)
    vardir = os.path.join(cfg.repodir, var.name)
    if not os.path.isdir(vardir):
        raise VariantConfigError("No {vdir} directory".format(vdir=vardir))

    if isinstance(var.repo, DebRepo):
        repo_add_deb(cfg, var, vardir)
    elif isinstance(var.repo, YumRepo):
        repo_add_yum(cfg, var, vardir)


def cmd_repo_add(cfg):
    # type: (Config) -> None
    """Install the StorPool repository configuration, display errors."""
    try:
        repo_add(cfg)
    except VariantError as err:
        print(str(err), file=sys.stderr)
        sys.exit(1)


def command_find(cfg, var):
    # type: (Config, Variant) -> List[Text]
    """Get a distribution-specific command from the variant definition."""
    assert cfg.command is not None

    current = var.commands
    for comp in cfg.command.split("."):
        if not isinstance(current, tuple):
            raise VariantConfigError("Too many command components")

        fields = getattr(current, "_fields")  # type: List[str]
        if comp not in fields:
            raise VariantConfigError(
                "Invalid command component '{comp}', should be one of {fields}".format(
                    comp=comp, fields=" ".join(fields)
                )
            )
        current = getattr(current, comp)

    if not isinstance(current, list):
        fields = getattr(current, "_fields")
        raise VariantConfigError(
            "Incomplete command specification, should continue with one of {fields}".format(
                fields=" ".join(fields)
            )
        )

    return current


def command_run(cfg):
    # type: (Config) -> None
    """Run a distribution-specific command."""
    assert cfg.args is not None

    cmd = command_find(cfg, detect_variant(cfg=cfg)) + cfg.args
    cfg.diag("About to run `{cmd}`".format(cmd=" ".join(cmd)))
    if cfg.noop:
        # Ahhh... we won't have shlex.quote() on Python 2.6, will we?
        print(" ".join(cmd))
        return

    try:
        subprocess.check_call(cmd, shell=False)
    except subprocess.CalledProcessError as err:
        raise VariantFileError("Could not run `{cmd}`: {err}".format(cmd=" ".join(cmd), err=err))


def cmd_command_list(cfg):
    # type: (Config) -> None
    """List the distribution-specific commands."""
    var = detect_variant(cfg=cfg)

    # We only have two levels, right?
    for cat_name, category in (
        (name, getattr(var.commands, name)) for name in sorted(var.commands._fields)
    ):
        for cmd_name, command in (
            (name, getattr(category, name)) for name in sorted(category._fields)
        ):
            if (cat_name, cmd_name) in CMD_LIST_BRIEF:
                command = ["..."]
            print("{cat}.{name}: {cmd}".format(cat=cat_name, name=cmd_name, cmd=" ".join(command)))


def cmd_command_run(cfg):
    # type: (Config) -> None
    """Run a distribution-specific command."""
    try:
        command_run(cfg)
    except VariantError as err:
        print(str(err), file=sys.stderr)
        sys.exit(1)


def cmd_features(_cfg):
    # type: (Config) -> None
    """Display the features supported by storpool_variant."""
    print(
        "Features: repo=0.2 variant={ver} format={f_major}.{f_minor}".format(
            ver=VERSION, f_major=FORMAT_VERSION[0], f_minor=FORMAT_VERSION[1]
        )
    )


def jsonify(obj):
    # type: (Any) -> Any
    """Return a more readable representation of an object."""
    if type(obj).__name__.endswith("Pattern") and hasattr(obj, "pattern"):
        return jsonify(obj.pattern)

    if hasattr(obj, "_asdict"):
        return dict((name, jsonify(value)) for name, value in obj._asdict().items())
    if isinstance(obj, dict):
        return dict((name, jsonify(value)) for name, value in obj.items())

    if isinstance(obj, list):
        return [jsonify(item) for item in obj]

    return obj


def cmd_show(cfg):
    # type: (Config) -> None
    """Display information about a single build variant."""
    assert cfg.command is not None
    build_variants(cfg)
    if cfg.command == "all":
        data = jsonify(
            {
                "format": {
                    "version": {
                        "major": FORMAT_VERSION[0],
                        "minor": FORMAT_VERSION[1],
                    }
                },
                "version": VERSION,
                "variants": VARIANTS,
                "order": [var.name for var in _DETECT_ORDER],
            }
        )
    else:
        if cfg.command == "current":
            var = detect_variant(cfg)  # type: Optional[Variant]
        else:
            var = VARIANTS.get(cfg.command)

        if var is None:
            sys.exit("Invalid build variant '{name}'".format(name=cfg.command))
        data = jsonify(
            {
                "format": {
                    "version": {
                        "major": FORMAT_VERSION[0],
                        "minor": FORMAT_VERSION[1],
                    }
                },
                "version": VERSION,
                "variant": var,
            }
        )
    print(json.dumps(data, sort_keys=True, indent=2))


def base_parser(prog):
    # type: (str) -> Tuple[argparse.ArgumentParser, SubPAction]
    """Build a parser with the options used by all the sp.variant tools."""
    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="verbose operation; display diagnostic output",
    )

    return parser, parser.add_subparsers()


def parse_arguments():
    # type: () -> Tuple[Config, Callable[[Config], None]]
    """Parse the command-line arguments."""
    parser, subp = base_parser(prog="storpool_variant")

    p_cmd = subp.add_parser("command", help="Distribition-specific commands")
    subp_cmd = p_cmd.add_subparsers()

    p_subcmd = subp_cmd.add_parser("list", help="List the distribution-specific commands")
    p_subcmd.set_defaults(func=cmd_command_list)

    p_subcmd = subp_cmd.add_parser("run", help="Run a distribution-specific command")
    p_subcmd.add_argument(
        "-N",
        "--noop",
        action="store_true",
        help="display the command instead of executing it",
    )
    p_subcmd.add_argument("command", type=str, help="The identifier of the command to run")
    p_subcmd.add_argument("args", type=str, nargs="*", help="Arguments to pass to the command")
    p_subcmd.set_defaults(func=cmd_command_run)

    p_cmd = subp.add_parser("detect", help="Detect the build variant for the current host")
    p_cmd.set_defaults(func=cmd_detect)

    p_cmd = subp.add_parser("features", help="Display the features supported by storpool_variant")
    p_cmd.set_defaults(func=cmd_features)

    p_cmd = subp.add_parser("repo", help="StorPool repository-related commands")
    subp_cmd = p_cmd.add_subparsers()

    p_subcmd = subp_cmd.add_parser("add", help="Install the StorPool repository configuration")
    p_subcmd.add_argument(
        "-d",
        "--repodir",
        type=str,
        required=True,
        help="The path to the directory with the repository configuration",
    )
    p_subcmd.add_argument(
        "-t",
        "--repotype",
        type=str,
        default=REPO_TYPES[0].name,
        choices=[item.name for item in REPO_TYPES],
        help="The type of repository to add (default: contrib)",
    )
    p_subcmd.set_defaults(func=cmd_repo_add)

    p_cmd = subp.add_parser("show", help="Display information about a build variant")
    p_cmd.add_argument(
        "name",
        type=str,
        help=(
            "the name of the build variant to query, 'all' for all, or "
            "'current' for the one detected"
        ),
    )
    p_cmd.set_defaults(func=cmd_show)

    args = parser.parse_args()
    if getattr(args, "func", None) is None:
        sys.exit("No command specified")

    return (
        Config(
            args=getattr(args, "args", None),
            command=getattr(args, "command", getattr(args, "name", None)),
            noop=bool(getattr(args, "noop", False)),
            repodir=getattr(args, "repodir", None),
            repotype=next(rtype for rtype in REPO_TYPES if rtype.name == args.repotype)
            if hasattr(args, "repotype")
            else REPO_TYPES[0],
            verbose=args.verbose,
        ),
        args.func,
    )


def main():
    # type: () -> None
    """Main routine: parse options, detect the variant."""
    cfg, func = parse_arguments()
    func(cfg)


if __name__ == "__main__":
    main()
