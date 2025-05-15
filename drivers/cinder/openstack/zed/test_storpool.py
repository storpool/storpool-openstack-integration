# Copyright 2014 - 2017, 2019  StorPool
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


from __future__ import annotations

import dataclasses
import itertools
import re
import sys
from typing import Any, NamedTuple, TYPE_CHECKING  # noqa: H301
from unittest import mock

import ddt
from oslo_utils import units

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


fakeStorPool = mock.Mock()
fakeStorPool.spopenstack = mock.Mock()
fakeStorPool.spapi = mock.Mock()
fakeStorPool.spconfig = mock.Mock()
fakeStorPool.sptypes = mock.Mock()
sys.modules['storpool'] = fakeStorPool


from cinder.common import constants
from cinder import exception
from cinder.tests.unit import fake_constants as fconst
from cinder.tests.unit import test
from cinder.volume import configuration as conf
from cinder.volume.drivers import storpool as driver


_ISCSI_IQN_OURS = 'beleriand'
_ISCSI_IQN_OTHER = 'rohan'
_ISCSI_IQN_THIRD = 'gondor'
_ISCSI_PAT_OTHER = 'roh*'
_ISCSI_PAT_BOTH = '*riand roh*'
_ISCSI_PORTAL_GROUP = 'openstack_pg'

volume_types = {
    fconst.VOLUME_TYPE_ID: {},
    fconst.VOLUME_TYPE2_ID: {'storpool_template': 'ssd'},
    fconst.VOLUME_TYPE3_ID: {'storpool_template': 'hdd'},
    fconst.VOLUME_TYPE4_ID:
        {'storpool_template': 'ssd2', 'storpool:qos_class': 'tier0'},
    fconst.VOLUME_TYPE5_ID:
        {'storpool_template': 'hdd2', 'storpool:qos_class': 'tier1'},
    fconst.VOLUME_TYPE6_ID: {'storpool:qos_class': 'tier1'}
}
volumes = {}
snapshots = {}


def MockExtraSpecs(vtype):
    return volume_types[vtype]


def mock_volume_types(f):
    def _types_inner_inner1(inst, *args, **kwargs):
        @mock.patch('cinder.volume.volume_types.get_volume_type_extra_specs',
                    new=MockExtraSpecs)
        def _types_inner_inner2():
            return f(inst, *args, **kwargs)

        return _types_inner_inner2()

    return _types_inner_inner1


def volumeName(vid):
    return 'os--volume--{id}'.format(id=vid)


def snapshotName(vtype, vid):
    return 'os--snap--{t}--{id}'.format(t=vtype, id=vid)


def targetName(vid):
    return 'iqn.2012-11.storpool:{id}'.format(id=vid)


class MockDisk(object):
    def __init__(self, diskId):
        self.id = diskId
        self.generationLeft = -1
        self.agCount = 14
        self.agFree = 12
        self.agAllocated = 1


class MockVolume(object):
    def __init__(self, v):
        self.name = v['name']


class MockTemplate(object):
    def __init__(self, name):
        self.name = name


class MockApiError(Exception):
    def __init__(self, msg):
        super(MockApiError, self).__init__(msg)


class MockAPI(object):
    def __init__(self):
        self._disks = {diskId: MockDisk(diskId) for diskId in (1, 2, 3, 4)}
        self._disks[3].generationLeft = 42

        self._templates = [MockTemplate(name) for name in ('ssd', 'hdd')]

    def setlog(self, log):
        self._log = log

    def disksList(self):
        return self._disks

    def snapshotCreate(self, vname, snap):
        snapshots[snap['name']] = dict(volumes[vname])

    def snapshotUpdate(self, snap, data):
        sdata = snapshots[snap]
        sdata.update(data)

    def snapshotDelete(self, name):
        del snapshots[name]

    def volumeCreate(self, vol):
        name = vol['name']
        if name in volumes:
            raise MockApiError('volume already exists')
        data = dict(vol)

        if 'parent' in vol and 'template' not in vol:
            sdata = snapshots[vol['parent']]
            if 'template' in sdata:
                data['template'] = sdata['template']

        if 'baseOn' in vol and 'template' not in vol:
            vdata = volumes[vol['baseOn']]
            if 'template' in vdata:
                data['template'] = vdata['template']

        if 'template' not in data:
            data['template'] = None

        volumes[name] = data

    def volumeDelete(self, name):
        del volumes[name]

    def volumesList(self):
        return [MockVolume(v[1]) for v in volumes.items()]

    def volumeTemplatesList(self):
        return self._templates

    def volumesReassign(self, json):
        pass

    def volumeUpdate(self, name, data):
        if 'size' in data:
            volumes[name]['size'] = data['size']

        if 'tags' in data:
            if 'tags' not in volumes[name]:
                volumes[name]['tags'] = {}
            for tag_name, tag_value in data['tags'].items():
                volumes[name]['tags'][tag_name] = tag_value

        if 'rename' in data and data['rename'] != name:
            new_name = data['rename']
            volumes[new_name] = volumes[name]
            if volumes[new_name]['name'] == name:
                volumes[new_name]['name'] = new_name
            del volumes[name]

    def volumeRevert(self, name, data):
        if name not in volumes:
            raise MockApiError('No such volume {name}'.format(name=name))

        snapname = data['toSnapshot']
        if snapname not in snapshots:
            raise MockApiError('No such snapshot {name}'.format(name=snapname))

        volumes[name] = dict(snapshots[snapname])


class MockAttachDB(object):
    def __init__(self, log):
        self._api = MockAPI()

    def api(self):
        return self._api

    def volumeName(self, vid):
        return volumeName(vid)

    def snapshotName(self, vtype, vid):
        return snapshotName(vtype, vid)


