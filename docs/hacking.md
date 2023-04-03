<!--
SPDX-FileCopyrightText: 2022 - 2023  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# Making changes to the StorPool OpenStack integration helper

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
