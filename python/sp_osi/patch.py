"""Patch an OpenStack component with the StorPool patches."""
import argparse
import json
import logging
import logging.handlers
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from . import detect
from . import divert


try:
    from pbr import version as pbr_version  # type: ignore[import-not-found]
except ModuleNotFoundError:
    pbr_version = None  # pylint: disable=invalid-name

SP_BACKUP_SUFFIX = ".sp-backup"
SP_BACKUP_NONEXIST_SUFFIX = ".sp-backup-nonexist"
LOG = logging.getLogger(__name__)

DETECT_FILES = {
    "cinder": [
        pathlib.Path("image/cache.py"),
        pathlib.Path("interface/volume_driver.py"),
        pathlib.Path("tests/unit/image/test_cache.py"),
        pathlib.Path("tests/unit/volume/drivers/test_storpool.py"),
        pathlib.Path("tests/unit/volume/flows/test_create_volume_flow.py"),
        pathlib.Path("volume/driver.py"),
        pathlib.Path("volume/drivers/storpool.py"),
        pathlib.Path("volume/flows/manager/create_volume.py"),
        pathlib.Path("volume/manager.py"),
    ],
    "nova": [
        pathlib.Path("conf/libvirt.py"),
        pathlib.Path("tests/fixtures/libvirt_data.py"),
        pathlib.Path("tests/unit/virt/libvirt/test_config.py"),
        pathlib.Path("virt/libvirt/config.py"),
        pathlib.Path("virt/libvirt/driver.py"),
        pathlib.Path("virt/libvirt/volume/volume.py"),
    ],
    "os_brick": [
        pathlib.Path("initiator/connectors/fibre_channel.py"),
        pathlib.Path("initiator/connectors/storpool.py"),
    ],
}


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


def parse_components(
    components: Optional[List[str]],
) -> List[Tuple[str, Optional[str], Optional[str]]]:
    """Parse the list of provided components into a list of (component,release,path) tuples."""
    if components is None:
        components = sorted(DETECT_FILES.keys())

    comps: List[Tuple[str, Optional[str], Optional[str]]] = []
    for comp in components:
        elems = comp.split(",", maxsplit=2)
        parts = [e if e else None for e in elems]
        parts += [None, None, None][: 3 - len(parts)]
        comps.append(parts)  # type: ignore[arg-type]

    components_error = False
    comp_names = {}
    for component, release, path in comps:
        if component in comp_names:
            LOG.error("This component type has already been provided: %s", component)
            components_error = True
            continue
        comp_names[component] = 1
        if component is None:
            LOG.error("Please provide a name for component: %s", (component, release, path))
            components_error = True
    if components_error:
        sys.exit(1)

    return comps


def handle_provided_component_info(
    components: List[Tuple[str, Optional[str], Optional[str]]]
) -> Tuple[Dict[Any, Any], bool]:
    """Create the targets structure from the component information from the CLI."""
    targets: Dict[Any, Any] = {}

    needs_search = False
    for component, required_release, required_path in components:
        targets[component] = {}
        if required_release is not None:
            LOG.info("Provided OpenStack release %s for component %s", required_release, component)
            targets[component]["release"] = required_release
        if required_path is not None:
            LOG.info("Provided path %s for component %s", required_path, component)
            targets[component]["destinations"] = [pathlib.Path(required_path)]
        else:
            needs_search = True

    return targets, needs_search


def find_components_for_uninstall(  # noqa: C901
    components: List[Tuple[str, Optional[str], Optional[str]]]
) -> Dict[Any, Any]:
    """Find components in Python paths or use the ones provided from the CLI."""
    targets, needs_search = handle_provided_component_info(components)

    if needs_search:
        paths = detect.get_python_paths()

        LOG.info("Will look for components: %s", components)
        LOG.info("Will search these paths:")
        for path in paths:
            LOG.info("  %s", path)

        for path in paths:
            LOG.debug("  Inspecting %s", path)

            for component, _, required_path in components:
                if required_path is not None:
                    LOG.debug(
                        "  Uninstall path provided for component %s: %s", component, required_path
                    )
                    continue

                LOG.debug("    Looking for %s", component)

                if (dest := path.joinpath(component)).is_dir():
                    LOG.debug("      Found: %s", dest)

                    if component not in targets:
                        targets[component] = {}
                    if "destinations" not in targets[component]:
                        targets[component]["destinations"] = []

                    targets[component]["destinations"].append(dest)

    LOG.info("Found the following components:")
    for component, destinations in targets.items():
        LOG.info("  %s:", component)
        for key, val in destinations.items():
            LOG.info("    %s: %s", key, val)

    return targets


