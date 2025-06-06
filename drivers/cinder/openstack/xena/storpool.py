#    Copyright (c) 2014 - 2022 StorPool
#    All Rights Reserved.
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

"""StorPool block device driver"""

import fnmatch
import platform

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import importutils
from oslo_utils import netutils
from oslo_utils import units
from oslo_utils import uuidutils
import six

from cinder import context
from cinder import exception
from cinder.i18n import _
from cinder import interface
from cinder.volume import configuration
from cinder.volume import driver
from cinder.volume import volume_types

LOG = logging.getLogger(__name__)

storpool = importutils.try_import('storpool')
if storpool:
    from storpool import spapi
    from storpool import spconfig
    from storpool import spopenstack
    from storpool import sptypes


storpool_opts = [
    cfg.BoolOpt('iscsi_cinder_volume',
                default=False,
                help='Let the cinder-volume service use iSCSI instead of '
                     'the StorPool block device driver for accessing '
                     'StorPool volumes, e.g. when creating a volume from '
                     'an image or vice versa.'),
    cfg.StrOpt('iscsi_export_to',
               default='',
               help='Whether to export volumes using iSCSI. '
                    'An empty string (the default) makes the driver export '
                    'all volumes using the StorPool native network protocol. '
                    'The value "*" makes the driver export all volumes using '
                    'iSCSI. '
                    'Any other value leads to an experimental not fully '
                    'supported configuration and is interpreted as '
                    'a whitespace-separated list of patterns for IQNs for '
                    'hosts that need volumes to be exported via iSCSI, e.g. '
                    '"iqn.1991-05.com.microsoft:\\*" for Windows hosts.'),
    cfg.BoolOpt('iscsi_learn_initiator_iqns',
                default=True,
                help='Create a StorPool record for a new initiator as soon as '
                     'Cinder asks for a volume to be exported to it.'),
    cfg.StrOpt('iscsi_portal_group',
               default=None,
               help='The portal group to export volumes via iSCSI in.'),
    cfg.StrOpt('storpool_template',
               default=None,
               help='The StorPool template for volumes with no type.'),
    cfg.IntOpt('storpool_replication',
               default=3,
               help='The default StorPool chain replication value.  '
                    'Used when creating a volume with no specified type if '
                    'storpool_template is not set.  Also used for calculating '
                    'the apparent free space reported in the stats.'),
]

CONF = cfg.CONF
CONF.register_opts(storpool_opts, group=configuration.SHARED_CONF_GROUP)

EXTRA_SPECS_NAMESPACE = 'storpool'
EXTRA_SPECS_QOS = 'qos_class'
ES_QOS = EXTRA_SPECS_NAMESPACE + ":" + EXTRA_SPECS_QOS


def _extract_cinder_ids(urls):
    ids = []
    for url in urls:
        # The url can also be None and a TypeError is raised
        # TypeError: a bytes-like object is required, not 'str'
        if not url:
            continue
        parts = netutils.urlsplit(url)
        if parts.scheme == 'cinder':
            if parts.path:
                vol_id = parts.path.split('/')[-1]
            else:
                vol_id = parts.netloc
            if uuidutils.is_uuid_like(vol_id):
                ids.append(vol_id)
            else:
                LOG.debug("Ignoring malformed image location uri "
                          "'%(url)s'", {'url': url})

    return ids


class StorPoolConfigurationInvalid(exception.CinderException):
    message = _("Invalid parameter %(param)s in the %(section)s section "
                "of the /etc/storpool.conf file: %(error)s")


