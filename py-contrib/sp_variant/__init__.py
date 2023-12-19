# SPDX-FileCopyrightText: 2021 - 2023  StorPool <support@storpool.com>
# SPDX-License-Identifier: BSD-2-Clause
"""Detect the Linux distribution and version for the StorPool build system.

The ``sp-variant`` library is mainly useful within the StorPool internal
build and QA environment, as well as the first step of installations on
end-user systems. It examines several files and tries to determine what
distribution and what version it is running on.
"""