def MockVolumeRevertDesc(toSnapshot):
    return {'toSnapshot': toSnapshot}


def MockVolumeUpdateDesc(size = None, tags = None):
    volume_update = {}
    if size is not None:
        volume_update['size'] = size
    if tags is not None:
        volume_update['tags'] = tags
    return volume_update


@dataclasses.dataclass(frozen=True)
class MockIscsiNetwork:
    """Mock a StorPool IP CIDR network definition (partially)."""

    address: str


@dataclasses.dataclass(frozen=True)
class MockIscsiPortalGroup:
    """Mock a StorPool iSCSI portal group definition (partially)."""

    name: str
    networks: list[MockIscsiNetwork]


@dataclasses.dataclass(frozen=True)
class MockIscsiExport:
    """Mock a StorPool iSCSI exported volume/target definition."""

    portalGroup: str
    target: str


@dataclasses.dataclass(frozen=True)
class MockIscsiInitiator:
    """Mock a StorPool iSCSI initiator definition."""

    name: str
    exports: list[MockIscsiExport]


@dataclasses.dataclass(frozen=True)
class MockIscsiTarget:
    """Mock a StorPool iSCSI volume-to-target mapping definition."""

    name: str
    volume: str


class IscsiTestCase(NamedTuple):
    """A single test case for the iSCSI config and export methods."""

    initiator: str | None
    volume: str | None
    exported: bool
    commands_count: int


@dataclasses.dataclass(frozen=True)
class MockIscsiConfig:
    """Mock the structure returned by the "get current config" query."""

    portalGroups: dict[str, MockIscsiPortalGroup]
    initiators: dict[str, MockIscsiInitiator]
    targets: dict[str, MockIscsiTarget]

    @classmethod
    def build(cls, tcase: IscsiTestCase) -> Self:
        """Build a test config structure."""
        initiators = {
            '0': MockIscsiInitiator(name=_ISCSI_IQN_OTHER, exports=[]),
        }
        if tcase.initiator is not None:
            initiators['1'] = MockIscsiInitiator(
                name=tcase.initiator,
                exports=(
                    [
                        MockIscsiExport(
                            portalGroup=_ISCSI_PORTAL_GROUP,
                            target=targetName(tcase.volume),
                        ),
                    ]
                    if tcase.exported
                    else []
                ),
            )

        targets = {
            '0': MockIscsiTarget(
                name=targetName(fconst.VOLUME2_ID),
                volume=volumeName(fconst.VOLUME2_ID),
            ),
        }
        if tcase.volume is not None:
            targets['1'] = MockIscsiTarget(
                name=targetName(tcase.volume),
                volume=volumeName(tcase.volume),
            )

        return cls(
            portalGroups={
                '0': MockIscsiPortalGroup(
                    name=_ISCSI_PORTAL_GROUP + '-not',
                    networks=[],
                ),
                '1': MockIscsiPortalGroup(
                    name=_ISCSI_PORTAL_GROUP,
                    networks=[
                        MockIscsiNetwork(address="192.0.2.0"),
                        MockIscsiNetwork(address="195.51.100.0"),
                    ],
                ),
            },
            initiators=initiators,
            targets=targets,
        )


@dataclasses.dataclass(frozen=True)
class MockIscsiConfigTop:
    """Mock the top level of the "get the iSCSI configuration" response."""

    iscsi: MockIscsiConfig


