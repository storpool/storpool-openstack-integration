"""Set up the common attachment database file and spopenstack group."""

import grp
import os
import pathlib
import stat
import subprocess

from . import defs

_GROUP_NAME = "spopenstack"
_DB_FILE = pathlib.Path("/var/spool/openstack-storpool/openstack-attach.json")


def setup_group(cfg: defs.Config) -> grp.struct_group:
    """Create the spopenstack group if necessary, add the user accounts to it."""
    print("Checking for the {group} group".format(group=_GROUP_NAME))
    try:
        osgrp = grp.getgrnam(_GROUP_NAME)
    except KeyError:
        print("Creating the spopenstack group")
        if cfg.noop:
            print("- groupadd --system -- {group}".format(group=_GROUP_NAME))
            osgrp = grp.struct_group((_GROUP_NAME, "x", 616, []))
        else:
            try:
                subprocess.check_call(["groupadd", "--system", "--", _GROUP_NAME], env=cfg.utf8_env)
            except (OSError, subprocess.CalledProcessError) as err:
                raise defs.OSIError(
                    "Could not create the {group} group: {err}".format(group=_GROUP_NAME, err=err)
                ) from err

            osgrp = grp.getgrnam(_GROUP_NAME)

    print(
        "Got group {name}, members {members}".format(
            name=osgrp.gr_name, members=" ".join(sorted(osgrp.gr_mem))
        )
    )

    missing = [name for name in cfg.components if name not in osgrp.gr_mem]
    if not missing:
        print("All of the service accounts are already members of this group")
        return osgrp

    all_groups = grp.getgrall()

    for name in missing:
        current = [group.gr_name for group in all_groups if name in group.gr_mem]
        if _GROUP_NAME in current:
            raise defs.OSIError(
                "Internal inconsistency: osgrp {osgrp!r}, current {current!r}".format(
                    osgrp=osgrp, current=current
                )
            )

        wanted = ",".join(sorted(current + [_GROUP_NAME]))
        print("Setting the group list of {name} to {wanted}".format(name=name, wanted=wanted))
        if cfg.noop:
            print("- usermod -G {wanted} -- {name}".format(wanted=wanted, name=name))
        else:
            try:
                subprocess.check_call(["usermod", "-G", wanted, "--", name], env=cfg.utf8_env)
            except (OSError, subprocess.CalledProcessError) as err:
                raise defs.OSIError(
                    "Could not add the {name} account to the {group} group: {err}".format(
                        name=name, group=_GROUP_NAME, err=err
                    )
                ) from err

    osgrp = grp.getgrnam(_GROUP_NAME)
    if not cfg.noop:
        missing = sorted(name for name in cfg.components if name not in osgrp.gr_mem)
        if missing:
            raise defs.OSIError(
                (
                    "Some of the service accounts are still not in the {group} group: {missing}"
                ).format(group=_GROUP_NAME, missing=" ".join(missing))
            )
    return osgrp


def _ensure(
    cfg: defs.Config,
    osgrp: grp.struct_group,
    path: pathlib.Path,
    pstat: os.stat_result,
    is_dir: bool,
) -> None:
    """Ensure the ownership and permissions of a directory or file."""
    if is_dir:
        if not stat.S_ISDIR(pstat.st_mode):
            raise defs.OSIError("Not a directory: {path}".format(path=path))
        mode = 0o770
    else:
        if not stat.S_ISREG(pstat.st_mode):
            raise defs.OSIError("Not a regular file: {path}".format(path=path))
        mode = 0o660

    if pstat.st_uid != 0 or pstat.st_gid != osgrp.gr_gid:
        print("Setting the ownership of {path}".format(path=path))
        if cfg.noop:
            print("- chown 0:{gid} -- {path}".format(gid=osgrp.gr_gid, path=path))
        else:
            try:
                os.chown(path, 0, osgrp.gr_gid)
            except OSError as err:
                raise defs.OSIError(
                    "Could not set the ownership of {path} to root:{group}: {err}".format(
                        path=path, group=osgrp.gr_name, err=err
                    )
                ) from err

    if (pstat.st_mode & 0o7777) != mode:
        print("Setting the permissions mode of {path} to {mode:03o}".format(path=path, mode=mode))
        if cfg.noop:
            print("- chmod {mode:03o} -- {path}".format(mode=mode, path=path))
        else:
            try:
                os.chmod(path, mode)
            except OSError as err:
                raise defs.OSIError(
                    "Could not set the permissions mode of {path} to {mode:03o}: {err}".format(
                        path=path, mode=0o777, err=err
                    )
                )


def setup_files(cfg: defs.Config, osgrp: grp.struct_group) -> None:
    """Set up the shared directory."""

    parent = _DB_FILE.parent
    print("Examining the {parent} directory".format(parent=parent))
    try:
        pstat = parent.stat()
    except FileNotFoundError:
        print("Creating the {parent} directory".format(parent=parent))
        if cfg.noop:
            print("- mkdir -m 0770 -- {parent}".format(parent=parent))
            pstat = pathlib.Path("/").stat()
        else:
            parent.mkdir(mode=0o770)
            pstat = parent.stat()

    _ensure(cfg, osgrp, parent, pstat, True)

    print("Examining the {path} file".format(path=_DB_FILE))
    try:
        pstat = _DB_FILE.stat()
    except FileNotFoundError:
        print("Creating the {path} file".format(path=_DB_FILE))
        if cfg.noop:
            print("- write '{{}}' to {path}".format(path=_DB_FILE))
            pstat = pathlib.Path("/etc/passwd").stat()
        else:
            _DB_FILE.write_text("{}\n", encoding="us-ascii")
            pstat = _DB_FILE.stat()

    _ensure(cfg, osgrp, _DB_FILE, pstat, False)
