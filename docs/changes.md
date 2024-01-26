<!--
SPDX-FileCopyrightText: 2022 - 2024  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# Change log for the StorPool OpenStack integration

## [Unreleased]

### Additions

- Glance drivers:
    - Bobcat:
        - recognize 27.0.0.0rc2
- kolla-rebuild:
    - also rebuild the `glance-api` container, since Glance also needs
      the StorPool API bindings and OpenStack helper modules installed

## [2.2.1] - 2024-01-16

### Fixes

- documentation:
    - document the `--topdir` / `-d` option to `kolla-rebuild` and
      reflect it in the instructions for running the tool from
      a virtual environment

## [2.2.0] - 2024-01-16

### Fixes

- Cinder drivers:
    - Antelope:
        - change the entry version: this is 22.0.0, no longer a snapshot
- Nova drivers:
    - Antelope:
        - change the entry version: this is 27.0.0, no longer a snapshot
- build infrastructure:
    - note the documentation URLs in the project metadata
    - install the `kolla_rebuild` module and the `kolla-rebuild` executable,
      also updating the requirements files
- documentation:
    - fix a couple of duplicate words as spotted by the `spellintian` tool

### Additions

- Cinder drivers:
    - Bobcat:
        - recognize 23.0.0 and add the StorPool updates
- Nova drivers:
    - Bobcat:
        - recognize 28.0.0, 28.0.1, and a couple of snapshots
    - Antelope:
        - recognize some more upstream snapshots
    - Zed:
        - recognize a couple of snapshots
    - Yoga:
        - recognize 25.2.1
- os-brick:
    - add it as a new component
    - Bobcat:
        - recognize 6.4.0 and add the StorPool updates
    - Antelope:
        - recognize 6.2.0 and add the StorPool updates
    - Zed:
        - recognize a snapshot and add the StorPool updates
    - Yoga:
        - recognize 5.2.2 (both upstream and the Ubuntu Cloud Archive version)
          and add the StorPool updates
- documentation:
    - hacking:
        - add a couple of words about the MkDocs-based documentation
        - add a brief section about adding a detect-only component entry
- kolla-rebuild:
    - handle containers that need more than one component updated
      (e.g. with Nova we also need to update the os-brick drivers)
    - use the canonical 2023.1 name for Antelope and 2023.2 for Bobcat
      but still recognize "antelope" and "bobcat" as aliases
    - add the `-d` / `--topdir` option to specify the path to
      the `storpool-openstack-integration` directory so that `kolla-rebuild`
      may be invoked directly from a virtual environment

### Other changes

- testing infrastructure:
    - update the Tox configuration file to the 4.x format
- documentation:
    - kolla: update the documentation for using a virtual environment
    - use MkDocs 1.5 and mkdocstrings 0.24 with no changes
- sp-osi:
    - update the bundled copy of sp-variant to version 3.4.2
- kolla-rebuild:
    - catch up with the changes in the changelog formatting
    - rename "component" to the more specific "container"

## [2.1.0] - 2023-04-04

### Fixes

- build infrastructure:
    - correct the requirements path in the pyproject.toml file
    - correct the sp-osi requirements, only leave the ones that are
      relevant to sp\_osi itself
    - use the canonical names for the cfg-diag and sp-variant libraries
- sp-osi:
    - catch more exceptions when parsing the components file
    - various minor fixes and refactoring as suggested by ruff

### Additions

- documentation:
    - convert the `CHANGES.md`, `HACKING.md`, and `README.md` files
      into a MkDocs-based documentation site within the `docs/` directory
    - add a brief overview blurb to the documentation main page
- sp-openstack:
    - include a simplified version of the `utf8-locale` library to
      make reading commands output a bit more reliable
- kolla-rebuild:
    - new tool for rebuilding the upstream Kolla container images
      (the `cinder-volume` and `nova-compute` ones) to support the StorPool
      Cinder backend
- testing infrastructure:
    - add a Python unit test suite
    - add separate environments for running the command-line tools
      other than sp-openstack itself
    - run ruff 0.0.260 with most of its checks enabled and satisfied
    - run ruff's isort emulation in a separate Tox environment

### Other changes

- Drop the drivers for OpenStack releases earlier than Victoria;
  the Kilo through Queens drivers are of historical value only at
  this point, and they were not described in the components file or
  handled by the new `sp-openstack` tool anyway