class MockIscsiAPI:
    """Mock only the iSCSI-related calls of the StorPool API bindings."""

    _asrt: test.TestCase
    _configs: list[MockIscsiConfig]

    def __init__(
        self,
        configs: list[MockIscsiConfig],
        asrt: test.TestCase,
    ) -> None:
        """Store the reference to the list of iSCSI config objects."""
        self._asrt = asrt
        self._configs = configs

    def iSCSIConfig(self) -> MockIscsiConfigTop:
        """Return the last version of the iSCSI configuration."""
        return MockIscsiConfigTop(iscsi=self._configs[-1])

    def _handle_export(
        self,
        cfg: MockIscsiConfig, cmd: dict[str, Any],
    ) -> MockIscsiConfig:
        """Add an export for an initiator."""
        self._asrt.assertDictEqual(
            cmd,
            {
                'initiator': _ISCSI_IQN_OURS,
                'portalGroup': _ISCSI_PORTAL_GROUP,
                'volumeName': volumeName(fconst.VOLUME_ID),
            },
        )
        self._asrt.assertEqual(cfg.initiators['1'].name, cmd['initiator'])
        self._asrt.assertListEqual(cfg.initiators['1'].exports, [])

        return dataclasses.replace(
            cfg,
            initiators={
                **cfg.initiators,
                '1': dataclasses.replace(
                    cfg.initiators['1'],
                    exports=[
                        MockIscsiExport(
                            portalGroup=cmd['portalGroup'],
                            target=targetName(fconst.VOLUME_ID),
                        ),
                    ],
                ),
            },
        )

    def _handle_delete_export(
        self,
        cfg: MockIscsiConfig,
        cmd: dict[str, Any],
    ) -> MockIscsiConfig:
        """Delete an export for an initiator."""
        self._asrt.assertDictEqual(
            cmd,
            {
                'initiator': _ISCSI_IQN_OURS,
                'portalGroup': _ISCSI_PORTAL_GROUP,
                'volumeName': volumeName(fconst.VOLUME_ID),
            },
        )
        self._asrt.assertEqual(cfg.initiators['1'].name, cmd['initiator'])
        self._asrt.assertListEqual(
            cfg.initiators['1'].exports,
            [MockIscsiExport(portalGroup=_ISCSI_PORTAL_GROUP,
                             target=cfg.targets['1'].name)])

        updated_initiators = cfg.initiators
        del updated_initiators['1']
        return dataclasses.replace(cfg, initiators=updated_initiators)

    def _handle_create_initiator(
        self,
        cfg: MockIscsiConfig,
        cmd: dict[str, Any],
    ) -> MockIscsiConfig:
        """Add a whole new initiator."""
        self._asrt.assertDictEqual(
            cmd,
            {
                'name': _ISCSI_IQN_OURS,
                'username': '',
                'secret': '',
            },
        )
        self._asrt.assertNotIn(
            cmd['name'],
            [init.name for init in cfg.initiators.values()],
        )
        self._asrt.assertListEqual(sorted(cfg.initiators), ['0'])

        return dataclasses.replace(
            cfg,
            initiators={
                **cfg.initiators,
                '1': MockIscsiInitiator(name=cmd['name'], exports=[]),
            },
        )

    def _handle_create_target(
        self,
        cfg: MockIscsiConfig,
        cmd: dict[str, Any],
    ) -> MockIscsiConfig:
        """Add a target for a volume so that it may be exported."""
        self._asrt.assertDictEqual(
            cmd,
            {'volumeName': volumeName(fconst.VOLUME_ID)},
        )
        self._asrt.assertListEqual(sorted(cfg.targets), ['0'])
        return dataclasses.replace(
            cfg,
            targets={
                **cfg.targets,
                '1': MockIscsiTarget(
                    name=targetName(fconst.VOLUME_ID),
                    volume=volumeName(fconst.VOLUME_ID),
                ),
            },
        )

    def _handle_delete_target(
        self,
        cfg: MockIscsiConfig,
        cmd: dict[str, Any]
    ) -> MockIscsiConfig:
        """Remove a target for a volume."""
        self._asrt.assertDictEqual(
            cmd,
            {'volumeName': volumeName(fconst.VOLUME_ID)},
        )

        self._asrt.assertListEqual(sorted(cfg.targets), ['0', '1'])
        updated_targets = cfg.targets
        del updated_targets['1']
        return dataclasses.replace(cfg, targets=updated_targets)

    def _handle_initiator_add_network(
        self,
        cfg: MockIscsiConfig,
        cmd: dict[str, Any],
    ) -> MockIscsiConfig:
        """Add a network that an initiator is allowed to log in from."""
        self._asrt.assertDictEqual(
            cmd,
            {
                'initiator': _ISCSI_IQN_OURS,
                'net': '0.0.0.0/0',
            },
        )
        return dataclasses.replace(cfg)

    _CMD_HANDLERS = {
        'createInitiator': _handle_create_initiator,
        'createTarget': _handle_create_target,
        'deleteTarget': _handle_delete_target,
        'export': _handle_export,
        'exportDelete': _handle_delete_export,
        'initiatorAddNetwork': _handle_initiator_add_network,
    }

    def iSCSIConfigChange(
        self,
        commands: dict[str, list[dict[str, dict[str, Any]]]],
    ) -> None:
        """Apply the requested changes to the iSCSI configuration.

        This method adds a new config object to the configs list,
        making a shallow copy of the last one and applying the changes
        specified in the list of commands.
        """
        self._asrt.assertListEqual(sorted(commands), ['commands'])
        self._asrt.assertGreater(len(commands['commands']), 0)
        for cmd in commands['commands']:
            keys = sorted(cmd.keys())
            cmd_name = keys[0]
            self._asrt.assertListEqual(keys, [cmd_name])
            handler = self._CMD_HANDLERS[cmd_name]
            new_cfg = handler(self, self._configs[-1], cmd[cmd_name])
            self._configs.append(new_cfg)


_ISCSI_TEST_CASES = [
    IscsiTestCase(None, None, False, 4),
    IscsiTestCase(_ISCSI_IQN_OURS, None, False, 2),
    IscsiTestCase(_ISCSI_IQN_OURS, fconst.VOLUME_ID, False, 1),
    IscsiTestCase(_ISCSI_IQN_OURS, fconst.VOLUME_ID, True, 0),
]


def MockSPConfig(section = 's01'):
    res = {}
    m = re.match('^s0*([A-Za-z0-9]+)$', section)
    if m:
        res['SP_OURID'] = m.group(1)
    return res


fakeStorPool.spapi.ApiError = MockApiError
fakeStorPool.spconfig.SPConfig = MockSPConfig
fakeStorPool.spopenstack.AttachDB = MockAttachDB
fakeStorPool.sptypes.VolumeRevertDesc = MockVolumeRevertDesc
fakeStorPool.sptypes.VolumeUpdateDesc = MockVolumeUpdateDesc


class MockVolumeDB(object):
    """Simulate a Cinder database with a volume_get() method."""

    def __init__(self, vol_types=None):
        """Store the specified volume types mapping if necessary."""
        self.vol_types = vol_types if vol_types is not None else {}

    def volume_get(self, _context, vid):
        """Get a volume-like structure, only the fields we care about."""
        # Still, try to at least make sure we know about that volume
        return {
            'id': vid,
            'size': volumes[volumeName(vid)]['size'],
            'volume_type': self.vol_types.get(vid),
        }


