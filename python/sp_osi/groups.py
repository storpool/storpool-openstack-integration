"""Set up the common attachment database file and spopenstack group."""

import grp
import os
import pathlib
import stat
import subprocess

from . import defs

_GROUP_NAME = "spopenstack"
_DB_FILE = pathlib.Path("/var/spool/openstack-storpool/openstack-attach.json")


def setup_group(cfg: defs.Config) -> grp.struct_group:  # noqa: C901,PLR0912
    """Create the spopenstack group if necessary, add the user accounts to it."""
    print(f"Checking for the {_GROUP_NAME} group")
    try:
        osgrp = grp.getgrnam(_GROUP_NAME)
    except KeyError:
        print("Creating the spopenstack group")
        if cfg.noop:
            print(f"- groupadd --system -- {_GROUP_NAME}")
            osgrp = grp.struct_group((_GROUP_NAME, "x", 616, []))
        else:
            try:
                subprocess.check_call(["groupadd", "--system", "--", _GROUP_NAME], env=cfg.utf8_env)
            except (OSError, subprocess.CalledProcessError) as err:
                raise defs.OSIError(f"Could not create the {_GROUP_NAME} group: {err}") from err

            osgrp = grp.getgrnam(_GROUP_NAME)

    print(f"Got group {osgrp.gr_name}, members {' '.join(sorted(osgrp.gr_mem))}")

    missing = [name for name in cfg.components if name not in osgrp.gr_mem]
    if not missing:
        print("All of the service accounts are already members of this group")
        return osgrp

    all_groups = grp.getgrall()

    for name in missing:
        current = [group.gr_name for group in all_groups if name in group.gr_mem]
        if _GROUP_NAME in current:
            raise defs.OSIError(f"Internal inconsistency: osgrp {osgrp!r}, current {current!r}")

        wanted = ",".join(sorted(current + [_GROUP_NAME]))
        print(f"Setting the group list of {name} to {wanted}")
        if cfg.noop:
            print(f"- usermod -G {wanted} -- {name}")
        else:
            try:
                subprocess.check_call(["usermod", "-G", wanted, "--", name], env=cfg.utf8_env)
            except (OSError, subprocess.CalledProcessError) as err:
                raise defs.OSIError(
                    f"Could not add the {name} account to the {_GROUP_NAME} group: {err}"
                ) from err

    osgrp = grp.getgrnam(_GROUP_NAME)
    if not cfg.noop:
        missing = sorted(name for name in cfg.components if name not in osgrp.gr_mem)
        if missing:
            raise defs.OSIError(
                (
                    f"Some of the service accounts are still not in "
                    f"the {_GROUP_NAME} group: {' '.join(missing)}"
                )
            )
    return osgrp


def _ensure(  # noqa: PLR0912
    cfg: defs.Config,
    osgrp: grp.struct_group,
    path: pathlib.Path,
    pstat: os.stat_result,
    is_dir: bool,
) -> None:
    """Ensure the ownership and permissions of a directory or file."""
    if is_dir:
        if not stat.S_ISDIR(pstat.st_mode):
            raise defs.OSIError(f"Not a directory: {path}")
        mode = 0o770
    else:
        if not stat.S_ISREG(pstat.st_mode):
            raise defs.OSIError(f"Not a regular file: {path}")
        mode = 0o660

    if pstat.st_uid != 0 or pstat.st_gid != osgrp.gr_gid:
        print(f"Setting the ownership of {path}")
        if cfg.noop:
            print(f"- chown 0:{osgrp.gr_gid} -- {path}")
        else:
            try:
                os.chown(path, 0, osgrp.gr_gid)
            except OSError as err:
                raise defs.OSIError(
                    f"Could not set the ownership of {path} to root:{osgrp.gr_name}: {err}"
                ) from err

    if (pstat.st_mode & 0o7777) != mode:
        print(f"Setting the permissions mode of {path} to {mode:03o}")
        if cfg.noop:
            print(f"- chmod {mode:03o} -- {path}")
        else:
            try:
                os.chmod(path, mode)
            except OSError as err:
                raise defs.OSIError(
                    f"Could not set the permissions mode of {path} to {mode:03o}: {err}"
                )


def setup_files(cfg: defs.Config, osgrp: grp.struct_group) -> None:
    """Set up the shared directory."""

    parent = _DB_FILE.parent
    print(f"Examining the {parent} directory")
    try:
        pstat = parent.stat()
    except FileNotFoundError:
        print(f"Creating the {parent} directory")
        if cfg.noop:
            print(f"- mkdir -m 0770 -- {parent}")
            pstat = pathlib.Path("/").stat()
        else:
            parent.mkdir(mode=0o770)
            pstat = parent.stat()

    _ensure(cfg, osgrp, parent, pstat, True)

    print(f"Examining the {_DB_FILE} file")
    try:
        pstat = _DB_FILE.stat()
    except FileNotFoundError:
        print(f"Creating the {_DB_FILE} file")
        if cfg.noop:
            print(f"- write '{{}}' to {_DB_FILE}")
            pstat = pathlib.Path("/etc/passwd").stat()
        else:
            _DB_FILE.write_text("{}\n", encoding="us-ascii")
            pstat = _DB_FILE.stat()

    _ensure(cfg, osgrp, _DB_FILE, pstat, False)
