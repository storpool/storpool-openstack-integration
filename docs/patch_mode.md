# Introduction

The storpool-openstack-integration tool (invoked with `./sp-openstack`)
can now patch the relevant files in a target OpenStack deployment
instead of overwriting them completely. This new "patch-mode" is
available as a subcommand: `./sp-openstack patch ...`

The patch-mode is the default for all components for OpenStack release
2024.1 (Caracal) and beyond.

# Patches

The patches this mode uses are stored in this repository and are
(component + OpenStack release + deployment type)-specific. The patches
for each (component + OpenStack release) are located at
`drivers/<COMPONENT>/openstack/<OPENSTACK_RELEASE>/patches`.

"Deployment type" means whether the directory of the OpenStack component
on disk is a full copy of the contents of the Git repository of the
component, or is just the subdirectory with the Python code. For
example, a Cinder installation from Canonical's Ubuntu Cloud Archive
will result in a directory that is missing directories `doc`,
`releasenotes`, etc. It is just the `cinder` subdirectory from the Git
repository `cinder`. If deploying DevStack, the whole Git repository of
the component will be copied.

A series of patches exists for each deployment type. The
`*.stripped.patch` series is used when just a subset of the Git
repository is detected; the `*.patch` series is used for the whole Git
repository case.

The format of the patches is:

    <PATCH_ORDER>_<CHANGE_NUMBER_IN_OPENDEV>_<PATCH_NUMBER>_<COMMIT_TITLE>.patch
    <PATCH_ORDER>_<CHANGE_NUMBER_IN_OPENDEV>_<PATCH_NUMBER>_<COMMIT_TITLE>.stripped.patch

Examples:

    10_954089_1_StorPool-Fix-typo.patch
    10_954089_1_StorPool-Fix-typo.stripped.patch
    11_954090_1_StorPool-DRY-volumeCreate-in-create_volume.patch

# How It Works

storpool-openstack-integration in patch-mode supports installation and
uninstallation of StorPool's changes.

The most common way to use it is to just run `./sp-openstack patch
install` on the host with the relevant OpenStack components. The tool
will try do detect all components on the host, the OpenStack release
that they are included in, and the deployment type. Based on release and
deployment type, it selects either the `[..]/patches/*.patch` files or
`[..]/patches/*.stripped.patch` files. After that, it will compute the
files that are going to be changed and back them up. Finally, it will
try to apply the patches, in order.

# Examples

Install all StorPool changes for all detected components on this host:

    ./sp-openstack patch install

Install all StorPool changes just for Cinder and os-brick on this host:

    ./sp-openstack patch --component cinder --component os_brick install

Uninstall all StorPool changes just from Nova:

    ./sp-openstack patch --component nova uninstall


# Limitations

## Only One Destination Per Component

If the tool detects multiple installations of a component, it will
refuse to pick a destination for the installation automatically.

## Only One Component Type Per Invocation

Patch-mode supports only one component type per invocation. For example,
the following is allowed:

    ./sp-openstack patch --component nova --component cinder --component os_brick

but the following is not (Cinder provided twice)

    ./sp-openstack patch --component cinder --component cinder --component os_brick
