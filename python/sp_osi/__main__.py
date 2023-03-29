"""StorPool OpenStack integration helper tool.

Detect the currently installed OpenStack version, determine whether
the StorPool driver is up-to-date, and replace it if necessary.
"""

import argparse
import os
import sys

from typing import Callable, Dict, Mapping, Tuple

from sp_variant import variant as spvariant

from . import defs
from . import detect
from . import groups
from . import install
from . import parse
from . import u8loc


def cmd_detect(cfg: defs.Config) -> None:
    """Detect the OpenStack version currently installed."""
    res = detect.detect(cfg)

    print("Found the following OpenStack components:")
    for name in cfg.components:
        data = res.res[name]
        outdated = "out of date!" if data.data.outdated else "ok"
        print(f"{name:20} {data.branch:10} {outdated:20} {data.path}")


def cmd_check(cfg: defs.Config) -> None:
    """Check whether the installed OpenStack files are up to date."""
    res = detect.detect(cfg)
    outdated = [name for name in cfg.components if res.res[name].data.outdated]
    if outdated:
        sys.exit(
            (
                f"The StorPool OpenStack integration is either not installed or "
                f"not up to date for {', '.join(outdated)}"
            )
        )

    print("The StorPool OpenStack integration is installed")


def cmd_install(cfg: defs.Config) -> None:
    """Replace some packaged files with updated StorPool versions."""
    res = detect.detect(cfg)
    for name in cfg.components:
        install.install(cfg, name, res.res[name])


def cmd_uninstall(cfg: defs.Config) -> None:
    """Restore the original OpenStack versions of the replaced files."""
    res = detect.detect(cfg)
    for name in cfg.components:
        install.uninstall(cfg, name, res.res[name])


def cmd_groups(cfg: defs.Config) -> None:
    """Set up groups for the common attached volumes file."""
    osgrp = groups.setup_group(cfg)
    groups.setup_files(cfg, osgrp)


def cmd_validate(cfg: defs.Config) -> None:
    """Validate the components data read from the file."""
    errors = parse.validate(cfg)
    if errors:
        sys.exit("\n".join(["Errors found in the component definitions:"] + errors))

    print("The components definition file passed the internal checks")


def _dict_union(left: Mapping[str, str], right: Mapping[str, str]) -> Dict[str, str]:
    """Let the right dictionary's elements override those in the left one."""
    res = dict(left)
    res.update(right)
    return res


def parse_args() -> Tuple[defs.Config, Callable[[defs.Config], None]]:
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(prog="sp-openstack")
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="process all known OpenStack components",
    )
    parser.add_argument(
        "-D",
        "--no-divert",
        action="store_true",
        help="do not use dpkg-divert even on Debian/Ubuntu systems",
    )
    parser.add_argument(
        "-N", "--noop", action="store_true", help="no-operation mode; display what would be done"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="verbose operation; display diagnostic output",
    )

    subp = parser.add_subparsers()

    def add_subcommand(
        name: str, handler: Callable[[defs.Config], None], desc: str, *, req_components: bool = True
    ) -> None:
        """Add a subcommand to the parser."""
        subcmd = subp.add_parser(name, help=desc)
        if req_components:
            subcmd.add_argument(
                "components", type=str, nargs="*", help="The OpenStack components to process"
            )
        subcmd.set_defaults(func=handler, req_components=req_components)

    add_subcommand("detect", cmd_detect, "Detect the OpenStack version currently installed")
    add_subcommand("check", cmd_check, "Check whether the StorPool drivers are up to date")
    add_subcommand("install", cmd_install, "Install the StorPool fixes as necessary")
    add_subcommand("groups", cmd_groups, "Set up permissions for the common attached volumes file")
    add_subcommand(
        "validate",
        cmd_validate,
        "Perform some internal checks on the components data file",
        req_components=False,
    )
    add_subcommand(
        "uninstall",
        cmd_uninstall,
        "Restore the original OpenStack files without the StorPool fixes",
    )

    args = parser.parse_args()

    func = getattr(args, "func", None)
    if func is None:
        sys.exit("No subcommand specified")

    cfg = defs.Config(
        all_components=defs.ComponentsTop(components={}),
        components=[],
        no_divert=args.no_divert,
        noop=args.noop,
        utf8_env={},
        variant=spvariant.detect_variant(spvariant.Config(verbose=args.verbose)),
        verbose=args.verbose,
    )

    components = getattr(args, "components", [])
    if not components:
        if getattr(args, "req_components", False):
            if args.all:
                assert not cfg.all_components.components
                assert not cfg.utf8_env
                cfg = cfg._replace(utf8_env=_dict_union(os.environ, u8loc.detect()))
                cfg = cfg._replace(all_components=parse.read_components(cfg))
                components = sorted(cfg.all_components.components.keys())
            else:
                sys.exit("No components specified")
        else:
            components = []

    assert not cfg.components
    cfg = cfg._replace(components=components)

    if not cfg.utf8_env:
        cfg = cfg._replace(utf8_env=_dict_union(os.environ, u8loc.detect()))

    if not cfg.all_components.components:
        cfg = cfg._replace(all_components=parse.read_components(cfg))

    invalid = [item for item in cfg.components if item not in cfg.all_components.components]
    if invalid:
        sys.exit(f"Invalid component name(s) specified: {' '.join(sorted(invalid))}")

    return cfg, func


def main() -> None:
    """Parse command-line options, execute requests."""
    try:
        cfg, func = parse_args()
        func(cfg)  # pylint: disable=not-callable
    except defs.OSIError as err:
        sys.exit(str(err))


if __name__ == "__main__":
    main()
