# (c) Copyright 2015 - 2017  StorPool
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

from os_brick.initiator import connector
from oslo_log import log as logging

from nova import utils
from nova.virt.libvirt.volume import volume as libvirt_volume

LOG = logging.getLogger(__name__)


class LibvirtStorPoolVolumeDriver(libvirt_volume.LibvirtBaseVolumeDriver):
    """Driver to attach StorPool volumes to libvirt."""

    def __init__(self, host):
        super(LibvirtStorPoolVolumeDriver, self).__init__(host,
                                                       is_block_dev=True)

        self.connector = connector.InitiatorConnector.factory(
            'STORPOOL', utils.get_root_helper())

    def get_config(self, connection_info, disk_info):
        """Returns xml for libvirt."""
        conf = super(LibvirtStorPoolVolumeDriver, self).get_config(
            connection_info, disk_info)

        conf.source_type = 'block'
        conf.source_path = connection_info['data']['device_path']
        return conf

    def connect_volume(self, connection_info, disk_info, instance):
        LOG.debug("Attaching a StorPool volume: %s.", connection_info, instance=instance)
        device_info = self.connector.connect_volume(connection_info['data'])
        LOG.debug("Attached StorPool volume %s.", device_info, instance=instance)
        connection_info['data']['device_path'] = device_info['path']
        return self.get_config(connection_info, disk_info)

    def disconnect_volume(self, connection_info, disk_dev, instance):
        LOG.debug("Disconnecting StorPool volume %s (%s)",
                  disk_dev, connection_info, instance=instance)
        self.connector.disconnect_volume(connection_info['data'], None)
        LOG.debug("Disconnected StorPool volume %s", disk_dev, instance=instance)

    def extend_volume(self, connection_info, instance):
        """Extend the volume."""
        LOG.debug("Extending StorPool volume %s", connection_info, instance=instance)
        new_size = self.connector.extend_volume(connection_info['data'])
        LOG.debug("Extend StorPool Volume %s; new_size=%s",
                  connection_info['data']['device_path'],
                  new_size, instance=instance)
        return new_size