- Switch to SPDX license identifiers
- documentation:
    - README: split this long file into several documentation sections
    - configure: drop some outdated information
    - hacking: minor updates:
        - running the full test suite is not optional
        - refer to `tox-stages` instead of `tox-delay`
        - temporarily comment out the Nox parts
- sp-openstack:
    - sort the import section, fold `typing` into the main group
- chroot-test:
    - turn this file into a full-fledged Python module (not installed,
      only used for running the program itself)
    - simplify the file structure using deferred type annotations
    - various minor fixes and refactoring as suggested by ruff
    - sort the import section, fold `typing` into the main group

## [2.0.5] - 2023-03-09

- correct the 2.0.4 changelog entry: it is about Nova, not Cinder

## [2.0.4] - 2023-03-09

- Nova drivers:
    - Zed:
        - recognize a Zed branch snapshot

## [2.0.3] - 2023-03-09

- Cinder drivers:
    - Zed:
        - recognize and support the 21.1.0 upstream version
    - Antelope:
        - recognize and support a master branch snapshot
- Nova drivers:
    - Zed:
        - recognize the 26.1.0 upstream version
    - Antelope:
        - recognize a master branch snapshot
- testing infrastructure:
    - add the tool.test-stages.stages pyproject setting for the tox-stages tool
    - update to cfg\_diag 0.4.x and inherit from the correct base class in
      the chroot\_test tool
    - update to pylint 2.16.x and define our own exception class in
      the Nox file
    - use black 23.x, flake8 6.x, mypy 1.x, and utf8-locale 1.x with
      no code changes

## [2.0.2] - 2023-03-01

- Cinder drivers:
    - Victoria:
        - add a fix for always detaching Glance image volumes after conversions
        - implement the "revert a volume to a snapshot" Cinder feature
    - Wallaby:
        - add a fix for always detaching Glance image volumes after conversions
        - implement the "revert a volume to a snapshot" Cinder feature
        - drop the `copy_image_to_volume()` and `copy_volume_to_image()` methods
        - fix retyping a volume to another StorPool template
        - add iSCSI attach support
        - add multipath support when attaching a volume via iSCSI
    - Xena:
        - implement the "revert a volume to a snapshot" Cinder feature
        - drop the `copy_image_to_volume()` and `copy_volume_to_image()` methods
        - fix retyping a volume to another StorPool template
        - add multipath support when attaching a volume via iSCSI
        - recognize the 19.1.1 upstream and Ubuntu cloud archive version
    - Yoga:
        - implement the "revert a volume to a snapshot" Cinder feature
        - drop the `copy_image_to_volume()` and `copy_volume_to_image()` methods
        - fix retyping a volume to another StorPool template
        - add multipath support when attaching a volume via iSCSI
- Nova drivers:
    - Wallaby:
        - recognize the 23.2.2 upstream and Ubuntu cloud archive version
    - Xena:
        - recognize the 24.2.0 upstream and Ubuntu cloud archive version
    - Yoga:
        - recognize the 25.1.0 upstream and Ubuntu cloud archive version
- documentation:
    - add the "our Cinder driver supports trim/discard operations" flag to
      the Cinder backend configuration example
- sp-openstack:
    - convert an error object to a string before passing it to `sys.exit()`
- build infrastructure:
    - add setuptools infrastructure for use with setuptools version 61 or later
    - add the py.typed marker file
- testing infrastructure:
    - drop the "flake8 + hacking" test environment
    - add version constraints to the dependencies in all test environments
    - add the "validate" test environment to make sure the components.json file
      remains sane
    - when validating the components.json file, make sure each outdated version
      has exactly one non-outdated version in the same component and branch to
      update to
    - add Nox test definitions
    - move the lists of test environment dependencies to separate files to
      help Nox and Tox use the same ones
    - do not build diagnostic messages unless we need to (use lambdas in diag calls)
- start a HACKING.md how-to document for developers

## [2.0.1] - 2022-08-05

- Cinder drivers:
    - Wallaby:
        - add an entry for the StorPool updated driver for the 18.1.0 Ubuntu
          cloud archive version
        - recognize the 18.2.1 upstream version
        - bump the StorPool Cinder driver version so that it is higher than
          the upstream one
    - Xena:
        - add iSCSI support to the StorPool driver
    - Yoga:
        - recognize the 20.0.0 and 20.0.1 upstream versions
        - install an updated driver with iSCSI support
- Glance drivers:
    - Yoga:
        - recognize the 24.0.0 upstream version
