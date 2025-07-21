"""Patch an OpenStack component with the StorPool patches."""
import argparse
import logging
import logging.handlers
import pathlib
import shutil
import subprocess
import sys
from typing import List, Tuple

from . import defs
from . import divert


SP_BACKUP_SUFFIX = ".sp-backup"
SP_BACKUP_NONEXIST_SUFFIX = ".sp-backup-nonexist"
LOG = logging.getLogger(__name__)


def configure_logging(verbose: bool) -> None:  # noqa: FBT001
    """Configure logging to stdout."""
    if logging.getLogger().hasHandlers():
        return
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if verbose:
        root_logger.setLevel(logging.DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)


def find_with_suffix(destination: pathlib.Path, suffix: str, lst: List[pathlib.Path]) -> None:
    """Find all files in a directory that end in the provided suffix."""
    for path in destination.iterdir():
        if path.is_dir():
            find_with_suffix(path, suffix, lst)
        elif path.name.endswith(suffix):
            lst.append(path)


def detect_type(destination: pathlib.Path) -> bool:
    """Detect if the destination is a copy of the whole Git repository of the component."""
    only_in_repo: List[Tuple[str, str]] = [
        ("doc", "dir"),
        (".gitignore", "file"),
        ("LICENSE", "file"),
        ("tox.ini", "file"),
    ]

    is_full = True
    for elem in only_in_repo:
        if not (
            (elem[1] == "file" and destination.joinpath(elem[0]).is_file())
            or (elem[1] == "dir" and destination.joinpath(elem[0]).is_dir())
        ):
            is_full = False
            break

    LOG.info("Is the destination %s a full copy of the Git repository?: %s", destination, is_full)

    return is_full


