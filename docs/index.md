<!--
SPDX-FileCopyrightText: 2015 - 2023  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# StorPool Integration with OpenStack

\[[Home][storpool-sp-osi] | [GitHub][github] | [Changelog][github-changelog]\]

## Overview

Most of the time, the the StorPool drivers in the upstream OpenStack Git
repositories (Cinder, Nova, os-brick) do not all contain the latest
bugfixes and features that the StorPool team has developed.
This may happen for several reasons: recent fixes and features have not
yet been merged, others have not yet been backported to previous releases,
some are considered too intrusive to backport, etc.
The StorPool OpenStack Integration repository contains the latest versions
of the StorPool Cinder backend driver, as well as several tools to help with
configuring a deployed OpenStack cluster to use StorPool-backed volumes or
assisting an OpenStack deployment system to configure a new cluster
straight away.

## Sections

- [A brief introduction to StorPool](storpool.md)
- [Configure OpenStack](configure.md)
- [OpenStack Kolla integration](kolla.md)

[github]: https://github.com/storpool/storpool-openstack-integration "The StorPool OpenStack integration GitHub repository"
[github-changelog]: https://github.com/storpool/storpool-openstack-integration/blob/master/docs/changes.md "The changelog file"
[storpool-sp-osi]: https://repo.storpool.com/public/doc/storpool-openstack-integration/ "The StorPool OpenStack integration documentation"