@interface.volumedriver
class StorPoolDriver(driver.VolumeDriver):
    """The StorPool block device driver.

    Version history:

    .. code-block:: none

        0.1.0   - Initial driver
        0.2.0   - Bring the driver up to date with Kilo and Liberty:
                  - implement volume retyping and migrations
                  - use the driver.*VD ABC metaclasses
                  - bugfix: fall back to the configured StorPool template
        1.0.0   - Imported into OpenStack Liberty with minor fixes
        1.1.0   - Bring the driver up to date with Liberty and Mitaka:
                  - drop the CloneableVD and RetypeVD base classes
                  - enable faster volume copying by specifying
                    sparse_volume_copy=true in the stats report
        1.1.1   - Fix the internal _storpool_client_id() method to
                  not break on an unknown host name or UUID; thus,
                  remove the StorPoolConfigurationMissing exception.
        1.1.2   - Bring the driver up to date with Pike: do not
                  translate the error messages
        1.2.0   - Inherit from VolumeDriver, implement get_pool()
        1.2.1   - Implement interface.volumedriver, add CI_WIKI_NAME,
                  fix the docstring formatting
        1.2.2   - Reintroduce the driver into OpenStack Queens,
                  add ignore_errors to the internal _detach_volume() method
        1.2.3   - Advertise some more driver capabilities.
        2.0.0   - Drop _attach_volume() and _detach_volume(), our os-brick
                  connector will handle this.
                - Drop backup_volume()
                - Avoid data duplication in create_cloned_volume()
                - Implement clone_image()
                - Implement revert_to_snapshot().
                - Add support for exporting volumes via iSCSI
    """

    VERSION = '2.0.0'
    CI_WIKI_NAME = 'StorPool_distributed_storage_CI'

    def __init__(self, *args, **kwargs):
        super(StorPoolDriver, self).__init__(*args, **kwargs)
        self.configuration.append_config_values(storpool_opts)
        self._sp_config = None
        self._ourId = None
        self._ourIdInt = None
        self._attach = None
        self._use_iscsi = None

    @staticmethod
    def get_driver_options():
        return storpool_opts

    @staticmethod
    def qos_from_volume(volume):
        volume_type = volume['volume_type']
        extra_specs = \
            volume_types.get_volume_type_extra_specs(volume_type['id'])
        if extra_specs is not None:
            return extra_specs.get(ES_QOS)
        return None

    def _backendException(self, e):
        return exception.VolumeBackendAPIException(data=six.text_type(e))

    def _template_from_volume(self, volume):
        default = self.configuration.storpool_template
        vtype = volume['volume_type']
        if vtype is not None:
            specs = volume_types.get_volume_type_extra_specs(vtype['id'])
            if specs is not None:
                return specs.get('storpool_template', default)
        return default

    def get_pool(self, volume):
        template = self._template_from_volume(volume)
        if template is None:
            return 'default'
        else:
            return 'template_' + template

    def create_volume(self, volume):
        size = int(volume['size']) * units.Gi
        name = self._attach.volumeName(volume['id'])
        template = self._template_from_volume(volume)
        qos_class = StorPoolDriver.qos_from_volume(volume)

        create_request = {'name': name, 'size': size}

        if template is not None:
            create_request['template'] = template
        else:
            create_request['replication'] = \
                self.configuration.storpool_replication

        if qos_class is not None:
            create_request['tags'] = {'qc': qos_class}

        try:
            self._attach.api().volumeCreate(create_request)
        except spapi.ApiError as e:
            raise self._backendException(e)

    def _storpool_client_id(self, connector):
        hostname = connector['host']
        if hostname == self.host or hostname == CONF.host:
            hostname = platform.node()
        try:
            cfg = spconfig.SPConfig(section=hostname)
            return int(cfg['SP_OURID'])
        except KeyError:
            return 65
        except Exception as e:
            raise StorPoolConfigurationInvalid(
                section=hostname, param='SP_OURID', error=e)

    def _connector_wants_iscsi(self, connector):
        """Should we do this export via iSCSI?

        Check the configuration to determine whether this connector is
        expected to provide iSCSI exports as opposed to native StorPool
        protocol ones.  Match the initiator's IQN against the list of
        patterns supplied in the "iscsi_export_to" configuration setting.
        """
        if connector is None:
            return False
        if self._use_iscsi:
            LOG.debug('  - forcing iSCSI for all exported volumes')
            return True
        if connector.get('storpool_wants_iscsi'):
            LOG.debug('  - forcing iSCSI for the controller')
            return True

        try:
            iqn = connector.get('initiator')
        except Exception:
            iqn = None
        try:
            host = connector.get('host')
        except Exception:
            host = None
        if iqn is None or host is None:
            LOG.debug('  - this connector certainly does not want iSCSI')
            return False

        LOG.debug('  - check whether %(host)s (%(iqn)s) wants iSCSI',
                  {
                      'host': host,
                      'iqn': iqn,
                  })

        export_to = self.configuration.iscsi_export_to
        if export_to is None:
            return False

        for pat in export_to.split():
            LOG.debug('    - matching against %(pat)s', {'pat': pat})
            if fnmatch.fnmatch(iqn, pat):
                LOG.debug('      - got it!')
                return True
        LOG.debug('    - nope')
        return False

    def validate_connector(self, connector):
        if self._connector_wants_iscsi(connector):
            return True
        return self._storpool_client_id(connector) >= 0

    def _get_iscsi_config(self, iqn, volume_id):
        """Get the StorPool iSCSI config items pertaining to this volume.

        Find the elements of the StorPool iSCSI configuration tree that
        will be needed to create, ensure, or remove the iSCSI export of
        the specified volume to the specified initiator.
        """
        cfg = self._attach.api().iSCSIConfig()

        pg_name = self.configuration.iscsi_portal_group
        pg_found = [
            pg for pg in cfg.iscsi.portalGroups.values() if pg.name == pg_name
        ]
        if not pg_found:
            raise Exception('StorPool Cinder iSCSI configuration error: '
                            'no portal group "{pg}"'.format(pg=pg_name))
        pg = pg_found[0]

        # Do we know about this initiator?
        i_found = [
            init for init in cfg.iscsi.initiators.values() if init.name == iqn
        ]
        if i_found:
            initiator = i_found[0]
        else:
            initiator = None

        # Is this volume already being exported?
        volname = self._attach.volumeName(volume_id)
        t_found = [
            tgt for tgt in cfg.iscsi.targets.values() if tgt.volume == volname
        ]
        if t_found:
            target = t_found[0]
        else:
            target = None

        # OK, so is this volume being exported to this initiator?
        export = None
        if initiator is not None and target is not None:
            e_found = [
                exp for exp in initiator.exports
                if exp.portalGroup == pg.name and exp.target == target.name
            ]
            if e_found:
                export = e_found[0]

        return {
            'cfg': cfg,
            'pg': pg,
            'initiator': initiator,
            'target': target,
            'export': export,
            'volume_name': volname,
            'volume_id': volume_id,
        }

    def _create_iscsi_export(self, volume, connector):
        """Create (if needed) an iSCSI export for the StorPool volume."""
        LOG.debug(
            '_create_iscsi_export() invoked for volume '
            '"%(vol_name)s" (%(vol_id)s) connector %(connector)s',
            {
                'vol_name': volume['display_name'],
                'vol_id': volume['id'],
                'connector': connector,
            }
        )
        iqn = connector['initiator']
        try:
            cfg = self._get_iscsi_config(iqn, volume['id'])
        except Exception as exc:
            LOG.error(
                'Could not fetch the iSCSI config: %(exc)s', {'exc': exc}
            )
            raise

        if cfg['initiator'] is None:
            if not (self.configuration.iscsi_learn_initiator_iqns or
                    self.configuration.iscsi_cinder_volume and
                    connector.get('storpool_wants_iscsi')):
                raise Exception('The "{iqn}" initiator IQN for the "{host}" '
                                'host is not defined in the StorPool '
                                'configuration.'
                                .format(iqn=iqn, host=connector['host']))
            else:
                LOG.info('Creating a StorPool iSCSI initiator '
                         'for "{host}s" ({iqn}s)',
                         {'host': connector['host'], 'iqn': iqn})
                self._attach.api().iSCSIConfigChange({
                    'commands': [
                        {
                            'createInitiator': {
                                'name': iqn,
                                'username': '',
                                'secret': '',
                            },
                        },
                        {
                            'initiatorAddNetwork': {
                                'initiator': iqn,
                                'net': '0.0.0.0/0',
                            },
                        },
                    ]
                })

        if cfg['target'] is None:
            LOG.info(
                'Creating a StorPool iSCSI target '
                'for the "%(vol_name)s" volume (%(vol_id)s)',
                {
                    'vol_name': volume['display_name'],
                    'vol_id': volume['id'],
                }
            )
            self._attach.api().iSCSIConfigChange({
                'commands': [
                    {
                        'createTarget': {
                            'volumeName': cfg['volume_name'],
                        },
                    },
                ]
            })
            cfg = self._get_iscsi_config(iqn, volume['id'])

        if cfg['export'] is None:
            LOG.info('Creating a StorPool iSCSI export '
                     'for the "{vol_name}s" volume ({vol_id}s) '
                     'to the "{host}s" initiator ({iqn}s) '
                     'in the "{pg}s" portal group',
                     {
                         'vol_name': volume['display_name'],
                         'vol_id': volume['id'],
                         'host': connector['host'],
                         'iqn': iqn,
                         'pg': cfg['pg'].name
                     })
            self._attach.api().iSCSIConfigChange({
                'commands': [
                    {
                        'export': {
                            'initiator': iqn,
                            'portalGroup': cfg['pg'].name,
                            'volumeName': cfg['volume_name'],
                        },
                    },
                ]
            })

        target_portals = [
            "{addr}:3260".format(addr=net.address)
            for net in cfg['pg'].networks
        ]
        target_iqns = [cfg['target'].name] * len(target_portals)
        target_luns = [0] * len(target_portals)
        if connector.get('multipath', False):
            multipath_settings = {
                'target_iqns': target_iqns,
                'target_portals': target_portals,
                'target_luns': target_luns,
            }
        else:
            multipath_settings = {}

        res = {
            'driver_volume_type': 'iscsi',
            'data': {
                **multipath_settings,
                'target_discovered': False,
                'target_iqn': target_iqns[0],
                'target_portal': target_portals[0],
                'target_lun': target_luns[0],
                'volume_id': volume['id'],
                'discard': True,
            },
        }
        LOG.debug('returning %(res)s', {'res': res})
        return res

    def _remove_iscsi_export(self, volume, connector):
        """Remove an iSCSI export for the specified StorPool volume."""
        LOG.debug(
            '_remove_iscsi_export() invoked for volume '
            '"%(vol_name)s" (%(vol_id)s) connector %(conn)s',
            {
                'vol_name': volume['display_name'],
                'vol_id': volume['id'],
                'conn': connector,
            }
        )
        try:
            cfg = self._get_iscsi_config(connector['initiator'], volume['id'])
        except Exception as exc:
            LOG.error(
                'Could not fetch the iSCSI config: %(exc)s', {'exc': exc}
            )
            raise

        if cfg['export'] is not None:
            LOG.info('Removing the StorPool iSCSI export '
                     'for the "%(vol_name)s" volume (%(vol_id)s) '
                     'to the "%(host)s" initiator (%(iqn)s) '
                     'in the "%(pg)s" portal group',
                     {
                         'vol_name': volume['display_name'],
                         'vol_id': volume['id'],
                         'host': connector['host'],
                         'iqn': connector['initiator'],
                         'pg': cfg['pg'].name,
                     })
            try:
                self._attach.api().iSCSIConfigChange({
                    'commands': [
                        {
                            'exportDelete': {
                                'initiator': cfg['initiator'].name,
                                'portalGroup': cfg['pg'].name,
                                'volumeName': cfg['volume_name'],
                            },
                        },
                    ]
                })
            except spapi.ApiError as e:
                if e.name not in ('objectExists', 'objectDoesNotExist'):
                    raise
                LOG.info('Looks like somebody beat us to it')

        if cfg['target'] is not None:
            last = True
            for initiator in cfg['cfg'].iscsi.initiators.values():
                if initiator.name == cfg['initiator'].name:
                    continue
                for exp in initiator.exports:
                    if exp.target == cfg['target'].name:
                        last = False
                        break
                if not last:
                    break

            if last:
                LOG.info(
                    'Removing the StorPool iSCSI target '
                    'for the "{vol_name}s" volume ({vol_id}s)',
                    {
                        'vol_name': volume['display_name'],
                        'vol_id': volume['id'],
                    }
                )
                try:
                    self._attach.api().iSCSIConfigChange({
                        'commands': [
                            {
                                'deleteTarget': {
                                    'volumeName': cfg['volume_name'],
                                },
                            },
                        ]
                    })
                except spapi.ApiError as e:
                    if e.name not in ('objectDoesNotExist', 'invalidParam'):
                        raise
                    LOG.info('Looks like somebody beat us to it')

    def initialize_connection(self, volume, connector):
        if self._connector_wants_iscsi(connector):
            return self._create_iscsi_export(volume, connector)
        return {'driver_volume_type': 'storpool',
                'data': {
                    'client_id': self._storpool_client_id(connector),
                    'volume': volume['id'],
                    'access_mode': 'rw',
                }}

    def terminate_connection(self, volume, connector, **kwargs):
        if self._connector_wants_iscsi(connector):
            LOG.debug('- removing an iSCSI export')
            self._remove_iscsi_export(volume, connector)
        pass

    def create_snapshot(self, snapshot):
        volname = self._attach.volumeName(snapshot['volume_id'])
        name = self._attach.snapshotName('snap', snapshot['id'])
        try:
            self._attach.api().snapshotCreate(volname, {'name': name})
        except spapi.ApiError as e:
            raise self._backendException(e)

    def create_volume_from_snapshot(self, volume, snapshot):
        size = int(volume['size']) * units.Gi
        volname = self._attach.volumeName(volume['id'])
        name = self._attach.snapshotName('snap', snapshot['id'])
        qos_class = StorPoolDriver.qos_from_volume(volume)

        create_request = {'name': volname, 'size': size, 'parent': name}

        if qos_class is not None:
            create_request['tags'] = {'qc': qos_class}

        try:
            self._attach.api().volumeCreate(create_request)
        except spapi.ApiError as e:
            raise self._backendException(e)

    def clone_image(self, context, volume,
                    image_location, image_meta, image_service):
        if (image_meta.get('container_format') != 'bare' or
                image_meta.get('disk_format') != 'raw'):
            LOG.info("Requested image %(id)s is not in raw format.",
                     {'id': image_meta.get('id')})
            return None, False

        LOG.debug('Check whether the image is accessible')
        visibility = image_meta.get('visibility', None)
        public = (
            visibility and visibility == 'public' or
            image_meta.get('is_public', False) or
            image_meta['owner'] == volume['project_id']
        )
        if not public:
            LOG.warning(
                'The requested image is not accessible by the current tenant'
            )
            return None, False

        LOG.debug('On to parsing %(loc)s', {'loc': repr(image_location)})
        direct_url, locations = image_location
        urls = list(set([direct_url] + [
            loc.get('url') for loc in locations or []
        ]))
        image_volume_ids = _extract_cinder_ids(urls)
        LOG.debug('image_volume_ids %(ids)s', {'ids': repr(image_volume_ids)})

        if not image_volume_ids:
            LOG.info('No Cinder volumes found to clone')
            return None, False

        vol_id = image_volume_ids[0]
        LOG.info('Cloning volume %(vol_id)s', {'vol_id': vol_id})
        return self.create_cloned_volume(volume, {'id': vol_id}), True

    def create_cloned_volume(self, volume, src_vref):
        refname = self._attach.volumeName(src_vref['id'])
        size = int(volume['size']) * units.Gi
        volname = self._attach.volumeName(volume['id'])
        qos_class = StorPoolDriver.qos_from_volume(volume)

        clone_request = {'name': volname, 'size': size}

        if qos_class is not None:
            clone_request['tags'] = {'qc': qos_class}

        src_volume = self.db.volume_get(
            context.get_admin_context(),
            src_vref['id'],
        )
        src_template = self._template_from_volume(src_volume)

        template = self._template_from_volume(volume)
        LOG.debug('clone volume id %(vol_id)s template %(template)s', {
            'vol_id': repr(volume['id']),
            'template': repr(template),
        })
        if template == src_template:
            LOG.info('Using baseOn to clone a volume into the same template')
            clone_request['baseOn'] = refname
            try:
                self._attach.api().volumeCreate(clone_request)
            except spapi.ApiError as e:
                raise self._backendException(e)

            return None

        snapname = self._attach.snapshotName('clone', volume['id'])
        LOG.info(
            'A transient snapshot for a %(src)s -> %(dst)s template change',
            {'src': src_template, 'dst': template})
        try:
            self._attach.api().snapshotCreate(refname, {'name': snapname})
        except spapi.ApiError as e:
            if e.name != 'objectExists':
                raise self._backendException(e)

        try:
            try:
                self._attach.api().snapshotUpdate(
                    snapname,
                    {'template': template},
                )
            except spapi.ApiError as e:
                raise self._backendException(e)

            try:
                clone_request['parent'] = snapname
                self._attach.api().volumeCreate(clone_request)
            except spapi.ApiError as e:
                raise self._backendException(e)

            try:
                self._attach.api().snapshotUpdate(
                    snapname,
                    {'tags': {'transient': '1.0'}},
                )
            except spapi.ApiError as e:
                raise self._backendException(e)
        except Exception:
            with excutils.save_and_reraise_exception():
                try:
                    LOG.warning(
                        'Something went wrong, removing the transient snapshot'
                    )
                    self._attach.api().snapshotDelete(snapname)
                except spapi.ApiError as e:
                    LOG.error(
                        'Could not delete the %(name)s snapshot: %(err)s',
                        {'name': snapname, 'err': str(e)}
                    )

    def create_export(self, context, volume, connector):
        if self._connector_wants_iscsi(connector):
            LOG.debug('- creating an iSCSI export')
            self._create_iscsi_export(volume, connector)

    def remove_export(self, context, volume):
        pass

    def _attach_volume(self, context, volume, properties, remote=False):
        if self.configuration.iscsi_cinder_volume and not remote:
            LOG.debug('- adding the "storpool_wants_iscsi" flag')
            properties['storpool_wants_iscsi'] = True

        return super()._attach_volume(context, volume, properties, remote)

    def delete_volume(self, volume):
        name = self._attach.volumeName(volume['id'])
        try:
            self._attach.api().volumesReassign(
                json=[{"volume": name, "detach": "all"}])
            self._attach.api().volumeDelete(name)
        except spapi.ApiError as e:
            if e.name == 'objectDoesNotExist':
                pass
            else:
                raise self._backendException(e)

    def delete_snapshot(self, snapshot):
        name = self._attach.snapshotName('snap', snapshot['id'])
        try:
            self._attach.api().volumesReassign(
                json=[{"snapshot": name, "detach": "all"}])
            self._attach.api().snapshotDelete(name)
        except spapi.ApiError as e:
            if e.name == 'objectDoesNotExist':
                pass
            else:
                raise self._backendException(e)

    def check_for_setup_error(self):
        if storpool is None:
            msg = _('storpool libraries not found')
            raise exception.VolumeBackendAPIException(data=msg)

        self._attach = spopenstack.AttachDB(log=LOG)
        try:
            self._attach.api()
        except Exception as e:
            LOG.error("StorPoolDriver API initialization failed: %s", e)
            raise

        export_to = self.configuration.iscsi_export_to
        export_to_set = export_to is not None and export_to.split()
        vol_iscsi = self.configuration.iscsi_cinder_volume
        pg_name = self.configuration.iscsi_portal_group
        if (export_to_set or vol_iscsi) and pg_name is None:
            msg = _('The "iscsi_portal_group" option is required if '
                    'any patterns are listed in "iscsi_export_to"')
            raise exception.VolumeDriverException(message=msg)

        self._use_iscsi = export_to == "*"

    def _update_volume_stats(self):
        try:
            dl = self._attach.api().disksList()
            templates = self._attach.api().volumeTemplatesList()
        except spapi.ApiError as e:
            raise self._backendException(e)
        total = 0
        used = 0
        free = 0
        agSize = 512 * units.Mi
        for (id, desc) in dl.items():
            if desc.generationLeft != -1:
                continue
            total += desc.agCount * agSize
            used += desc.agAllocated * agSize
            free += desc.agFree * agSize * 4096 / (4096 + 128)

        # Report the free space as if all new volumes will be created
        # with StorPool replication 3; anything else is rare.
        free /= self.configuration.storpool_replication

        space = {
            'total_capacity_gb': total / units.Gi,
            'free_capacity_gb': free / units.Gi,
            'reserved_percentage': 0,
            'multiattach': not self._use_iscsi,
            'QoS_support': False,
            'thick_provisioning_support': False,
            'thin_provisioning_support': True,
        }

        pools = [dict(space, pool_name='default')]

        pools += [dict(space,
                       pool_name='template_' + t.name,
                       storpool_template=t.name
                       ) for t in templates]

        self._stats = {
            # Basic driver properties
            'volume_backend_name': self.configuration.safe_get(
                'volume_backend_name') or 'storpool',
            'vendor_name': 'StorPool',
            'driver_version': self.VERSION,
            'storage_protocol': (
                'iSCSI' if self._use_iscsi else 'storpool'
            ),
            # Driver capabilities
            'clone_across_pools': True,
            'sparse_copy_volume': True,
            # The actual pools data
            'pools': pools
        }

    def extend_volume(self, volume, new_size):
        size = int(new_size) * units.Gi
        name = self._attach.volumeName(volume['id'])
        try:
            upd = sptypes.VolumeUpdateDesc(size=size)
            self._attach.api().volumeUpdate(name, upd)
        except spapi.ApiError as e:
            raise self._backendException(e)

    def ensure_export(self, context, volume):
        # Already handled by Nova's AttachDB, we hope.
        # Maybe it should move here, but oh well.
        pass

    def retype(self, context, volume, new_type, diff, host):
        update = {}

        if diff['encryption']:
            LOG.error('Retype of encryption type not supported.')
            return False

        templ = self.configuration.storpool_template
        repl = self.configuration.storpool_replication
        if diff['extra_specs']:
            for (k, v) in diff['extra_specs'].items():
                if k == 'volume_backend_name':
                    if v[0] != v[1]:
                        # Retype of a volume backend not supported yet,
                        # the volume needs to be migrated.
                        return False
                elif k == 'storpool_template':
                    if v[0] != v[1]:
                        if v[1] is not None:
                            update['template'] = v[1]
                        elif templ is not None:
                            update['template'] = templ
                        else:
                            update['replication'] = repl
                elif k == ES_QOS:
                    if v[1] is None:
                        update['tags']['qc'] = ''
                    elif v[0] != v[1]:
                        update['tags'].update({'qc': v[1]})
                else:
                    # We ignore any extra specs that we do not know about.
                    # Let's leave it to Cinder's scheduler to not even
                    # get this far if there is any serious mismatch between
                    # the volume types.
                    pass

        if update:
            name = self._attach.volumeName(volume['id'])
            try:
                upd = sptypes.VolumeUpdateDesc(**update)
                self._attach.api().volumeUpdate(name, upd)
            except spapi.ApiError as e:
                raise self._backendException(e)

        return True

    def update_migrated_volume(self, context, volume, new_volume,
                               original_volume_status):
        orig_id = volume['id']
        orig_name = self._attach.volumeName(orig_id)
        temp_id = new_volume['id']
        temp_name = self._attach.volumeName(temp_id)
        vols = {v.name: True for v in self._attach.api().volumesList()}
        if temp_name not in vols:
            LOG.error('StorPool update_migrated_volume(): it seems '
                      'that the StorPool volume "%(tid)s" was not '
                      'created as part of the migration from '
                      '"%(oid)s".', {'tid': temp_id, 'oid': orig_id})
            return {'_name_id': new_volume['_name_id'] or new_volume['id']}

        if orig_name in vols:
            LOG.debug('StorPool update_migrated_volume(): both '
                      'the original volume "%(oid)s" and the migrated '
                      'StorPool volume "%(tid)s" seem to exist on '
                      'the StorPool cluster.',
                      {'oid': orig_id, 'tid': temp_id})
            int_name = temp_name + '--temp--mig'
            LOG.debug('Trying to swap the volume names, intermediate "%(int)s"',
                      {'int': int_name})
            try:
                LOG.debug('- rename "%(orig)s" to "%(int)s"',
                    {'orig': orig_name, 'int': int_name})
                self._attach.api().volumeUpdate(orig_name,
                                                {'rename': int_name})

                LOG.debug('- rename "%(temp)s" to "%(orig)s"',
                    {'temp': temp_name, 'orig': orig_name})
                self._attach.api().volumeUpdate(temp_name,
                                                {'rename': orig_name})

                LOG.debug('- rename "%(int)s" to "%(temp)s"',
                    {'int': int_name, 'temp': temp_name})
                self._attach.api().volumeUpdate(int_name,
                                                {'rename': temp_name})
                return {'_name_id': None}
            except spapi.ApiError as e:
                LOG.error('StorPool update_migrated_volume(): '
                          'could not rename a volume: '
                          '%(err)s',
                          {'err': e})
                return {'_name_id': new_volume['_name_id'] or new_volume['id']}

        try:
            self._attach.api().volumeUpdate(temp_name,
                                            {'rename': orig_name})
            return {'_name_id': None}
        except spapi.ApiError as e:
            LOG.error('StorPool update_migrated_volume(): '
                      'could not rename %(tname)s to %(oname)s: '
                      '%(err)s',
                      {'tname': temp_name, 'oname': orig_name, 'err': e})
            return {'_name_id': new_volume['_name_id'] or new_volume['id']}

    def revert_to_snapshot(self, context, volume, snapshot):
        volname = self._attach.volumeName(volume['id'])
        snapname = self._attach.snapshotName('snap', snapshot['id'])
        try:
            rev = sptypes.VolumeRevertDesc(toSnapshot=snapname)
            self._attach.api().volumeRevert(volname, rev)
        except spapi.ApiError as e:
            LOG.error('StorPool revert_to_snapshot(): could not revert '
                      'the %(vol_id)s volume to the %(snap_id)s snapshot: '
                      '%(err)s',
                      {'vol_id': volume['id'],
                       'snap_id': snapshot['id'],
                       'err': e})
            raise self._backendException(e)
