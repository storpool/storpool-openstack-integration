"""Common definitions for the StorPool OpenStack integration helpers."""

import pathlib
import sys

from typing import Dict, List, NamedTuple, Optional  # noqa: H301

from sp_variant import variant as spvariant

ComponentFile = NamedTuple("ComponentFile", [("sha256", str)])

ComponentVersion = NamedTuple(
    "ComponentVersion",
    [
        ("comment", str),
        ("files", Dict[pathlib.Path, ComponentFile]),
        ("outdated", bool),
    ],
)

Component = NamedTuple(
    "Component",
    [
        ("detect_files_order", List[pathlib.Path]),
        ("branches", Dict[str, Dict[str, ComponentVersion]]),
    ],
)

ComponentsTop = NamedTuple("ComponentsTop", [("components", Dict[str, Component])])


class OSIError(Exception):
    """An error that occurred during the integration setup."""


class OSIEnvError(Exception):
    """An error caused by the OS/platform environment."""


class Config:
    """Runtime configuration for the sp-openstack tool.

    This should be a NamedTuple-derived class, but, well, Python 3.5...
    """

    def __init__(
        self,
        all_components: ComponentsTop,
        components: List[str],
        no_divert: bool,
        noop: bool,
        utf8_env: Dict[str, str],
        variant: spvariant.Variant,
        verbose: bool,
    ) -> None:
        """Store the runtime configuration options."""
        # pylint: disable=too-many-arguments
        self._all_components = all_components
        self._components = components
        self._no_divert = no_divert
        self._noop = noop
        self._utf8_env = utf8_env
        self._variant = variant
        self._verbose = verbose

    def __repr__(self) -> str:
        """Provide a Python-esque representation."""
        # pylint: disable-next=consider-using-f-string
        return (
            "{tname}("
            "all_components={all_components!r}, "
            "components={components!r}, "
            "no_divert={no_divert!r}, "
            "noop={noop!r}, "
            "utf8_env={utf8_env!r}, "
            "variant={variant!r}, "
            "verbose={verbose!r}"
            ")"
        ).format(
            tname=type(self).__name__,
            all_components=self._all_components,
            components=self._components,
            no_divert=self._no_divert,
            noop=self._noop,
            utf8_env=self._utf8_env,
            variant=self._variant,
            verbose=self._verbose,
        )

    def replace(
        self,
        all_components: Optional[ComponentsTop] = None,
        components: Optional[List[str]] = None,
        no_divert: Optional[bool] = None,
        noop: Optional[bool] = None,
        utf8_env: Optional[Dict[str, str]] = None,
        variant: Optional[spvariant.Variant] = None,
        verbose: Optional[bool] = None,
    ) -> "Config":
        """Return a new object with some elements replaced."""
        # pylint: disable=too-many-arguments
        return Config(
            all_components=all_components if all_components is not None else self._all_components,
            components=components if components is not None else self._components,
            no_divert=no_divert if no_divert is not None else self._no_divert,
            noop=noop if noop is not None else self._noop,
            utf8_env=utf8_env if utf8_env is not None else self._utf8_env,
            variant=variant if variant is not None else self._variant,
            verbose=verbose if verbose is not None else self._verbose,
        )

    @property
    def all_components(self) -> ComponentsTop:
        """Get the full list of components read from the definitions file."""
        return self._all_components

    @property
    def components(self) -> List[str]:
        """Get the requested list of components."""
        return self._components

    @property
    def no_divert(self) -> bool:
        """Get the "do not divert" setting."""
        return self._no_divert

    @property
    def noop(self) -> bool:
        """Get the no-operation setting."""
        return self._noop

    @property
    def utf8_env(self) -> Dict[str, str]:
        """Get the UTF-8 environment setting."""
        return self._utf8_env

    @property
    def variant(self) -> spvariant.Variant:
        """Get the OS/distribution variant data."""
        return self._variant

    @property
    def verbose(self) -> bool:
        """Get the verbose setting."""
        return self._verbose

    def diag(self, msg: str) -> None:
        """Output a diagnostic message if requested."""
        if self.verbose:
            print(msg, file=sys.stderr)
