<!--
SPDX-FileCopyrightText: 2015 - 2023  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# StorPool Integration with OpenStack

\[[Home][storpool-sp-osi] | [GitHub][github] | [Changelog][kb-changelog]\]

## Overview

Most of the time, the the StorPool drivers in the upstream OpenStack Git
repositories (Cinder, Nova, os-brick) do not all contain the latest
bug fixes and features that the StorPool team has developed.
This may happen for several reasons: recent fixes and features have not
yet been merged, others have not yet been backported to previous releases,
some are considered too intrusive to backport, and so on.

The StorPool OpenStack Integration repository contains the latest versions
of the StorPool Cinder backend driver, as well as several tools to help with
configuring a deployed OpenStack cluster to use StorPool-backed volumes or
assisting an OpenStack deployment system to configure a new cluster
straight away.

## Sections

For more information see the documentation on the StorPool knowledge base:

- [Release notes][kb-changelog]
- [Configuring OpenStack][storpool-web-configure]
- [OpenStack Kolla integration][storpool-web-kolla]

## Contact

The StorPool OpenStack integration repository is developed by
[StorPool][storpool-support] in [a GitHub repository][github].
This documentation is hosted at [StorPool][storpool-sp-osi].

[github]: https://github.com/storpool/storpool-openstack-integration "The StorPool OpenStack integration GitHub repository"
[kb-changelog]: https://kb.storpool.com/storpool_integrations/OpenStack/changes.html "The changelog file"
[storpool-sp-osi]: https://kb.storpool.com/storpool_integrations/OpenStack/ "The StorPool OpenStack integration documentation"
[storpool-support]: mailto:support@storpool.com "The StorPool team"
[storpool-web-configure]: https://kb.storpool.com/storpool_integrations/OpenStack/configure.html "Configure OpenStack"
[storpool-web-kolla]: https://kb.storpool.com/storpool_integrations/OpenStack/kolla.html "OpenStack Kolla integration"
