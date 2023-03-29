<!--
SPDX-FileCopyrightText: 2015 - 2023  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# StorPool Integration with OpenStack

This document describes the ways to configure the OpenStack Cinder block
storage component to use the StorPool distributed storage as a backend
and provide StorPool-backed volumes to the other OpenStack services
such as Nova Compute.

## StorPool Distributed Storage

### Introduction

StorPool is distributed data storage software running on standard x86
servers.  StorPool aggregates the performance and capacity of all drives
into a shared pool of storage distributed among the servers.  Within
this storage pool the user creates thin-provisioned volumes that are
exposed to the clients as block devices.  StorPool consists of two parts
wrapped in one package - a server and a client.  The StorPool server
allows a hypervisor to act as a storage node, while the StorPool client
allows a hypervisor node to access the storage pool and act as a compute
node.  In OpenStack terms the StorPool solution allows each hypervisor
node to be both a storage and a compute node simultaneously.

### Concepts

In a StorPool cluster the user data is stored in virtual volumes managed
in a transparent way by the StorPool servers.  When needed, a volume is
attached to a client host using the StorPool client device driver and
exposed to processes running on the host as a block device.

### Components

Hosts that will use the StorPool volumes only need to run
the `storpool_beacon` (StorPool cluster presence and quorum) and
the `storpool_block` (StorPool block device client) services.

On a hyperconverged setup, the hosts will also run the `storpool_server`
(StorPool data storage) and `storpool_mgmt` (StorPool management API)
services.  On setups with differentiated storage and client hosts, these
services will only need to run on the storage cluster.

## Configuring the OpenStack Cinder StorPool volume backend

An OpenStack environment that uses StorPool as a storage backend only
needs the client services; the actual disks that store the data may be
on a separate storage cluster.

This section describes the configuration of the OpenStack Cinder (block
storage) service.  Note that for OpenStack releases before Queens
(February 2018), the StorPool Cinder drivers may need to be installed
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

## Configuring the OpenStack Nova StorPool volume attachment driver

This section describes the configuration of the OpenStack Nova (compute)
service to use StorPool-backed volumes created by Cinder.  Note that for
OpenStack releases before Queens (February 2018), the StorPool Nova
drivers may need to be installed beforehand; see the "Installing the
StorPool drivers" section for details.

### Configuring the Nova volume attachment driver

Edit the `/etc/nova/nova.conf` file.  If there is a `volume_drivers`
line in the `[DEFAULT]` section, add to it the following definition.
If there is no such line, add it:

    volume_drivers=storpool=nova.virt.libvirt.volume.LibvirtStorPoolVolumeDriver

Then restart the relevant Nova services:

    # service nova-compute restart
    # service nova-api-metadata restart

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

For the OpenStack releases before Queens, namely Mitaka (April 2016),
Newton (October 2016), Ocata (February 2017), and Pike (August 2017),
the StorPool drivers for Cinder and Nova are not part of the OpenStack
distribution and must be installed separately.  The tools referenced in
this section may be obtained from the [StorPool OpenStack
Integration][github] Git repository.

### Preliminary setup

1. Set up an OpenStack cluster.

2. Set up a StorPool cluster.

3. Set up at least the StorPool client (the `storpool_beacon` and
   `storpool_block` services) on the OpenStack controller node and on
   each of the hypervisor nodes.

4. On the controller and all the hypervisor nodes, install the
   [`storpool`][py-storpool] and
   [`storpool-spopenstack`][py-spopenstack] Python packages:

        # Install pip (the Python package installer) first
        yum install python-pip
        # ...or...
        apt-get install --no-install-recommends python-pip
        
        pip install storpool
        pip install storpool.spopenstack

5. On the controller and all the hypervisor nodes, clone
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
   and make the necessary modifications in its own work directory:

        ./sp-openstack check
        ./sp-openstack install nova

3. Proceed as per the "Configuring the OpenStack Nova StorPool volume
   attachment driver" section above.

[github]: https://github.com/storpool/storpool-openstack-integration
[py-storpool]: https://github.com/storpool/python-storpool
[py-spopenstack]: https://github.com/storpool/python-storpool-spopenstack
[rdo]: https://www.rdoproject.org/