def find_components(  # noqa: C901, PLR0912
    components: List[Tuple[str, Optional[str], Optional[str]]]
) -> Dict[Any, Any]:
    # pylint: disable=too-many-branches
    """Find components in Python paths or use the ones provided from the CLI."""
    targets, needs_search = handle_provided_component_info(components)

    if needs_search:  # pylint: disable=too-many-nested-blocks
        paths = detect.get_python_paths()

        LOG.info("Will look for components: %s", components)
        LOG.info("Will search these paths:")
        for path in paths:
            LOG.info("  %s", path)

        versions = {}
        with pathlib.Path("drivers/versions.json").open(encoding="UTF-8") as versions_file:
            versions = json.load(versions_file)

        for path in paths:
            LOG.debug("  Inspecting %s", path)

            for component, required_release, _ in components:
                LOG.debug("    Looking for %s", component)

                if (dest := path.joinpath(component)).is_dir():
                    LOG.debug("      Found: %s", dest)

                    if component not in targets:
                        targets[component] = {}
                    if "destinations" not in targets[component]:
                        targets[component]["destinations"] = []

                    targets[component]["destinations"].append(dest)

                    if required_release is not None:
                        LOG.info(
                            "Skip detecting the OpenStack release of %s"
                            " because it was provided: %s",
                            component,
                            required_release,
                        )
                        continue

                    if pbr_version is not None:
                        targets[component]["version"] = str(pbr_version.VersionInfo(component))
                        for release, vers in versions[component].items():
                            if targets[component]["version"] in vers:
                                LOG.info("Detected OpenStack release of %s: %s", component, release)
                                targets[component]["release"] = release
                                break

    LOG.info("Found the following components:")
    for component, destinations in targets.items():
        LOG.info("  %s:", component)
        for key, val in destinations.items():
            LOG.info("    %s: %s", key, val)

    return targets


def detect_type(component: str, destination: pathlib.Path) -> bool:
    """Detect if the destination is a copy of the whole Git repository of the component."""
    missing = False
    for file in DETECT_FILES[component]:
        the_file = destination.joinpath(file)
        if not the_file.is_file():
            LOG.debug("File %s is missing from the destination %s", the_file, destination)
            missing = True

    if not missing:
        LOG.info(
            "The destination %s is not a full copy of the Git repository of component %s",
            destination,
            component,
        )
        return False

    missing = False
    for file in DETECT_FILES[component]:
        dest_file = destination.joinpath(pathlib.Path(component)).joinpath(file)
        if not dest_file.is_file():
            LOG.debug("File %s is missing from the destination %s", dest_file, destination)
            missing = True

    if missing:
        LOG.error("Could not find the component %s at destination: %s", component, destination)
        sys.exit(1)

    LOG.info(
        "The destination %s is a full copy of the Git repository of component %s",
        destination,
        component,
    )
    return True


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


def ensure_destinations_exist(components: Dict[Any, Any]) -> None:
    """Check that the destination for each component exists."""
    missing = False
    for name, component in components.items():
        if not component["destination"].exists() or not component["destination"].is_dir():
            LOG.error(
                "Component %s has a destination that does not exist: %s",
                name,
                component["destination"],
            )
            missing = True
    if missing:
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


def ensure_only_one_destination_per_component(
    components: List[str], destinations: Dict[str, Any]
) -> None:
    """Check that there is only one destination path per component."""
    LOG.info("Checking if each component is found in exactly one destination")
    for component in components:
        if len(destinations[component]["destinations"]) != 1:
            LOG.error(
                "Component %s found at more than one destination: %s",
                component,
                destinations[component],
            )
            sys.exit(1)


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


def do_uninstall(destination: pathlib.Path) -> None:
    """Actually do the uninstall."""
    ensure_no_sp_diversions(destination)

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


def uninstall(args: argparse.Namespace) -> None:
    """Scan the destination for backups and move them to their original paths."""
    verbose = args.verbose
    configure_logging(verbose)

    comps = parse_components(args.component)

    components = find_components_for_uninstall(comps)
    ensure_only_one_destination_per_component([c[0] for c in comps], components)

    for component in components.values():
        component["destination"] = component["destinations"][0]

    ensure_destinations_exist(components)

    for component in components.values():
        do_uninstall(component["destination"])


def install(args: argparse.Namespace) -> None:
    """Install the StorPool changes via patching."""
    verbose = args.verbose
    configure_logging(verbose)

    comps = parse_components(args.component)

    ensure_tools_exist()

    components = find_components(comps)
    ensure_only_one_destination_per_component([c[0] for c in comps], components)

    for component in components.values():
        component["destination"] = component["destinations"][0]

    ensure_destinations_exist(components)

    for component in components.values():
        ensure_no_sp_diversions(component["destination"])

        sp_backups: List[pathlib.Path] = []
        find_with_suffix(component["destination"], SP_BACKUP_SUFFIX, sp_backups)
        if sp_backups:
            LOG.info(
                "StorPool backups detected, will run uninstall first at: %s",
                component["destination"],
            )
            do_uninstall(component["destination"])
        ensure_no_sp_backups(component["destination"])

    for name, component in components.items():
        patch_folder = pathlib.Path(f"drivers/{name}/openstack/{component['release']}/patches")
        is_full_repo = detect_type(name, component["destination"])
        patches = collect_patches(patch_folder, is_full_repo)
        files_to_be_changed = compute_files_to_be_changed(
            patches, component["destination"], is_full_repo
        )
        ensure_files_are_not_symlinks(files_to_be_changed)
        backup_original_files(files_to_be_changed)
        do_patch(patches, component["destination"], is_full_repo)
