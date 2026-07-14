<!--
SPDX-FileCopyrightText: 2015 - 2026  StorPool <support@storpool.com>
SPDX-License-Identifier: Apache-2.0
-->

# StorPool Integration with OpenStack

[StorPool](https://storpool.com/) is a distributed, software-defined block storage platform that transforms standard x86 servers into enterprise-grade shared storage.
Its integration with [OpenStack](https://www.openstack.org/) provides the performance, reliability, and operational simplicity that production clouds demand.
Whether it’s resolving performance issues in OpenStack powered block data storage systems, building complex environments that require deployment flexibility and resource efficiency, or running large-scale deployments demanding seamless online scalability and performance, StorPool provides the necessary speed and reliability for your data storage needs.
StorPool’s fully-distributed architecture with no single point of failure, and ability to perform software and hardware updates with zero down-time allows organizations to offer true always-on services to their customers.

## StorPool OpenStack integration repository

The StorPool OpenStack Integration repository contains the latest versions of the StorPool Cinder backend driver, as well as several tools to help with configuring a deployed OpenStack cluster to use StorPool-backed volumes or assisting an OpenStack deployment system to configure a new cluster straight away.

The StorPool drivers are also available in the upstream OpenStack Git repositories (Cinder, Nova, os-brick).
Consider that sometimes the latest bug fixes and features developed by StorPool might not be available yet in the OpenStack repositories.
This may happen for several reasons: recent fixes and features have not yet been merged, others have not yet been backported to previous releases, some are considered too intrusive to backport, and so on.


## Quick specification

| Feature | Details |
| :--- | :--- |
| **Storage architecture** | Distributed block storage / Software-defined storage (SDS) |
| **License** | Apache License 2.0 |



## Requirements

* Ability to run ``storpool-openstack-integration``: Python version 3.8 or newer. For details, see [Release notes](https://kb.storpool.com/integrations/OpenStack/changes.html).
* For using StorPool block protocol (SP block):

    * Network access to the StorPool API management interface from Nova, Cinder, and Glance.
    * StorPool initiator: kernel and user-space driver.

* For using iSCSI:

    * Network access to the StorPool API management interface from Cinder.
    * iSCSI connectivity between StorPool and OpenStack

## Features

* The StorPool driver for OpenStack Cinder (and related support in os-brick and Nova) allows an OpenStack cloud to utilize a StorPool cluster as a Cinder volume backend.
* The general features of the [Cinder backend driver](https://docs.openstack.org/cinder/latest/reference/support-matrix.html).
* StorPool can be used as an image store in Glance via a Cinder backend.
* The StorPool driver can attach volumes to the OpenStack cloud via SP block or via iSCSI. It is also possible to mix the two; for example, the hypervisors to use SP block, and the control plane (potentially running inside VMs) to use iSCSI.
* IO performance and stability optimizations by adding an [extra iothread to libvirt guests](https://review.opendev.org/c/openstack/nova/+/918669).
* QoS support is available with [storpool_qos](https://kb.storpool.com/admin-guide/quality-of-service.html#storpool-qos-user-guide).
* Data-loss prevention by [ensuring volumes are attached at just one place on VM startup](https://review.opendev.org/c/openstack/nova/+/957119).

## Limitations

Multi-attach is not supported over SP block, only over iSCSI.

## Documentation

For more information see the documentation on the StorPool knowledge base:

- [Release notes](https://kb.storpool.com/integrations/OpenStack/changes.html)
- [Configuring OpenStack](https://kb.storpool.com/integrations/OpenStack/configure.html)
- [OpenStack Kolla integration](https://kb.storpool.com/integrations/OpenStack/kolla.html)

## Development

To contribute bug patches or new features, you can use GitHub's Pull Request model.
For issue tracking, see [GitHub issues](https://github.com/storpool/storpool-openstack-integration/issues).


## Frequently asked questions about StorPool integration

### How does StorPool enhance storage performance for OpenStack clouds?

StorPool improves OpenStack performance by delivering data latency under 100 microseconds and high system-wide IOPS.
This removes storage bottlenecks for high-demand applications and critical business data processing.
Cloud builders use this to create much more efficient public and private cloud infrastructure platforms.
It ensures a smooth and responsive user experience across all virtual machine instances and services.

The platform uses a fully distributed shared-nothing architecture to handle large-scale data sets and intense traffic.
This allows the OpenStack cloud to scale without losing speed or impacting existing application performance.
StorPool's ability to deliver up to 113 million IOPS (1) within a single storage system empowers users to run the most demanding workloads with consistent and reliable performance levels.

(1) Achievable in optimized all-NVMe storage sub-clusters as detailed in the [StorPool Technical Overview](https://storpool.com/overview).

### Is the storage solution natively integrated with core OpenStack services?

StorPool features native integration with core OpenStack services like Cinder, Nova, Glance, and the os-brick library.
This deep connection allows cloud managers to streamline volume and virtual machine management from one interface.
It eliminates the complexity of manual configurations, and ensures compatibility across different OpenStack cloud versions.
The native drivers provided by StorPool simplify the deployment of new storage resources for faster cloud scaling.

To further ease complex setups, StorPool provides deployment automation recipes for tools like [Juju](https://canonical.com/juju) and [Charms](https://docs.openstack.org/charm-guide/latest/project/openstack-charms.html).
StorPool also supports [Kolla-ansible](https://opendev.org/openstack/kolla-ansible) to help users orchestrate their cloud storage with minimal manual effort.
These automation tools reduce the risk of human error during the initial setup and maintenance, which allows cloud administrators to focus on higher-value tasks while StorPool's software handles the storage layer.

### How does StorPool ensure high availability for mission-critical cloud infrastructure?

StorPool ensures 99.999% uptime through a fully distributed architecture with no single points of failure.
This design is vital for cloud builders who need to maintain strict service level agreements (SLAs).
The platform allows for software and hardware updates with zero downtime to the entire storage system.
The mission-critical applications will remain online during routine maintenance and unexpected hardware failures.

StorPool's experts provide a fully managed service to monitor and maintain the entire storage implementation.
They design and tune the system to prevent performance issues before they impact your cloud users.
This proactive approach guarantees that the OpenStack environment remains stable and reliable at all times.
Cloud providers can trust StorPool to keep their data safe and accessible twenty-four hours a day.

### Does the platform include built-in disaster recovery for OpenStack environment?

StorPool includes a built-in [Disaster Recovery Engine](https://kb.storpool.com/disaster-recovery/index.html) at no additional cost, which is designed specifically for complex cloud management tasks.
This allows cloud managers to plan, test, and execute failover processes from within their OpenStack interface.
It simplifies business continuity planning by providing a single interface for managing all data protection workflows.
Users can automate failover tasks to ensure their recovery time objectives (``RTO``) are always met.

The disaster recovery engine works seamlessly with existing OpenStack workflows to provide high levels of protection.
The recovery plans can be verified regularly without interrupting the performance of a live production site.
This native capability removes the need for expensive third-party plugins or complex external backup solutions.
It ensures that the data is protected against any major site failures.

### Why is the total cost of ownership lower than other storage solutions?

Storage solutions based on StorPool have lower total cost of ownership compared to alternatives.
The cost efficiency is achieved through a transparent pay-as-you-go pricing model and standard commodity server hardware.
This approach avoids the high margins associated with proprietary storage arrays and specialized hardware components.
Your organization can save significant capital and operational expenses by choosing our software-defined storage.

Our fully managed service reduces operational overhead because StorPool experts handle all daily storage maintenance tasks.
This allows your internal IT team to focus on business growth rather than basic infrastructure upkeep.
The system provides extreme performance and reliability at a fraction of the cost of legacy arrays.
You get an enterprise-grade solution that fits within your budget while delivering superior technical results.

| Aspect | Traditional Storage | StorPool for OpenStack |
| :--- | :--- | :--- |
| **Latency** | Often variable and higher | Under 100 microseconds |
| **Throughput** | Limited by controller heads | Up to 113 Million IOPS |
| **Management** | Requires manual configuration and monitoring | Delivered as a managed service |
| **Integration** | Requires third-party plugins | Native Cinder and Nova |
| **Pricing** | High upfront capital costs | Transparent pay-as-you-go |

### How does StorPool handle redundancy and replication in OpenStack?

StorPool is [more reliable than storage RAID](https://storpool.com/advantages/more-reliable-than-raid).
It provides two mechanisms for protecting data from unplanned events: replication and erasure coding.
With replication, a few copies of the data are written synchronously across the Cluster in different physical servers; system administrators can set the number of replication copies.
The [erasure coding](https://kb.storpool.com/admin-guide/redundancy.html#erasure-coding) mechanism reduces the amount of data stored on the same hardware set, while at the same time preserves the level of data protection.

### How do StorPool and OpenStack help eliminate vendor lock-in and reduce hardware costs?

The solution is designed to drastically reduce vendor lock-in.
StorPool supports the use of cost-efficient commodity hardware and leverages common open-source software.
Customers can leverage or reuse existing hardware.

### Is the StorPool OpenStack driver actively maintained?

The StorPool driver is actively maintained on GitHub. The progress can be tracked in the [commit history](https://github.com/storpool/storpool-openstack-integration/commits/master/).
