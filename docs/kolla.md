<!--
SPDX-FileCopyrightText: 2015 - 2023  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# Integration with OpenStack Kolla

The [Kolla/kolla-ansible][kolla] project provides container images that
may be used to deploy individual OpenStack services in isolation.
To use StorPool-backed Cinder volumes in such a deployment, some changes
need to be made to the [cinder-volume][kolla-cinder-volume] and
[nova-compute][kolla-nova-compute] Kolla containers.

## Rebuilding the Kolla containers

The StorPool OpenStack integration repository includes the `kolla-rebuild`
command-line tool that uses the `docker-build` utility to install and
configure the StorPool support tools and drivers in the Kolla containers.
The `kolla-rebuild` tool will usually start from the containers provided by
the upstream Kolla project, install the OpenStack integration repository
files inside, then run the `sp-openstack` command-line tool to install
any necessary drivers and prepare any system accounts, directories, and
access permissions.

Note: the `kolla-rebuild` tool currently only handles
the `ubuntu-jammy`/`ubuntu` Kolla containers, and only fetches
the source containers from the Kolla project's
[quay.io/openstack.kolla][quay-io-kolla] repositories.

### Invoking kolla-rebuild

The `kolla-rebuild` tool accepts the following command-line options:

- `--component` / `-c`: specify the name of a component to rebuild.
  This option may be given more than once to specify more than one
  component.
  The only valid values are "cinder-volume" and "nova-compute";
  the default is to rebuild all of these containers.
- `--no-cache`: flush the Docker build cache before rebuilding
- `--pull`: update the upstream container image before rebuilding
- `--quiet` / `-q`: quiet operation; no diagnostic output
- `--release` / `-r`: specify the OpenStack release to fetch and
  rebuild the Kolla containers for.
  The default value is "master".
- `--sp-osi` / `-s`: the storpool-openstack-integration version to use
   instead of the last released one.
   The special value "wip" will cause `kolla-rebuild` to create a new
   tarball containing the last-committed files (the contents of
   the `HEAD` Git ref) in the currently-checked-out copy of
   the StorPool OpenStack integration repository.
   This may be useful for testing new driver versions or new OpenStack
   version definitions in the `defs/components.json` file; note that
   the changes need to be committed to the local Git repository.
- `--tag-suffix` / `-T`: the suffix to add to the built image tag.
  The default is to use a dot, the current date in the `YYYYMMDD` format,
  and an additional ".0" suffix, e.g. `.20230403.0` for April 3rd, 2023.
  This will result in `kolla-rebuild` tagging the build image as e.g.
  `storpool/cinder-volume:zed-ubuntu-jammy.20230403.0`.
  An empty string may be specified to not add anything to the tag of
  the source container image.
- `--topdir` / `-d`: the path to the `storpool-openstack-integration`
  directory where the `kolla-rebuild` tool can find its data files.
  This needs to be specified when `kolla-rebuild` has been installed into
  a virtual environment.

### Running kolla-rebuild in a virtual environment

To use the `kolla-rebuild` tool, several Python libraries must be installed
in a location that the Python interpreter will look for.
One of the ways to do that is to use the Python `venv` module to create
a virtual environment in a new directory:

``` sh
python3 -m venv venv-kolla-rebuild
venv-kolla-rebuild/bin/python3 -m pip install -U pip setuptools
venv-kolla-rebuild/bin/python3 -m pip install /path/to/storpool-openstack-integration
```

After the virtual environment has been prepared, run the `kolla-rebuild` tool
from its executable programs directory, once again specifying the path to
the `storpool-openstack-integration` directory:

``` sh
venv-kolla-rebuild/bin/python3 -m kolla_rebuild -d /path/to/storpool-openstack-integration --help
venv-kolla-rebuild/bin/python3 -m kolla_rebuild -d /path/to/storpool-openstack-integration -r 'zed' --pull
venv-kolla-rebuild/bin/python3 -m kolla_rebuild -d /path/to/storpool-openstack-integration -r 'yoga' --tag-suffix '.sp' -c 'cinder-volume'
```

### Running kolla-rebuild using Tox

The `kolla-rebuild` Tox environment is defined in the `tox.ini` file to
make use of the `tox` tool to create the virtual environment and manage its
dependencies.
If the `KOLLA_REBUILD_ARGS` variable is defined in the environment, its
contents will be passed to `kolla-rebuild` as command-line arguments;
otherwise, default values will be used: "zed" for the OpenStack release
name, and "ubuntu:focal"

``` sh
env KOLLA_REBUILD_ARGS='-r zed -c nova-compute --pull' tox -e 'kolla-rebuild'
```

[kolla]: https://docs.openstack.org/kolla-ansible/latest/user/
[quay-io-kolla]: https://quay.io/organization/openstack.kolla "The Kolla project's quay.io repositories"
[kolla-cinder-volume]: https://quay.io/repository/openstack.kolla/cinder-volume?tab=tags "The Kolla cinder-volume container image"
[kolla-nova-compute]: https://quay.io/repository/openstack.kolla/nova-compute?tab=tags "The Kolla nova-compute container image"