def ensure_tools_exist() -> None:
    """Confirm that 'patch' and 'lsdiff' installed or fail.

    These tools are needed for the patch procedure to work. Usually patch is in package patch, and
    lsdiff in patchutils
    """
    for tool in ["patch", "lsdiff"]:
        try:
            subprocess.run(["which", tool], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            LOG.exception("The required tool '%s' cannot be found", tool)
            sys.exit(1)


def ensure_no_sp_backups(destination: pathlib.Path) -> None:
    """Check if there are files with the SP_BACKUP_SUFFIX suffix and do not continue."""
    sp_backups: List[pathlib.Path] = []
    find_with_suffix(destination, SP_BACKUP_SUFFIX, sp_backups)
    if sp_backups:
        LOG.error(
            "The destination %s contains StorPool backups. Please run uninstall first:", destination
        )
        for backup in sp_backups:
            LOG.error("  %s", backup)
        sys.exit(1)
    LOG.info("No StorPool backups detected at %s, can continue", destination)


def ensure_no_sp_diversions(destination: pathlib.Path) -> None:
    """Check if there are backup files in the form of package diversions/renames."""
    sp_diversions: List[pathlib.Path] = []
    find_with_suffix(destination, divert.DIVERSION_SUFFIX, sp_diversions)
    if sp_diversions:
        LOG.error(
            "The destination %s contains StorPool diversions."
            " Please run uninstall in non-patch mode first:",
            destination,
        )
        for diversion in sp_diversions:
            LOG.error("  %s", diversion)
        sys.exit(1)
    LOG.info("No StorPool diversions detected at %s, can continue", destination)


def ensure_files_are_not_symlinks(files: List[pathlib.Path]) -> None:
    """Check if all the files we are going to manipulate are regular files."""
    not_reqular_files: List[pathlib.Path] = []
    for file in files:
        if not file.is_file() and file.is_symlink():
            not_reqular_files.append(file)

    if not_reqular_files:
        LOG.info("Aborting; target files that are going to be changed are not regular files:")
        for file in not_reqular_files:
            LOG.info("  %s", file)
        sys.exit(1)

    LOG.info("All files that are going to be changed are regular files")


def backup_original_files(files: List[pathlib.Path]) -> None:
    """Copy the given files at file.SP_BACKUP_SUFFIX."""
    for file in files:
        if file.exists():
            backup_file = f"{file.absolute()}{SP_BACKUP_SUFFIX}"
            LOG.info("Backing up %s to %s", file.absolute(), backup_file)
            shutil.copy2(file.absolute(), backup_file)
        else:
            backup_file = f"{file.absolute()}{SP_BACKUP_NONEXIST_SUFFIX}"
            LOG.info("Non-existent file %s marked as such at %s", file, backup_file)
            pathlib.Path(backup_file).touch()


def collect_patches(
    patch_folder: pathlib.Path, full_repo: bool  # noqa: FBT001
) -> List[pathlib.Path]:
    """Find the patches to apply depending on the destination."""
    patches: List[pathlib.Path] = []

    if full_repo:
        LOG.debug("Collecting all full patches")
    else:
        LOG.debug("Collecting all stripped patches")

    for file in patch_folder.iterdir():
        if full_repo ^ file.name.endswith(".stripped.patch"):
            LOG.debug("Found patch: %s", file.absolute())
            patches.append(file.absolute())

    patches.sort()
    LOG.info("Will apply the following patches in order:")
    for patch in patches:
        LOG.info("  %s", patch)

    return patches


def compute_files_to_be_changed(
    patches: List[pathlib.Path], destination: pathlib.Path, is_full_repo: bool  # noqa: FBT001
) -> List[pathlib.Path]:
    """Generate the list of files that will be modified by the patching procedure."""
    strip_level = 1
    if not is_full_repo:
        strip_level = 2
    files = set()
    for patch in patches:
        lsdiff_out = (
            subprocess.run(
                ["lsdiff", "--strip", f"{strip_level}", patch], check=True, capture_output=True
            )
            .stdout.decode("UTF-8")
            .splitlines()
        )
        LOG.debug("Patch %s changes the following files:", patch)
        for changed_file in lsdiff_out:
            fname = destination.joinpath(pathlib.Path(changed_file))
            LOG.debug("  %s", fname)
            files.add(fname)
    files_to_be_changed = sorted(files)

    LOG.info("The following files are going to be changed by the patches:")
    for file in files_to_be_changed:
        LOG.info("  %s", file)

    return files_to_be_changed


def do_patch(
    patches: List[pathlib.Path], destination: pathlib.Path, is_full_repo: bool  # noqa: FBT001
) -> None:
    """Apply the list of patches to the destination."""
    strip_level = 1
    if not is_full_repo:
        strip_level = 2
    for patch in patches:
        LOG.info("Applying patch %s to %s", patch, destination)
        res = subprocess.run(
            [
                "patch",
                "--no-backup-if-mismatch",
                f"--strip={strip_level}",
                f"--input={patch}",
                f"--directory={destination}",
            ],
            check=True,
            capture_output=True,
        )
        LOG.debug("Result:")
        LOG.debug("  stdout:")
        for line in res.stdout.decode("UTF-8").splitlines():
            LOG.debug("    %s", line)
        LOG.debug("  stderr:")
        for line in res.stderr.decode("UTF-8").splitlines():
            LOG.debug("    %s", line)


def uninstall(args: argparse.Namespace) -> None:
    """Scan the destination for backups and move them to their original paths."""
    verbose = args.verbose
    destination = pathlib.Path(args.component_destination).resolve()

    configure_logging(verbose)

    sp_backups: List[pathlib.Path] = []
    find_with_suffix(destination, SP_BACKUP_SUFFIX, sp_backups)
    sp_nonexistent: List[pathlib.Path] = []
    find_with_suffix(destination, SP_BACKUP_NONEXIST_SUFFIX, sp_nonexistent)

    if not sp_backups and not sp_nonexistent:
        LOG.info("No StorPool backup files detected, exiting")
        return

    LOG.info("Found the following files that will be restored to their original paths:")
    for backup in sp_backups:
        LOG.info("  %s", backup)

    for backup in sp_backups:
        current_file = pathlib.Path(str(pathlib.Path(backup.absolute()))[: -len(SP_BACKUP_SUFFIX)])
        LOG.debug("Copying %s to %s", backup, current_file)
        shutil.copy2(backup, current_file)

    for backup in sp_backups:
        LOG.debug("Removing StorPool backup file %s", backup)
        backup.unlink(missing_ok=True)

    LOG.info("Found the following files that will to be removed:")
    for sp_nonexist in sp_nonexistent:
        real_file = pathlib.Path(str(sp_nonexist)[: -len(SP_BACKUP_NONEXIST_SUFFIX)])
        LOG.info("  %s so removing %s", sp_nonexist, real_file)
        real_file.unlink(missing_ok=True)

    for sp_nonexist in sp_nonexistent:
        LOG.debug("Removing StorPool backup file %s", sp_nonexist)
        sp_nonexist.unlink(missing_ok=True)


def install(args: argparse.Namespace) -> None:
    """Install the StorPool changes via patching."""
    verbose = args.verbose
    component = args.component
    openstack_version = defs.OpenStackVersion[args.component_version.upper()]
    destination = pathlib.Path(args.component_destination).resolve()

    configure_logging(verbose)

    ensure_tools_exist()
    ensure_no_sp_diversions(destination)

    sp_backups: List[pathlib.Path] = []
    find_with_suffix(destination, SP_BACKUP_SUFFIX, sp_backups)
    if sp_backups:
        uninstall(args)
    ensure_no_sp_backups(destination)

    patch_folder = pathlib.Path(
        f"drivers/{component}/openstack/{openstack_version.name.lower()}/patches"
    )
    is_full_repo = detect_type(destination)
    patches = collect_patches(patch_folder, is_full_repo)
    files_to_be_changed = compute_files_to_be_changed(patches, destination, is_full_repo)
    ensure_files_are_not_symlinks(files_to_be_changed)
    backup_original_files(files_to_be_changed)
    do_patch(patches, destination, is_full_repo)
