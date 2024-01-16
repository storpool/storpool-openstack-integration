<!--
SPDX-FileCopyrightText: 2015 - 2024  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# Configure OpenStack for use with the StorPool Cinder backend

## Cinder backend

An OpenStack environment that uses StorPool as a storage backend only
needs the client services; the actual disks that store the data may be
on a separate storage cluster.

This section describes the configuration of the OpenStack Cinder (block
storage) service.
Note that the StorPool Cinder drivers may need to be installed
beforehand; see the "Installing the StorPool drivers" section for
details.

### Configuring the StorPool Cinder backend

Once the StorPool Cinder volume driver is installed (as part of
OpenStack or, for earlier releases, separately), a driver backend
section must be created in the `/etc/cinder/cinder.conf` file:

    [storpool]
    volume_driver=cinder.volume.drivers.storpool.StorPoolDriver
    storpool_template=hybrid-r3
    report_discard_supported=True

If StorPool should be the only storage backend, all the
`enabled_backends` and `volume_backend` lines should be removed from
the `cinder.conf` file's `[DEFAULT]` section and a single line should be
added:

    enabled_backends=storpool

If other volume backends should coexist with StorPool, make sure that
`storpool` is listed in an `enabled_backends` setting.

Then restart the relevant Cinder services:

    # service cinder-volume restart
    # service cinder-scheduler restart

### Using StorPool templates via Cinder volume types

If a StorPool cluster has several different templates defined (for
reasons ranging from quality of service to fault sets and availability
zones), they may be exposed to Cinder through the use of volume types.
For each StorPool template, define a volume type and specify the
StorPool template name as its `storpool_template` property:

    # openstack volume type create --property volume_backend_name=storpool --property storpool_template='hybrid-r2' hybrid-r2
    # openstack volume type create --property volume_backend_name=storpool --property storpool_template='hdd-only' hdd-only

The names of the available StorPool templates may be viewed with
the `storpool template list` command if the StorPool CLI is installed.

### Creating volumes and snapshots

To create a new, blank volume in one of the previously defined volume
types:

    # openstack volume create --type hybrid --size 10 test-volume

To make sure that there is actually a StorPool volume created, first
obtain the OpenStack internal volume identifier:

    # openstack volume show -f value -c id test-volume
    cc2b3692-a2b6-4ad7-82ef-6a37d3e0f4da

    # storpool volume list | fgrep -e 'cc2b3692-a2b6-4ad7-82ef-6a37d3e0f4da'
    | os--volume-cc2b3692-a2b6-4ad7-82ef-6a37d3e0f4da |   10 GB |     3 | hdd        | hdd        | ssd        |

To create a volume from an existing image stored in Glance:

    # openstack volume create --type hybrid --size 1 --image cirros-0.4.0 cirros-v

To create a snapshot of this volume:

    # openstack volume snapshot create --name cirros cirros-v

## Nova attachment driver

This section describes the configuration of the OpenStack Nova (compute)
service to use StorPool-backed volumes created by Cinder.

The changes needed to let Nova recognize StorPool volumes as exported by
Cinder were merged into the OpenStack Queens (February 2018) release.

### Using StorPool volumes as instance root disks

The preferred way to use StorPool volumes as root disks for Nova
instances is to create a volume-backed instance and a new volume for it
to use.

1. Choose a Glance image to use as the root disk.

2. Create a Cinder volume from that Glance image.

3. Create a snapshot of that Cinder volume.

4. Create a Nova instance and tell it to create a new volume from
   the snapshot.

Step 4 may be repeated for many instances; a new volume shall be created
for each instance's root disk, but within the StorPool cluster all these
volumes will be descended from the one holding the Cinder snapshot, so
there shall be no needless copying of data and no overuse of disk space.

## Installing the StorPool drivers

Most of the time, the StorPool Cinder driver in the OpenStack Git
repository or the released versions is not completely up-to-date with
the latest features and bugfixes.

### Preliminary setup

1. Set up an OpenStack cluster.

2. Set up a StorPool cluster.

3. Set up at least the StorPool client (the `storpool_beacon` and
   `storpool_block` services) on the OpenStack controller node and on
   each of the hypervisor nodes.

4. On the node that will run the `cinder-volume` service and all
   the hypervisor nodes that will run the `nova-compute` service,
   install the
   [`storpool`][py-storpool] and
   [`storpool-spopenstack`][py-spopenstack] Python packages:

        # Install pip (the Python package installer) first
        yum install python-pip
        # ...or...
        apt-get install --no-install-recommends python-pip
        
        pip install storpool
        pip install storpool.spopenstack

5. On the same nodes, clone
   the [StorPool OpenStack Integration][github] Git repository
   or copy it from some other host where it has been cloned:

        # Clone the StorPool OpenStack Integration repository
        git clone https://github.com/storpool/storpool-openstack-integration.git

### Set up the Cinder volume backend

0. Change into the `storpool-openstack-integration/` directory prepared in
   the last step of the "Preliminary setup" section above.

1. Let the StorPool OpenStack integration suite find your Cinder drivers and
   apply the StorPool integration changes:
   and make the necessary modifications in its own work directory:

        ./sp-openstack check
        ./sp-openstack install cinder os_brick

2. Proceed as per the "Configuring the OpenStack Cinder StorPool volume
   backend" section above.

### Set up the Nova volume attachment driver (on each hypevisor node)

0. Change into the `storpool-openstack-integration/` directory prepared in
   the last step of the "Preliminary setup" section above.

1. Make sure that the Python modules [`storpool`][py-storpool] and
   [`storpool.spopenstack`][py-spopenstack]
   have also been installed on all the hypervisor nodes (see the "Preliminary
   setup" section above).

2. Let the StorPool OpenStack integration suite find your Nova drivers and
   make the necessary modifications in its own work directory:

        ./sp-openstack check
        ./sp-openstack install nova

3. Proceed as per the "Configuring the OpenStack Nova StorPool volume
   attachment driver" section above.

[github]: https://github.com/storpool/storpool-openstack-integration
[py-storpool]: https://github.com/storpool/python-storpool
[py-spopenstack]: https://github.com/storpool/python-storpool-spopenstack
[rdo]: https://www.rdoproject.org/
