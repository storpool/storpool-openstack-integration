# Copyright 2011 OpenStack Foundation
# (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Volume drivers for libvirt."""

from oslo_log import log as logging

import nova.conf
from nova import exception
from nova import profiler
from nova.virt import block_device as driver_block_device
from nova.virt.libvirt import config as vconfig

CONF = nova.conf.CONF
LOG = logging.getLogger(__name__)


@profiler.trace_cls("volume_api")
class LibvirtBaseVolumeDriver(object):
    """Base class for volume drivers."""

    def __init__(self, host, is_block_dev):
        self.host = host
        self.is_block_dev = is_block_dev

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = vconfig.LibvirtConfigGuestDisk()

        conf.source_device = disk_info['type']
        conf.driver_format = "raw"
        conf.driver_cache = "none"
        conf.target_dev = disk_info['dev']
        conf.target_bus = disk_info['bus']
        conf.serial = connection_info.get('serial')

        if CONF.libvirt.virt_type in ('qemu', 'kvm'):
            # the QEMU backend supports multiple backends, so tell libvirt
            # which one to use
            conf.driver_name = 'qemu'
            if CONF.libvirt.virt_type == 'kvm':
                conf.iothread_count = CONF.libvirt.iothread_count

        # Support for block size tuning
        data = {}
        if 'data' in connection_info:
            data = connection_info['data']
        if 'logical_block_size' in data:
            conf.logical_block_size = data['logical_block_size']
        if 'physical_block_size' in data:
            conf.physical_block_size = data['physical_block_size']

        # Extract rate_limit control parameters
        if 'qos_specs' in data and data['qos_specs']:
            tune_opts = ['total_bytes_sec', 'read_bytes_sec',
                         'write_bytes_sec', 'total_iops_sec',
                         'read_iops_sec', 'write_iops_sec',
                         'read_bytes_sec_max', 'read_iops_sec_max',
                         'write_bytes_sec_max', 'write_iops_sec_max',
                         'total_bytes_sec_max', 'total_iops_sec_max',
                         'size_iops_sec']
            specs = data['qos_specs']
            if isinstance(specs, dict):
                for k, v in specs.items():
                    if k in tune_opts:
                        new_key = 'disk_' + k
                        setattr(conf, new_key, v)
            else:
                LOG.warning('Unknown content in connection_info/'
                            'qos_specs: %s', specs)

        # Extract access_mode control parameters
        if 'access_mode' in data and data['access_mode']:
            access_mode = data['access_mode']
            if access_mode in ('ro', 'rw'):
                conf.readonly = access_mode == 'ro'
            else:
                LOG.error('Unknown content in '
                          'connection_info/access_mode: %s',
                          access_mode)
                raise exception.InvalidVolumeAccessMode(
                    access_mode=access_mode)

        # Configure usage of discard
        if data.get('discard', False) is True:
            conf.driver_discard = 'unmap'

        # NOTE(melwitt): We set the device address unit number manually in the
        # case of the virtio-scsi controller, in order to allow attachment of
        # up to 256 devices. So, we should only be setting the address tag
        # if we intend to set the unit number. Otherwise, we will let libvirt
        # handle autogeneration of the address tag.
        # See https://bugs.launchpad.net/nova/+bug/1792077 for details.
        if disk_info['bus'] == 'scsi' and 'unit' in disk_info:
            # The driver is responsible to create the SCSI controller
            # at index 0.
            conf.device_addr = vconfig.LibvirtConfigGuestDeviceAddressDrive()
            conf.device_addr.controller = 0
            # In order to allow up to 256 disks handled by one
            # virtio-scsi controller, the device addr should be
            # specified.
            conf.device_addr.unit = disk_info['unit']

        if connection_info.get('multiattach', False):
            # Note that driver_cache should be disabled (none) when using
            # a shareable disk.
            conf.shareable = True

        volume_id = driver_block_device.get_volume_id(connection_info)
        conf.alias = vconfig.make_libvirt_device_alias(volume_id)
        volume_secret = None
        if volume_id:
            volume_secret = self.host.find_secret('volume', volume_id)
        if volume_secret:
            conf.volume_encryption = vconfig.LibvirtConfigGuestDiskEncryption()
            secret = vconfig.LibvirtConfigGuestDiskEncryptionSecret()
            secret.type = 'passphrase'
            secret.uuid = volume_secret.UUIDString()
            conf.volume_encryption.format = 'luks'
            conf.volume_encryption.secret = secret

        return conf

    def connect_volume(self, connection_info, instance):
        """Connect the volume."""
        pass

    def disconnect_volume(self, connection_info, instance, force=False):
        """Disconnect the volume."""
        pass

    def extend_volume(self, connection_info, instance, requested_size):
        """Extend the volume.

        :param connection_info: connection information about the volume
            that has been extended.
        :param instance: instance connected to the newly extended volume.
        :param requested_size: new extended size (in bytes) for the volume to
            be extended.

        :returns: the new size to use when resizing the disk in QEMU.

        Note: the requested_size parameter is not used by all volume drivers
        """
        raise NotImplementedError()


class LibvirtVolumeDriver(LibvirtBaseVolumeDriver):
    """Class for volumes backed by local file."""

    def __init__(self, host):
        super(LibvirtVolumeDriver,
              self).__init__(host, is_block_dev=True)

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtVolumeDriver,
                     self).get_config(connection_info, disk_info)
        conf.source_type = "block"
        conf.source_path = connection_info['data']['device_path']
        return conf


class LibvirtFakeVolumeDriver(LibvirtBaseVolumeDriver):
    """Driver to attach fake volumes to libvirt."""

    def __init__(self, host):
        super(LibvirtFakeVolumeDriver,
              self).__init__(host, is_block_dev=True)

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtFakeVolumeDriver,
                     self).get_config(connection_info, disk_info)
        conf.source_type = "network"
        conf.source_protocol = "fake"
        conf.source_name = "fake"
        return conf