- Nova drivers:
    - Victora:
        - recognize the 22.4.0 upstream version
        - recognize the 22.4.0 Ubuntu cloud archive version
    - Wallaby:
        - recognize the 23.2.0 and 23.2.1 upstream versions
        - recognize the 23.2.1 Ubuntu cloud archive version
    - Xena:
        - recognize the 24.1.0 and 24.1.1 upstream versions
        - recognize the 24.1.1 Ubuntu cloud archive version
    - Yoga:
        - recognize the 25.0.0 upstream version
        - recognize the 25.0.0 Ubuntu cloud archive version

## [2.0.0] - 2022-05-19

- reimplement the `sp-openstack` tool in Python 3.6 or higher
- let `sp-openstack` use the `dpkg-divert` tool on Debian/Ubuntu systems
  (unless the `-D` / `--no-divert` command-line option is specified) to
  make sure the local changes are not lost if the OpenStack packages are
  upgraded
- add the "uninstall" command to the `sp-openstack` tool
- detect the Xena release of OpenStack
- add some StorPool driver fixes for the OpenStack Victoria, Wallaby, and
  Xena releases:
    - drop `_attach_volume()`, `_detach_volume()`, and `backup_volume()`
    - reimplement `create_cloned_volume()` in a much more efficient way
    - implement `clone_image()`

## [1.5.0] - 2021-12-14

- add the "groups" command to the `sp-openstack` tool to only check, create,
  and set up the "spopenstack" group and the service accounts' membership,
  as well as the `/var/spool/storpool-spopenstack/` directory
- detect the Rocky, Stein, Train, Victoria, and Wallaby releases of OpenStack
- detect and set up the groups for Glance, too

## [1.4.0] - 2018-06-05

- Note that the StorPool drivers have been included in the Queens release.
- Detect the Queens release of OpenStack and (hopefully) just say that
  the StorPool integration is installed already.

## [1.3.0] - 2017-09-18

- Add the Pike Cinder, Nova, and os-brick drivers.
- Properly capitalize the 1.2.0 changelog entry.
- Add the `sp-image-to-volume` tool to save a Glance image to a StorPool volume
  and its manual page.

## [1.2.0] - 2017-08-06

- Add the `-T txn-module` option for use with the txn-install tool.

## [1.1.1] - 2017-08-06

- Add the sp-openstack.1 manual page.
- Look for the Python modules path in a way compatible with Python 3.

## [1.1.0] - 2017-07-31

- Add the Ocata Cinder volume driver and Nova attachment driver.
- Add the Newton and Ocata os-brick connector driver.
- Add the capability to make different changes to the same file for
  different OpenStack releases.
- Remove the "probably unaligned" warnings from the documentation of
  the "storpool volume list" and "storpool volume status" checks, since
  the StorPool CLI tool aligns the output in recent versions.
- Let the documentation use the "openstack" client tool where possible.

## [1.0.0] - 2016-09-07

- Update the Mitaka os-brick connector.
- Update the Liberty and Mitaka Cinder volume drivers.
- Fix the detection of Nova Liberty vs Mitaka.
- Drop support for the Juno and Kilo releases of OpenStack.

## [0.2.0] - 2016-07-26

- Allow the owner and group of the /var/spool/openstack-storpool/
  shared state directory to be overridden using the -u and -g
  options of the sp-openstack tool.

## [0.1.0] - 2016-07-26

- Initial public release.

[Unreleased]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.2.1...master
[2.2.1]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.2.0...release/2.2.1
[2.2.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.1.0...release/2.2.0
[2.1.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.0.5...release/2.1.0
[2.0.5]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.0.4...release/2.0.5
[2.0.4]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.0.3...release/2.0.4
[2.0.3]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.0.2...release/2.0.3
[2.0.2]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.0.1...release/2.0.2
[2.0.1]: https://github.com/storpool/storpool-openstack-integration/compare/release/2.0.0...release/2.0.1
[2.0.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/1.5.0...release/2.0.0
[1.5.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/1.4.0...release/1.5.0
[1.4.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/1.3.0...release/1.4.0
[1.3.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/1.2.0...release/1.3.0
[1.2.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/1.1.1...release/1.2.0
[1.1.1]: https://github.com/storpool/storpool-openstack-integration/compare/release/1.1.0...release/1.1.1
[1.1.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/1.0.0...release/1.1.0
[1.0.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/0.2.0...release/1.0.0
[0.2.0]: https://github.com/storpool/storpool-openstack-integration/compare/release/0.1.0...release/0.2.0
[0.1.0]: https://github.com/storpool/storpool-openstack-integration/releases/tag/release%2F0.1.0
