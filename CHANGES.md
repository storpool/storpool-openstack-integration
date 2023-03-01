Change log for the StorPool OpenStack integration
=================================================

2.0.2
-----

- Cinder drivers:
    - Victoria:
        - add a fix for always detaching Glance image volumes after conversions
        - implement the "revert a volume to a snapshot" Cinder feature
    - Wallaby:
        - add a fix for always detaching Glance image volumes after conversions
        - implement the "revert a volume to a snapshot" Cinder feature
        - drop the `copy_image_to_volume()` and `copy_volume_to_image()` methods
        - fix retyping a volume to another StorPool template
        - add iSCSI attach support
        - add multipath support when attaching a volume via iSCSI
    - Xena:
        - implement the "revert a volume to a snapshot" Cinder feature
        - drop the `copy_image_to_volume()` and `copy_volume_to_image()` methods
        - fix retyping a volume to another StorPool template
        - add multipath support when attaching a volume via iSCSI
        - recognize the 19.1.1 upstream and Ubuntu cloud archive version
    - Yoga:
        - implement the "revert a volume to a snapshot" Cinder feature
        - drop the `copy_image_to_volume()` and `copy_volume_to_image()` methods
        - fix retyping a volume to another StorPool template
        - add multipath support when attaching a volume via iSCSI
- Nova drivers:
    - Wallaby:
        - recognize the 23.2.2 upstream and Ubuntu cloud archive version
    - Xena:
        - recognize the 24.2.0 upstream and Ubuntu cloud archive version
    - Yoga:
        - recognize the 25.1.0 upstream and Ubuntu cloud archive version
- documentation:
    - add the "our Cinder driver supports trim/discard operations" flag to
      the Cinder backend configuration example
- build infrastructure:
    - add setuptools infrastructure for use with setuptools version 61 or later
    - add the py.typed marker file
- testing infrastructure:
    - drop the "flake8 + hacking" test environment
    - add version constraints to the dependencies in all test environments
    - add the "validate" test environment to make sure the components.json file
      remains sane
    - when validating the components.json file, make sure each outdated version
      has exactly one non-outdated version in the same component and branch to
      update to
    - add Nox test definitions
    - move the lists of test environment dependencies to separate files to
      help Nox and Tox use the same ones
    - do not build diagnostic messages unless we need to (use lambdas in diag calls)
- start a HACKING.md how-to document for developers

2.0.1
-----

- Cinder drivers:
    - Wallaby:
        - add an entry for the StorPool updated driver for the 18.1.0 Ubuntu
          cloud archive version
        - recognize the 18.2.1 upstream version
        - bump the StorPool Cinder driver version so that it is higher than
          the upstream one
    - Xena:
        - add iSCSI support to the StorPool driver
    - Yoga:
        - recognize the 20.0.0 and 20.0.1 upstream versions
        - install an updated driver with iSCSI support
- Glance drivers:
    - Yoga:
        - recognize the 24.0.0 upstream version
- Nova drivers:
    - Victora:
        - recognize the 22.4.0 upstream version
        - recognize the 22.4.0 Ubuntu cloud archive version
    - Wallaby:
        - recognize the 23.2.0 and 23.2.1 upstream versions
        - recognize the 23.2.1 Ubuntu cloud archive version
    - Xena:
        - recognize the 24.1.0 and 24.1.1 upstream versions
        - recognize the 24.1.1 Ubuntu cloud archive version
    - Yoga:
        - recognize the 25.0.0 upstream version
        - recognize the 25.0.0 Ubuntu cloud archive version

2.0.0
-----

- reimplement the `sp-openstack` tool in Python 3.6 or higher
- let `sp-openstack` use the `dpkg-divert` tool on Debian/Ubuntu systems
  (unless the `-D` / `--no-divert` command-line option is specified) to
  make sure the local changes are not lost if the OpenStack packages are
  upgraded
- add the "uninstall" command to the `sp-openstack` tool
- detect the Xena release of OpenStack
- add some StorPool driver fixes for the OpenStack Victoria, Wallaby, and
  Xena releases:
    - drop `_attach_volume()`, `_detach_volume()`, and `backup_volume()`
    - reimplement `create_cloned_volume()` in a much more efficient way
    - implement `clone_image()`

1.5.0
-----

- add the "groups" command to the `sp-openstack` tool to only check, create,
  and set up the "spopenstack" group and the service accounts' membership,
  as well as the `/var/spool/storpool-spopenstack/` directory
- detect the Rocky, Stein, Train, Victoria, and Wallaby releases of OpenStack
- detect and set up the groups for Glance, too

1.4.0
-----

- Note that the StorPool drivers have been included in the Queens release.
- Detect the Queens release of OpenStack and (hopefully) just say that
  the StorPool integration is installed already.

1.3.0
-----

- Add the Pike Cinder, Nova, and os-brick drivers.
- Properly capitalize the 1.2.0 changelog entry.
- Add the `sp-image-to-volume` tool to save a Glance image to a StorPool volume
  and its manual page.

1.2.0
-----

- Add the `-T txn-module` option for use with the txn-install tool.

1.1.1
-----

- Add the sp-openstack.1 manual page.
- Look for the Python modules path in a way compatible with Python 3.

1.1.0
-----

- Add the Ocata Cinder volume driver and Nova attachment driver.
- Add the Newton and Ocata os-brick connector driver.
- Add the capability to make different changes to the same file for
  different OpenStack releases.
- Remove the "probably unaligned" warnings from the documentation of
  the "storpool volume list" and "storpool volume status" checks, since
  the StorPool CLI tool aligns the output in recent versions.
- Let the documentation use the "openstack" client tool where possible.

1.0.0
-----

- Update the Mitaka os-brick connector.
- Update the Liberty and Mitaka Cinder volume drivers.
- Fix the detection of Nova Liberty vs Mitaka.
- Drop support for the Juno and Kilo releases of OpenStack.

0.2.0
-----

- Allow the owner and group of the /var/spool/openstack-storpool/
  shared state directory to be overridden using the -u and -g
  options of the sp-openstack tool.

0.1.0
-----

- Initial public release.