@ddt.ddt
class StorPoolTestCase(test.TestCase):

    def setUp(self):
        super(StorPoolTestCase, self).setUp()

        self.cfg = mock.Mock(spec=conf.Configuration)
        self.cfg.volume_backend_name = 'storpool_test'
        self.cfg.storpool_template = None
        self.cfg.storpool_replication = 3
        self.cfg.iscsi_cinder_volume = False
        self.cfg.iscsi_export_to = ''
        self.cfg.iscsi_learn_initiator_iqns = True
        self.cfg.iscsi_portal_group = _ISCSI_PORTAL_GROUP

        self._setup_test_driver()

    def _setup_test_driver(self):
        """Initialize a StorPool driver as per the current configuration."""
        mock_exec = mock.Mock()
        mock_exec.return_value = ('', '')

        self.driver = driver.StorPoolDriver(execute=mock_exec,
                                            configuration=self.cfg)
        self.driver.check_for_setup_error()

    @ddt.data(
        (5, (TypeError, AttributeError)),
        ({'no-host': None}, KeyError),
        ({'host': 'sbad'}, driver.StorPoolConfigurationInvalid),
        ({'host': 's01'}, None),
        ({'host': 'none'}, None),
    )
    @ddt.unpack
    def test_validate_connector(self, conn, exc):
        if exc is None:
            self.assertTrue(self.driver.validate_connector(conn))
        else:
            self.assertRaises(exc,
                              self.driver.validate_connector,
                              conn)

    @ddt.data(
        (5, (TypeError, AttributeError)),
        ({'no-host': None}, KeyError),
        ({'host': 'sbad'}, driver.StorPoolConfigurationInvalid),
    )
    @ddt.unpack
    def test_initialize_connection_bad(self, conn, exc):
        self.assertRaises(exc,
                          self.driver.initialize_connection,
                          None, conn)

    @ddt.data(
        (1, '42', 's01'),
        (2, '616', 's02'),
        (65, '1610', 'none'),
    )
    @ddt.unpack
    def test_initialize_connection_good(self, cid, hid, name):
        c = self.driver.initialize_connection({'id': hid}, {'host': name})
        self.assertEqual('storpool', c['driver_volume_type'])
        self.assertDictEqual({'client_id': cid, 'volume': hid,
                              'access_mode': 'rw'},
                             c['data'])

    def test_noop_functions(self):
        self.driver.terminate_connection(None, None)
        self.driver.create_export(None, None, {})
        self.driver.remove_export(None, None)

    @ddt.data(*[{'name': 'volume-' + str(key),
                 'volume_type': {'id': key, 'extra_specs': val}}
                for key, val in sorted(volume_types.items())])
    @mock_volume_types
    def test_get_qos_from_volume(self, volume):
        expected = None
        if volume['volume_type']['extra_specs']:
            expected = (volume['volume_type']['extra_specs']
                        .get('storpool:qos_class', None))

        actual = driver.StorPoolDriver.qos_from_volume(volume)

        self.assertEqual(expected, actual)

    def test_stats(self):
        stats = self.driver.get_volume_stats(refresh=True)
        self.assertEqual('StorPool', stats['vendor_name'])
        self.assertEqual('storpool', stats['storage_protocol'])
        self.assertListEqual(['default', 'template_hdd', 'template_ssd'],
                             sorted([p['pool_name'] for p in stats['pools']]))
        r = re.compile(r'^template_([A-Za-z0-9_]+)$')
        for pool in stats['pools']:
            self.assertEqual(21, pool['total_capacity_gb'])
            self.assertEqual(5, int(pool['free_capacity_gb']))

            self.assertFalse(pool['multiattach'])
            self.assertFalse(pool['QoS_support'])
            self.assertFalse(pool['thick_provisioning_support'])
            self.assertTrue(pool['thin_provisioning_support'])

            if pool['pool_name'] != 'default':
                m = r.match(pool['pool_name'])
                self.assertIsNotNone(m)
                self.assertIsNotNone(m.group(1))
                self.assertEqual(m.group(1), pool['storpool_template'])

    def assertVolumeNames(self, names):
        self.assertListEqual(sorted([volumeName(n) for n in names]),
                             sorted(volumes.keys()))
        self.assertListEqual(sorted([volumeName(n) for n in names]),
                             sorted(data['name'] for data in volumes.values()))

    def assertSnapshotNames(self, specs):
        self.assertListEqual(
            sorted(snapshotName(spec[0], spec[1]) for spec in specs),
            sorted(snapshots.keys()))

    @mock_volume_types
    def test_create_delete_volume(self):
        volume_types_list = [{'id': key, 'extra_specs': val}
                             for key, val in volume_types.items()]

        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        self.driver.create_volume({'id': '1', 'name': 'v1', 'size': 1,
                                   'volume_type': volume_types_list[0]})
        self.assertCountEqual([volumeName('1')], volumes.keys())
        self.assertVolumeNames(('1',))
        v = volumes[volumeName('1')]
        self.assertEqual(1 * units.Gi, v['size'])
        self.assertIsNone(v['template'])
        self.assertEqual(3, v['replication'])
        self.assertIsNone(v.get('tags'))

        caught = False
        try:
            self.driver.create_volume({'id': '1', 'name': 'v1', 'size': 0,
                                       'volume_type': volume_types_list[0]})
        except exception.VolumeBackendAPIException:
            caught = True
        self.assertTrue(caught)

        self.driver.delete_volume({'id': '1'})
        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)

        self.driver.create_volume({'id': '1', 'name': 'v1', 'size': 2,
                                   'volume_type': volume_types_list[0]})
        self.assertVolumeNames(('1',))
        v = volumes[volumeName('1')]
        self.assertEqual(2 * units.Gi, v['size'])
        self.assertIsNone(v['template'])
        self.assertEqual(3, v['replication'])
        self.assertIsNone(v.get('tags'))

        self.driver.create_volume({'id': '2', 'name': 'v2', 'size': 3,
                                   'volume_type': volume_types_list[0]})
        self.assertVolumeNames(('1', '2'))
        v = volumes[volumeName('2')]
        self.assertEqual(3 * units.Gi, v['size'])
        self.assertIsNone(v['template'])
        self.assertEqual(3, v['replication'])
        self.assertIsNone(v.get('tags'))

        self.driver.create_volume({'id': '3', 'name': 'v2', 'size': 4,
                                   'volume_type': volume_types_list[1]})
        self.assertVolumeNames(('1', '2', '3'))
        v = volumes[volumeName('3')]
        self.assertEqual(4 * units.Gi, v['size'])
        self.assertEqual('ssd', v['template'])
        self.assertNotIn('replication', v.keys())
        self.assertIsNone(v.get('tags'))

        self.driver.create_volume({'id': '4', 'name': 'v2', 'size': 5,
                                   'volume_type': volume_types_list[2]})
        self.assertVolumeNames(('1', '2', '3', '4'))
        v = volumes[volumeName('4')]
        self.assertEqual(5 * units.Gi, v['size'])
        self.assertEqual('hdd', v['template'])
        self.assertNotIn('replication', v.keys())
        self.assertIsNone(v.get('tags'))

        self.driver.create_volume({'id': '5', 'name': 'v5', 'size': 6,
                                   'volume_type': volume_types_list[3]})
        self.assertVolumeNames(('1', '2', '3', '4', '5'))
        v = volumes[volumeName('5')]
        self.assertEqual(6 * units.Gi, v['size'])
        self.assertEqual('ssd2', v['template'])
        self.assertNotIn('replication', v.keys())
        self.assertEqual(
            volume_types_list[3]['extra_specs']['storpool:qos_class'],
            v['tags']['qc'])

        self.driver.create_volume({'id': '6', 'name': 'v6', 'size': 7,
                                   'volume_type': volume_types_list[4]})
        self.assertVolumeNames(('1', '2', '3', '4', '5', '6'))
        v = volumes[volumeName('6')]
        self.assertEqual(7 * units.Gi, v['size'])
        self.assertEqual('hdd2', v['template'])
        self.assertNotIn('replication', v.keys())
        self.assertEqual(
            volume_types_list[4]['extra_specs']['storpool:qos_class'],
            v['tags']['qc'])

        self.driver.create_volume({'id': '7', 'name': 'v7', 'size': 8,
                                   'volume_type': volume_types_list[5]})
        self.assertVolumeNames(('1', '2', '3', '4', '5', '6', '7'))
        v = volumes[volumeName('7')]
        self.assertEqual(8 * units.Gi, v['size'])
        self.assertIsNone(v['template'])
        self.assertEqual(3, v['replication'])
        self.assertEqual(
            volume_types_list[5]['extra_specs']['storpool:qos_class'],
            v['tags']['qc'])

        # Make sure the dictionary is not corrupted somehow...
        v = volumes[volumeName('1')]
        self.assertEqual(2 * units.Gi, v['size'])
        self.assertIsNone(v['template'])
        self.assertEqual(3, v['replication'])

        for vid in ('1', '2', '3', '4', '5', '6', '7'):
            self.driver.delete_volume({'id': vid})
        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

    @mock_volume_types
    def test_update_migrated_volume(self):
        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        # Create two volumes
        self.driver.create_volume(
            {'id': '1', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE_ID}})
        self.driver.create_volume(
            {'id': '2', 'name': 'v2', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE_ID}})
        self.assertCountEqual([volumeName('1'), volumeName('2')],
                              volumes.keys())
        self.assertVolumeNames(('1', '2',))

        # Failure: the "migrated" volume does not even exist
        res = self.driver.update_migrated_volume(None, {'id': '1'},
                                                 {'id': '3', '_name_id': '1'},
                                                 'available')
        self.assertDictEqual({'_name_id': '1'}, res)

        # Success: rename the migrated volume to match the original
        res = self.driver.update_migrated_volume(None, {'id': '3'},
                                                 {'id': '2', '_name_id': '3'},
                                                 'available')
        self.assertDictEqual({'_name_id': None}, res)
        self.assertCountEqual([volumeName('1'), volumeName('3')],
                              volumes.keys())
        self.assertVolumeNames(('1', '3',))

        # Success: swap volume names with an existing volume
        res = self.driver.update_migrated_volume(None, {'id': '1'},
                                                 {'id': '3', '_name_id': '1'},
                                                 'available')
        self.assertDictEqual({'_name_id': None}, res)
        self.assertCountEqual([volumeName('1'), volumeName('3')],
                              volumes.keys())
        self.assertVolumeNames(('1', '3',))

        for vid in ('1', '3'):
            self.driver.delete_volume({'id': vid})
        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

    @mock_volume_types
    def test_clone_extend_volume(self):
        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        self.driver.create_volume(
            {'id': '1', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE_ID}})
        self.assertVolumeNames(('1',))
        self.driver.extend_volume({'id': '1'}, 2)
        self.assertEqual(2 * units.Gi, volumes[volumeName('1')]['size'])

        with mock.patch.object(self.driver, 'db', new=MockVolumeDB()):
            self.driver.create_cloned_volume(
                {
                    'id': '2',
                    'name': 'clo',
                    'size': 3,
                    'volume_type': {'id': fconst.VOLUME_TYPE_ID}
                },
                {'id': 1})
        self.assertVolumeNames(('1', '2'))
        self.assertDictEqual({}, snapshots)
        # We do not provide a StorPool template name in either of the volumes'
        # types, so create_cloned_volume() should take the baseOn shortcut.
        vol2 = volumes[volumeName('2')]
        self.assertEqual(vol2['baseOn'], volumeName('1'))
        self.assertNotIn('parent', vol2)

        self.driver.delete_volume({'id': 1})
        self.driver.delete_volume({'id': 2})

        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

    @ddt.data(*itertools.product(
        [
            {
                'id': key,
                'extra_specs': val
            } for key, val in sorted(volume_types.items())],
        [
            {
                'id': key,
                'extra_specs': val
            } for key, val in sorted(volume_types.items())
        ]
    ))
    @ddt.unpack
    @mock_volume_types
    def test_create_cloned_volume(self, src_type, dst_type):
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        src_template = src_type['extra_specs'].get('storpool_template')
        dst_template = dst_type['extra_specs'].get('storpool_template')
        src_name = 's-none' if src_template is None else 's-' + src_template
        dst_name = 'd-none' if dst_template is None else 'd-' + dst_template

        snap_name = snapshotName('clone', '2')

        vdata1 = {
            'id': '1',
            'name': src_name,
            'size': 1,
            'volume_type': src_type,
        }
        self.assertEqual(
            self.driver._template_from_volume(vdata1),
            src_template)
        self.driver.create_volume(vdata1)
        self.assertVolumeNames(('1',))
        v = volumes[volumeName('1')]
        src_qos_class_expected = (
            src_type['extra_specs'].get('storpool:qos_class'))
        if src_qos_class_expected is None:
            self.assertIsNone(v.get('tags'))
        else:
            self.assertEqual(src_qos_class_expected, v['tags']['qc'])

        vdata2 = {
            'id': 2,
            'name': dst_name,
            'size': 1,
            'volume_type': dst_type,
        }
        self.assertEqual(
            self.driver._template_from_volume(vdata2),
            dst_template)
        with mock.patch.object(self.driver, 'db',
                               new=MockVolumeDB(vol_types={'1': src_type})):
            self.driver.create_cloned_volume(vdata2, {'id': '1'})
        self.assertVolumeNames(('1', '2'))
        vol2 = volumes[volumeName('2')]
        self.assertEqual(vol2['template'], dst_template)
        dst_qos_class_expected = (
            dst_type['extra_specs'].get('storpool:qos_class'))
        if dst_qos_class_expected is None:
            self.assertIsNone(vol2.get('tags'))
        else:
            self.assertEqual(dst_qos_class_expected, vol2['tags']['qc'])

        if src_template == dst_template:
            self.assertEqual(vol2['baseOn'], volumeName('1'))
            self.assertNotIn('parent', vol2)

            self.assertDictEqual({}, snapshots)
        else:
            self.assertNotIn('baseOn', vol2)
            self.assertEqual(vol2['parent'], snap_name)

            self.assertSnapshotNames((('clone', '2'),))
            self.assertEqual(snapshots[snap_name]['template'], dst_template)

        self.driver.delete_volume({'id': '1'})
        self.driver.delete_volume({'id': '2'})
        if src_template != dst_template:
            del snapshots[snap_name]

        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

    @mock_volume_types
    def test_config_replication(self):
        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        save_repl = self.driver.configuration.storpool_replication

        self.driver.configuration.storpool_replication = 3
        stats = self.driver.get_volume_stats(refresh=True)
        pool = stats['pools'][0]
        self.assertEqual(21, pool['total_capacity_gb'])
        self.assertEqual(5, int(pool['free_capacity_gb']))

        self.driver.create_volume(
            {'id': 'cfgrepl1', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE_ID}})
        self.assertVolumeNames(('cfgrepl1',))
        v = volumes[volumeName('cfgrepl1')]
        self.assertEqual(3, v['replication'])
        self.assertIsNone(v['template'])
        self.driver.delete_volume({'id': 'cfgrepl1'})

        self.driver.configuration.storpool_replication = 2
        stats = self.driver.get_volume_stats(refresh=True)
        pool = stats['pools'][0]
        self.assertEqual(21, pool['total_capacity_gb'])
        self.assertEqual(8, int(pool['free_capacity_gb']))

        self.driver.create_volume(
            {'id': 'cfgrepl2', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE_ID}})
        self.assertVolumeNames(('cfgrepl2',))
        v = volumes[volumeName('cfgrepl2')]
        self.assertEqual(2, v['replication'])
        self.assertIsNone(v['template'])
        self.driver.delete_volume({'id': 'cfgrepl2'})

        self.driver.create_volume(
            {'id': 'cfgrepl3', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE2_ID}})
        self.assertVolumeNames(('cfgrepl3',))
        v = volumes[volumeName('cfgrepl3')]
        self.assertNotIn('replication', v)
        self.assertEqual('ssd', v['template'])
        self.driver.delete_volume({'id': 'cfgrepl3'})

        self.driver.configuration.storpool_replication = save_repl

        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

    @mock_volume_types
    def test_config_template(self):
        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        save_template = self.driver.configuration.storpool_template

        self.driver.configuration.storpool_template = None

        self.driver.create_volume(
            {'id': 'cfgtempl1', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE_ID}})
        self.assertVolumeNames(('cfgtempl1',))
        v = volumes[volumeName('cfgtempl1')]
        self.assertEqual(3, v['replication'])
        self.assertIsNone(v['template'])
        self.driver.delete_volume({'id': 'cfgtempl1'})

        self.driver.create_volume(
            {'id': 'cfgtempl2', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE2_ID}})
        self.assertVolumeNames(('cfgtempl2',))
        v = volumes[volumeName('cfgtempl2')]
        self.assertNotIn('replication', v)
        self.assertEqual('ssd', v['template'])
        self.driver.delete_volume({'id': 'cfgtempl2'})

        self.driver.configuration.storpool_template = 'hdd'

        self.driver.create_volume(
            {'id': 'cfgtempl3', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE_ID}})
        self.assertVolumeNames(('cfgtempl3',))
        v = volumes[volumeName('cfgtempl3')]
        self.assertNotIn('replication', v)
        self.assertEqual('hdd', v['template'])
        self.driver.delete_volume({'id': 'cfgtempl3'})

        self.driver.create_volume(
            {'id': 'cfgtempl4', 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE2_ID}})
        self.assertVolumeNames(('cfgtempl4',))
        v = volumes[volumeName('cfgtempl4')]
        self.assertNotIn('replication', v)
        self.assertEqual('ssd', v['template'])
        self.driver.delete_volume({'id': 'cfgtempl4'})

        self.driver.configuration.storpool_template = save_template

        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

    @ddt.data(
        # No volume type at all: 'default'
        ('default', None),
        # No storpool_template in the type extra specs: 'default'
        ('default', {'id': fconst.VOLUME_TYPE_ID}),
        # An actual template specified: 'template_*'
        ('template_ssd', {'id': fconst.VOLUME_TYPE2_ID}),
        ('template_hdd', {'id': fconst.VOLUME_TYPE3_ID}),
    )
    @ddt.unpack
    @mock_volume_types
    def test_get_pool(self, pool, volume_type):
        self.assertEqual(pool,
                         self.driver.get_pool({
                             'volume_type': volume_type
                         }))

    @mock_volume_types
    def test_volume_revert(self):
        vol_id = 'rev1'
        vol_name = volumeName(vol_id)
        snap_id = 'rev-s1'
        snap_name = snapshotName('snap', snap_id)

        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        self.driver.create_volume(
            {'id': vol_id, 'name': 'v1', 'size': 1,
             'volume_type': {'id': fconst.VOLUME_TYPE_ID}})
        self.assertVolumeNames((vol_id,))
        self.assertDictEqual({}, snapshots)

        self.driver.create_snapshot({'id': snap_id, 'volume_id': vol_id})
        self.assertVolumeNames((vol_id,))
        self.assertListEqual([snap_name], sorted(snapshots.keys()))
        self.assertDictEqual(volumes[vol_name], snapshots[snap_name])
        self.assertIsNot(volumes[vol_name], snapshots[snap_name])

        self.driver.extend_volume({'id': vol_id}, 2)
        self.assertVolumeNames((vol_id,))
        self.assertNotEqual(volumes[vol_name], snapshots[snap_name])

        self.driver.revert_to_snapshot(None, {'id': vol_id}, {'id': snap_id})
        self.assertVolumeNames((vol_id,))
        self.assertDictEqual(volumes[vol_name], snapshots[snap_name])
        self.assertIsNot(volumes[vol_name], snapshots[snap_name])

        self.driver.delete_snapshot({'id': snap_id})
        self.assertVolumeNames((vol_id,))
        self.assertDictEqual({}, snapshots)

        self.assertRaisesRegex(exception.VolumeBackendAPIException,
                               'No such snapshot',
                               self.driver.revert_to_snapshot, None,
                               {'id': vol_id}, {'id': snap_id})

        self.driver.delete_volume({'id': vol_id})
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        self.assertRaisesRegex(exception.VolumeBackendAPIException,
                               'No such volume',
                               self.driver.revert_to_snapshot, None,
                               {'id': vol_id}, {'id': snap_id})

    @ddt.data(
        # The default values
        ('', False, constants.STORPOOL, _ISCSI_IQN_OURS, False),

        # Export to all
        ('*', True, constants.ISCSI, _ISCSI_IQN_OURS, True),
        ('*', True, constants.ISCSI, _ISCSI_IQN_OURS, True),

        # Only export to the controller
        ('', False, constants.STORPOOL, _ISCSI_IQN_OURS, False),

        # Some of the not-fully-supported pattern lists
        (_ISCSI_PAT_OTHER, False, constants.STORPOOL, _ISCSI_IQN_OURS, False),
        (_ISCSI_PAT_OTHER, False, constants.STORPOOL, _ISCSI_IQN_OTHER, True),
        (_ISCSI_PAT_BOTH, False, constants.STORPOOL, _ISCSI_IQN_OURS, True),
        (_ISCSI_PAT_BOTH, False, constants.STORPOOL, _ISCSI_IQN_OTHER, True),
    )
    @ddt.unpack
    def test_wants_iscsi(self, iscsi_export_to, use_iscsi, storage_protocol,
                         hostname, expected):
        """Check the "should this export use iSCSI?" detection."""
        self.cfg.iscsi_export_to = iscsi_export_to
        self._setup_test_driver()
        self.assertEqual(self.driver._use_iscsi, use_iscsi)

        # Make sure the driver reports the correct protocol in the stats
        self.driver._update_volume_stats()
        self.assertEqual(self.driver._stats["vendor_name"], "StorPool")
        self.assertEqual(self.driver._stats["storage_protocol"],
                         storage_protocol)

        def check(conn, forced, expected):
            """Pass partially or completely valid connector info."""
            for initiator in (None, hostname):
                for host in (None, _ISCSI_IQN_THIRD):
                    self.assertEqual(
                        self.driver._connector_wants_iscsi({
                            "host": host,
                            "initiator": initiator,
                            **conn,
                        }),
                        expected if initiator is not None and host is not None
                        else forced)

        # If iscsi_cinder_volume is set and this is the controller, then yes.
        check({"storpool_wants_iscsi": True}, True, True)

        # If iscsi_cinder_volume is not set or this is not the controller, then
        # look at the specified expected value.
        check({"storpool_wants_iscsi": False}, use_iscsi, expected)
        check({}, use_iscsi, expected)

    def _validate_iscsi_config(
        self,
        cfg: MockIscsiConfig,
        res: dict[str, Any],
        tcase: IscsiTestCase,
    ) -> None:
        """Make sure the returned structure makes sense."""
        initiator = res['initiator']
        cfg_initiator = cfg.initiators.get('1')

        self.assertIs(res['cfg'].iscsi, cfg)
        self.assertEqual(res['pg'].name, _ISCSI_PORTAL_GROUP)

        if tcase.initiator is None:
            self.assertIsNone(initiator)
        else:
            self.assertIsNotNone(initiator)
        self.assertEqual(initiator, cfg_initiator)

        if tcase.volume is None:
            self.assertIsNone(res['target'])
        else:
            self.assertIsNotNone(res['target'])
        self.assertEqual(res['target'], cfg.targets.get('1'))

        if tcase.initiator is None:
            self.assertIsNone(cfg_initiator)
            self.assertIsNone(res['export'])
        else:
            self.assertIsNotNone(cfg_initiator)
            if tcase.exported:
                self.assertIsNotNone(res['export'])
                self.assertEqual(res['export'], cfg_initiator.exports[0])
            else:
                self.assertIsNone(res['export'])

    @ddt.data(*_ISCSI_TEST_CASES)
    def test_iscsi_get_config(self, tcase: IscsiTestCase) -> None:
        """Make sure the StorPool iSCSI configuration is parsed correctly."""
        cfg_orig = MockIscsiConfig.build(tcase)
        configs = [cfg_orig]
        iapi = MockIscsiAPI(configs, self)
        with mock.patch.object(self.driver._attach, 'api', new=lambda: iapi):
            res = self.driver._get_iscsi_config(
                _ISCSI_IQN_OURS,
                fconst.VOLUME_ID,
            )

        self._validate_iscsi_config(cfg_orig, res, tcase)

    @ddt.data(*_ISCSI_TEST_CASES)
    def test_iscsi_create_export(self, tcase: IscsiTestCase) -> None:
        """Make sure _create_iscsi_export() makes the right API calls."""
        cfg_orig = MockIscsiConfig.build(tcase)
        configs = [cfg_orig]
        iapi = MockIscsiAPI(configs, self)
        with mock.patch.object(self.driver._attach, 'api', new=lambda: iapi):
            self.driver._create_iscsi_export(
                {
                    'id': fconst.VOLUME_ID,
                    'display_name': fconst.VOLUME_NAME,
                },
                {
                    # Yeah, okay, so we cheat a little bit here...
                    'host': _ISCSI_IQN_OURS + '.hostname',
                    'initiator': _ISCSI_IQN_OURS,
                },
            )

        self.assertEqual(len(configs), tcase.commands_count + 1)
        cfg_final = configs[-1]
        self.assertEqual(cfg_final.initiators['1'].name, _ISCSI_IQN_OURS)
        self.assertEqual(
            cfg_final.initiators['1'].exports[0].target,
            targetName(fconst.VOLUME_ID),
        )
        self.assertEqual(
            cfg_final.targets['1'].volume,
            volumeName(fconst.VOLUME_ID),
        )

    @ddt.data(*_ISCSI_TEST_CASES)
    def test_remove_iscsi_export(self, tcase: IscsiTestCase):
        cfg_orig = MockIscsiConfig.build(tcase)
        configs = [cfg_orig]
        iapi = MockIscsiAPI(configs, self)

        def _target_exists(cfg: MockIscsiConfig, volume: str) -> bool:
            for name, target in cfg.targets.items():
                if target.volume == volumeName(volume):
                    return True
            return False

        def _export_exists(cfg: MockIscsiConfig, volume: str) -> bool:
            for name, initiator in cfg.initiators.items():
                for export in initiator.exports:
                    if export.target == targetName(volume):
                        return True
            return False

        if tcase.exported:
            self.assertTrue(
                _target_exists(iapi.iSCSIConfig().iscsi, tcase.volume))
            self.assertTrue(
                _export_exists(iapi.iSCSIConfig().iscsi, tcase.volume))

        with mock.patch.object(self.driver._attach, 'api', new=lambda: iapi):
            self.driver._remove_iscsi_export(
                {
                    'id': fconst.VOLUME_ID,
                    'display_name': fconst.VOLUME_NAME,
                },
                {
                    'host': _ISCSI_IQN_OURS + '.hostname',
                    'initiator': _ISCSI_IQN_OURS,
                },
            )

        self.assertFalse(
            _target_exists(iapi.iSCSIConfig().iscsi, tcase.volume))
        self.assertFalse(
            _export_exists(iapi.iSCSIConfig().iscsi, tcase.volume))

    @mock_volume_types
    def test_volume_retype(self):
        volume_types_list = [{'id': key, 'extra_specs': val}
                             for key, val in volume_types.items()]

        self.assertVolumeNames([])
        self.assertDictEqual({}, volumes)
        self.assertDictEqual({}, snapshots)

        self.driver.create_volume({'id': '1', 'name': 'v1', 'size': 1,
                                   'volume_type': volume_types_list[0]})
        self.assertNotIn('tags', volumes[volumeName('1')])

        volume = {'id': '1'}
        diff = {
            'encryption': None,
            'extra_specs': {
                'storpool:qos_class': [
                    None,
                    'tier1'
                ]
            }
        }
        self.driver.retype(None, volume, None, diff, None)
        self.assertEqual('tier1', volumes[volumeName('1')]['tags']['qc'])

        diff['extra_specs']['storpool:qos_class'] = ['tier1', 'tier2']
        self.driver.retype(None, volume, None, diff, None)
        self.assertEqual('tier2', volumes[volumeName('1')]['tags']['qc'])

        diff['extra_specs']['storpool:qos_class'] = ['tier1', None]
        self.driver.retype(None, volume, None, diff, None)
        self.assertEqual('', volumes[volumeName('1')]['tags']['qc'])
