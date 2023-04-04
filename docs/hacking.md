<!--
SPDX-FileCopyrightText: 2022 - 2023  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# Making changes to the StorPool OpenStack integration helper

## Python versions compatibility

- `sp_osi`: this module still needs to support Python 3.6 so that
  it may be used on e.g. Ubuntu 18.04 (Bionic Beaver) with the system
  Python interpreter.
- the rest of the Python modules should support Python 3.8 so that
  the tools can be run using the current version of the Python
  interpreter bundled with the StorPool software suite

## Using third-party Python libraries

- `sp_osi`: this module needs to be self-contained and only use
  the Python standard library so that it may be used on any system or
  in any virtual environment without the need to install additional
  software
- the rest of the Python tools should use common Python libraries such as
  `click`, `requests`, etc. and also libraries commonly used in other
  StorPool software such as `cfg-diag`, `sp-variant`, or `utf8-locale`

## Adding a new version of a StorPool driver

- Make the changes to the driver file in the drivers/ tree.
- Add a new record to the `defs/components.json` file with
  the new checksum of the driver file; in most cases, mark it as
  non-outdated.
- Make sure to mark any entries referring to the old version of
  the file (with the old checksum) as outdated now.
- Run the internal validation suite: <!-- either `tox -e validate` or
  `nox -s validate` -->
  `tox -e validate`.
- Run the full test suite using Tox: either `tox -p all` or,
  using the [tox-stages utility][tox-stages], `tox-stages run`.
<!--
- Optionally, run the full test suite using Nox: either `nox` or,
  using the [nox-stages utility][nox-stages],
  `nox-stages -p1 -q1 @check @tests`.
  -->

[tox-stages]: https://devel.ringlet.net/devel/test-stages/ "Run Tox tests in groups, stopping on errors"
[nox-stages]: https://gitlab.com/ppentchev/nox-dump "The nox-stages tool from the nox-dump package"
