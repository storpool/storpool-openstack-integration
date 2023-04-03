<!--
SPDX-FileCopyrightText: 2015 - 2023  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# StorPool Distributed Storage

## Introduction

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

## Concepts

In a StorPool cluster the user data is stored in virtual volumes managed
in a transparent way by the StorPool servers.  When needed, a volume is
attached to a client host using the StorPool client device driver and
exposed to processes running on the host as a block device.

## Components

Hosts that will use the StorPool volumes only need to run
the `storpool_beacon` (StorPool cluster presence and quorum) and
the `storpool_block` (StorPool block device client) services.

On a hyperconverged setup, the hosts will also run the `storpool_server`
(StorPool data storage) and `storpool_mgmt` (StorPool management API)
services.  On setups with differentiated storage and client hosts, these
services will only need to run on the storage cluster.
