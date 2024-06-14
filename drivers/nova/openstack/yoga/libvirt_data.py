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

import collections

from lxml import etree
from oslo_utils import units

from nova.objects.fields import Architecture
from nova.virt.libvirt import config


def fake_kvm_guest(iothread_count=0):
    obj = config.LibvirtConfigGuest()
    obj.virt_type = "kvm"
    obj.memory = 100 * units.Mi
    obj.vcpus = 2
    obj.cpuset = set([0, 1, 3, 4, 5])

    obj.cputune = config.LibvirtConfigGuestCPUTune()
    obj.cputune.shares = 100
    obj.cputune.quota = 50000
    obj.cputune.period = 25000

    obj.membacking = config.LibvirtConfigGuestMemoryBacking()
    page1 = config.LibvirtConfigGuestMemoryBackingPage()
    page1.size_kb = 2048
    page1.nodeset = [0, 1, 2, 3, 5]
    page2 = config.LibvirtConfigGuestMemoryBackingPage()
    page2.size_kb = 1048576
    page2.nodeset = [4]
    obj.membacking.hugepages.append(page1)
    obj.membacking.hugepages.append(page2)

    obj.memtune = config.LibvirtConfigGuestMemoryTune()
    obj.memtune.hard_limit = 496
    obj.memtune.soft_limit = 672
    obj.memtune.swap_hard_limit = 1638
    obj.memtune.min_guarantee = 2970

    obj.numatune = config.LibvirtConfigGuestNUMATune()

    numamemory = config.LibvirtConfigGuestNUMATuneMemory()
    numamemory.mode = "preferred"
    numamemory.nodeset = [0, 1, 2, 3, 8]

    obj.numatune.memory = numamemory

    numamemnode0 = config.LibvirtConfigGuestNUMATuneMemNode()
    numamemnode0.cellid = 0
    numamemnode0.mode = "preferred"
    numamemnode0.nodeset = [0, 1]

    numamemnode1 = config.LibvirtConfigGuestNUMATuneMemNode()
    numamemnode1.cellid = 1
    numamemnode1.mode = "preferred"
    numamemnode1.nodeset = [2, 3]

    numamemnode2 = config.LibvirtConfigGuestNUMATuneMemNode()
    numamemnode2.cellid = 2
    numamemnode2.mode = "preferred"
    numamemnode2.nodeset = [8]

    obj.numatune.memnodes.extend([numamemnode0,
                                  numamemnode1,
                                  numamemnode2])

    obj.name = "demo"
    obj.uuid = "b38a3f43-4be2-4046-897f-b67c2f5e0147"
    obj.os_type = "linux"
    obj.os_boot_dev = ["hd", "cdrom", "fd"]
    obj.os_smbios = config.LibvirtConfigGuestSMBIOS()
    obj.features = [
        config.LibvirtConfigGuestFeatureACPI(),
        config.LibvirtConfigGuestFeatureAPIC(),
        config.LibvirtConfigGuestFeatureKvmHidden(),
        config.LibvirtConfigGuestFeatureVMCoreInfo(),
    ]

    obj.sysinfo = config.LibvirtConfigGuestSysinfo()
    obj.sysinfo.bios_vendor = "Acme"
    obj.sysinfo.system_version = "1.0.0"

    obj.iothread_count = iothread_count

    # obj.devices[0]
    disk = config.LibvirtConfigGuestDisk()
    disk.source_type = "file"
    disk.source_path = "/tmp/disk-img"
    disk.target_dev = "vda"
    disk.target_bus = "virtio"
    disk.iothread_count = iothread_count
    obj.add_device(disk)

    # obj.devices[1]
    disk = config.LibvirtConfigGuestDisk()
    disk.source_device = "cdrom"
    disk.source_type = "file"
    disk.source_path = "/tmp/cdrom-img"
    disk.target_dev = "sda"
    disk.target_bus = "sata"
    disk.iothread_count = iothread_count
    obj.add_device(disk)

    # obj.devices[2]
    intf = config.LibvirtConfigGuestInterface()
    intf.net_type = "network"
    intf.mac_addr = "52:54:00:f6:35:8f"
    intf.model = "virtio"
    intf.source_dev = "virbr0"
    obj.add_device(intf)

    # obj.devices[3]
    balloon = config.LibvirtConfigMemoryBalloon()
    balloon.model = 'virtio'
    balloon.period = 11
    obj.add_device(balloon)

    # obj.devices[4]
    mouse = config.LibvirtConfigGuestInput()
    mouse.type = "mouse"
    mouse.bus = "virtio"
    obj.add_device(mouse)

    # obj.devices[5]
    gfx = config.LibvirtConfigGuestGraphics()
    gfx.type = "vnc"
    gfx.autoport = True
    gfx.keymap = "en_US"
    gfx.listen = "127.0.0.1"
    obj.add_device(gfx)

    # obj.devices[6]
    video = config.LibvirtConfigGuestVideo()
    video.type = 'virtio'
    obj.add_device(video)

    # obj.devices[7]
    serial = config.LibvirtConfigGuestSerial()
    serial.type = "file"
    serial.source_path = "/tmp/vm.log"
    obj.add_device(serial)

    # obj.devices[8]
    rng = config.LibvirtConfigGuestRng()
    rng.backend = '/dev/urandom'
    rng.rate_period = '12'
    rng.rate_bytes = '34'
    obj.add_device(rng)

    # obj.devices[9]
    controller = config.LibvirtConfigGuestController()
    controller.type = 'scsi'
    controller.model = 'virtio-scsi'  # usually set from image meta
    controller.index = 0
    controller.iothread_count = iothread_count
    obj.add_device(controller)

    return obj


FAKE_KVM_GUEST = """
  <domain type="kvm">
    <uuid>b38a3f43-4be2-4046-897f-b67c2f5e0147</uuid>
    <name>demo</name>
    <memory>104857600</memory>
    <memoryBacking>
      <hugepages>
        <page size="2048" unit="KiB" nodeset="0-3,5"/>
        <page size="1048576" unit="KiB" nodeset="4"/>
      </hugepages>
    </memoryBacking>
    <memtune>
      <hard_limit unit="KiB">496</hard_limit>
      <soft_limit unit="KiB">672</soft_limit>
      <swap_hard_limit unit="KiB">1638</swap_hard_limit>
      <min_guarantee unit="KiB">2970</min_guarantee>
    </memtune>
    <numatune>
      <memory mode="preferred" nodeset="0-3,8"/>
      <memnode cellid="0" mode="preferred" nodeset="0-1"/>
      <memnode cellid="1" mode="preferred" nodeset="2-3"/>
      <memnode cellid="2" mode="preferred" nodeset="8"/>
    </numatune>
    <vcpu cpuset="0-1,3-5">2</vcpu>
    <sysinfo type='smbios'>
       <bios>
         <entry name="vendor">Acme</entry>
       </bios>
       <system>
         <entry name="version">1.0.0</entry>
       </system>
    </sysinfo>
    <os>
      <type>linux</type>
      <boot dev="hd"/>
      <boot dev="cdrom"/>
      <boot dev="fd"/>
      <smbios mode="sysinfo"/>
    </os>
    <features>
      <acpi/>
      <apic/>
      <kvm>
        <hidden state='on'/>
      </kvm>
      <vmcoreinfo/>
    </features>
    <cputune>
      <shares>100</shares>
      <quota>50000</quota>
      <period>25000</period>
    </cputune>
    <devices>
      <disk type="file" device="disk">
        <source file="/tmp/disk-img"/>
        <target bus="virtio" dev="vda"/>
      </disk>
      <disk type="file" device="cdrom">
        <source file="/tmp/cdrom-img"/>
        <target bus="sata" dev="sda"/>
      </disk>
      <interface type='network'>
        <mac address='52:54:00:f6:35:8f'/>
        <model type='virtio'/>
        <source bridge='virbr0'/>
      </interface>
      <memballoon model='virtio'>
        <stats period='11'/>
      </memballoon>
      <input type="mouse" bus="virtio"/>
      <graphics type="vnc" autoport="yes" keymap="en_US" listen="127.0.0.1"/>
      <video>
        <model type='virtio'/>
      </video>
      <serial type="file">
        <source path="/tmp/vm.log"/>
      </serial>
      <rng model='virtio'>
          <rate period='12' bytes='34'/>
          <backend model='random'>/dev/urandom</backend>
      </rng>
      <controller type='scsi' index='0' model='virtio-scsi'/>
    </devices>
    <launchSecurity type="sev">
      <policy>0x0033</policy>
      <cbitpos>47</cbitpos>
      <reducedPhysBits>1</reducedPhysBits>
    </launchSecurity>
  </domain>"""

FAKE_KVM_GUEST_IOTHREAD = """
  <domain type="kvm">
    <uuid>b38a3f43-4be2-4046-897f-b67c2f5e0147</uuid>
    <name>demo</name>
    <memory>104857600</memory>
    <memoryBacking>
      <hugepages>
        <page size="2048" unit="KiB" nodeset="0-3,5"/>
        <page size="1048576" unit="KiB" nodeset="4"/>
      </hugepages>
    </memoryBacking>
    <memtune>
      <hard_limit unit="KiB">496</hard_limit>
      <soft_limit unit="KiB">672</soft_limit>
      <swap_hard_limit unit="KiB">1638</swap_hard_limit>
      <min_guarantee unit="KiB">2970</min_guarantee>
    </memtune>
    <numatune>
      <memory mode="preferred" nodeset="0-3,8"/>
      <memnode cellid="0" mode="preferred" nodeset="0-1"/>
      <memnode cellid="1" mode="preferred" nodeset="2-3"/>
      <memnode cellid="2" mode="preferred" nodeset="8"/>
    </numatune>
    <vcpu cpuset="0-1,3-5">2</vcpu>
    <sysinfo type='smbios'>
       <bios>
         <entry name="vendor">Acme</entry>
       </bios>
       <system>
         <entry name="version">1.0.0</entry>
       </system>
    </sysinfo>
    <os>
      <type>linux</type>
      <boot dev="hd"/>
      <boot dev="cdrom"/>
      <boot dev="fd"/>
      <smbios mode="sysinfo"/>
    </os>
    <features>
      <acpi/>
      <apic/>
      <kvm>
        <hidden state='on'/>
      </kvm>
      <vmcoreinfo/>
    </features>
    <cputune>
      <shares>100</shares>
      <quota>50000</quota>
      <period>25000</period>
    </cputune>
    <iothreads>2</iothreads>
    <devices>
      <disk type="file" device="disk">
        <driver io="native" iothread="1" />
        <source file="/tmp/disk-img"/>
        <target bus="virtio" dev="vda"/>
      </disk>
      <disk type="file" device="cdrom">
        <source file="/tmp/cdrom-img"/>
        <target bus="sata" dev="sda"/>
      </disk>
      <interface type='network'>
        <mac address='52:54:00:f6:35:8f'/>
        <model type='virtio'/>
        <source bridge='virbr0'/>
      </interface>
      <memballoon model='virtio'>
        <stats period='11'/>
      </memballoon>
      <input type="mouse" bus="virtio"/>
      <graphics type="vnc" autoport="yes" keymap="en_US" listen="127.0.0.1"/>
      <video>
        <model type='virtio'/>
      </video>
      <serial type="file">
        <source path="/tmp/vm.log"/>
      </serial>
      <rng model='virtio'>
          <rate period='12' bytes='34'/>
          <backend model='random'>/dev/urandom</backend>
      </rng>
      <controller type='scsi' index='0' model='virtio-scsi'>
        <driver iothread='1' />
      </controller>
    </devices>
    <launchSecurity type="sev">
      <policy>0x0033</policy>
      <cbitpos>47</cbitpos>
      <reducedPhysBits>1</reducedPhysBits>
    </launchSecurity>
  </domain>"""

CAPABILITIES_HOST_X86_64_TEMPLATE = """
  <host>
    <uuid>cef19ce0-0ca2-11df-855d-b19fbce37686</uuid>
    <cpu>
      <arch>x86_64</arch>
      <model>Penryn</model>
      <vendor>Intel</vendor>
      <topology sockets='%(sockets)s' cores='%(cores)s' threads='%(threads)s'/>
      <feature name='xtpr'/>
      <feature name='tm2'/>
      <feature name='est'/>
      <feature name='vmx'/>
      <feature name='ds_cpl'/>
      <feature name='monitor'/>
      <feature name='pbe'/>
      <feature name='tm'/>
      <feature name='ht'/>
      <feature name='ss'/>
      <feature name='acpi'/>
      <feature name='ds'/>
      <feature name='vme'/>
      <pages unit='KiB' size='4'/>
      <pages unit='KiB' size='2048'/>
      <pages unit='KiB' size='1048576'/>
    </cpu>
    <migration_features>
      <live/>
      <uri_transports>
        <uri_transport>tcp</uri_transport>
      </uri_transports>
    </migration_features>
    %(topology)s
    <secmodel>
      <model>apparmor</model>
      <doi>0</doi>
    </secmodel>
  </host>"""

# NOTE(stephenfin): This is incomplete
CAPABILITIES_HOST_I686_TEMPLATE = """
  <host>
    <uuid>cef19ce0-0ca2-11df-855d-b19fbce37686</uuid>
    <cpu>
      <arch>i686</arch>
    </cpu>
    <power_management/>
    <iommu support='no'/>
  </host>"""

CAPABILITIES_HOST_AARCH64_TEMPLATE = """
  <host>
    <uuid>cef19ce0-0ca2-11df-855d-b19fbce37686</uuid>
    <cpu>
      <arch>aarch64</arch>
      <model>host</model>
      <topology sockets='1' cores='48' threads='1'/>
      <pages unit='KiB' size='4'/>
      <pages unit='KiB' size='2048'/>
    </cpu>
    <power_management/>
    <migration_features>
      <live/>
      <uri_transports>
        <uri_transport>tcp</uri_transport>
        <uri_transport>rdma</uri_transport>
      </uri_transports>
    </migration_features>
    %(topology)s
    <secmodel>
      <model>apparmor</model>
      <doi>0</doi>
    </secmodel>
    <secmodel>
      <model>dac</model>
      <doi>0</doi>
      <baselabel type='kvm'>+0:+0</baselabel>
      <baselabel type='qemu'>+0:+0</baselabel>
    </secmodel>
  </host>"""

# NOTE(stephenfin): This is incomplete
CAPABILITIES_HOST_ARMV7_TEMPLATE = """
  <host>
    <cpu>
      <arch>armv7l</arch>
    </cpu>
    <power_management/>
    <iommu support='no'/>
  </host>"""

# NOTE(stephenfin): This is incomplete
CAPABILITIES_HOST_PPC_TEMPLATE = """
  <host>
    <uuid>cef19ce0-0ca2-11df-855d-b19fbce37686</uuid>
    <cpu>
      <arch>ppc</arch>
    </cpu>
    <power_management/>
    <iommu support='no'/>
  </host>"""

# NOTE(stephenfin): This is incomplete
CAPABILITIES_HOST_PPC64_TEMPLATE = """
  <host>
    <uuid>cef19ce0-0ca2-11df-855d-b19fbce37686</uuid>
    <cpu>
      <arch>ppc64</arch>
    </cpu>
    <power_management/>
    <iommu support='no'/>
  </host>"""

# NOTE(stephenfin): This is incomplete
CAPABILITIES_HOST_PPC64LE_TEMPLATE = """
  <host>
    <uuid>cef19ce0-0ca2-11df-855d-b19fbce37686</uuid>
    <cpu>
      <arch>ppc64le</arch>
    </cpu>
    <power_management/>
    <iommu support='no'/>
  </host>"""

# NOTE(stephenfin): This is incomplete
CAPABILITIES_HOST_S390X_TEMPLATE = """
  <host>
    <uuid>cef19ce0-0ca2-11df-855d-b19fbce37686</uuid>
    <cpu>
      <arch>s390x</arch>
    </cpu>
    <power_management/>
    <iommu support='no'/>
  </host>"""

CAPABILITIES_HOST_TEMPLATES = {
    Architecture.X86_64: CAPABILITIES_HOST_X86_64_TEMPLATE,
    Architecture.I686: CAPABILITIES_HOST_I686_TEMPLATE,
    Architecture.AARCH64: CAPABILITIES_HOST_AARCH64_TEMPLATE,
    Architecture.ARMV7: CAPABILITIES_HOST_ARMV7_TEMPLATE,
    Architecture.PPC: CAPABILITIES_HOST_PPC_TEMPLATE,
    Architecture.PPC64: CAPABILITIES_HOST_PPC64_TEMPLATE,
    Architecture.PPC64LE: CAPABILITIES_HOST_PPC64LE_TEMPLATE,
    Architecture.S390X: CAPABILITIES_HOST_S390X_TEMPLATE,
}

# NOTE(aspiers): HostTestCase has tests which assert that for any
# given (arch, domain) listed in the guest capabilities here, all
# canonical machine types (e.g. 'pc' or 'q35') must be a substring of
# the expanded machine type returned in the <machine> element of the
# corresponding fake getDomainCapabilities response for that (arch,
# domain, canonical_machine_type) combination.  Those responses are
# defined by the DOMCAPABILITIES_* variables below.  While
# DOMCAPABILITIES_X86_64_TEMPLATE can return multiple values for the
# <machine> element, DOMCAPABILITIES_I686 is fixed to fake a response
# of the 'pc-i440fx-2.11' machine type, therefore
# CAPABILITIES_GUEST['i686'] should return 'pc' as the only canonical
# machine type.
#
# CAPABILITIES_GUEST does not include canonical machine types for
# other non-x86 architectures, so these test assertions on apply to
# x86.
CAPABILITIES_GUEST = {
    'i686': '''
        <guest>
           <os_type>hvm</os_type>
           <arch name='i686'>
             <wordsize>32</wordsize>
             <emulator>/usr/bin/qemu-system-i386</emulator>
             <machine maxCpus='255'>pc-i440fx-2.11</machine>
             <machine canonical='pc-i440fx-2.11' maxCpus='255'>pc</machine>
             <machine maxCpus='1'>isapc</machine>
             <machine maxCpus='255'>pc-1.1</machine>
             <machine maxCpus='255'>pc-1.2</machine>
             <machine maxCpus='255'>pc-1.3</machine>
             <machine maxCpus='255'>pc-i440fx-2.8</machine>
             <machine maxCpus='255'>pc-1.0</machine>
             <machine maxCpus='255'>pc-i440fx-2.9</machine>
             <machine maxCpus='255'>pc-i440fx-2.6</machine>
             <machine maxCpus='255'>pc-i440fx-2.7</machine>
             <machine maxCpus='128'>xenfv</machine>
             <machine maxCpus='255'>pc-i440fx-2.3</machine>
             <machine maxCpus='255'>pc-i440fx-2.4</machine>
             <machine maxCpus='255'>pc-i440fx-2.5</machine>
             <machine maxCpus='255'>pc-i440fx-2.1</machine>
             <machine maxCpus='255'>pc-i440fx-2.2</machine>
             <machine maxCpus='255'>pc-i440fx-2.0</machine>
             <machine maxCpus='288'>pc-q35-2.11</machine>
             <machine maxCpus='288'>q35</machine>
             <machine maxCpus='1'>xenpv</machine>
             <machine maxCpus='288'>pc-q35-2.10</machine>
             <machine maxCpus='255'>pc-i440fx-1.7</machine>
             <machine maxCpus='288'>pc-q35-2.9</machine>
             <machine maxCpus='255'>pc-0.15</machine>
             <machine maxCpus='255'>pc-i440fx-1.5</machine>
             <machine maxCpus='255'>pc-q35-2.7</machine>
             <machine maxCpus='255'>pc-i440fx-1.6</machine>
             <machine maxCpus='288'>pc-q35-2.8</machine>
             <machine maxCpus='255'>pc-0.13</machine>
             <machine maxCpus='255'>pc-0.14</machine>
             <machine maxCpus='255'>pc-q35-2.4</machine>
             <machine maxCpus='255'>pc-q35-2.5</machine>
             <machine maxCpus='255'>pc-q35-2.6</machine>
             <machine maxCpus='255'>pc-i440fx-1.4</machine>
             <machine maxCpus='255'>pc-i440fx-2.10</machine>
             <machine maxCpus='255'>pc-0.11</machine>
             <machine maxCpus='255'>pc-0.12</machine>
             <machine maxCpus='255'>pc-0.10</machine>
             <domain type='qemu'/>
             <domain type='kvm'>
               <emulator>/usr/bin/qemu-kvm</emulator>
               <machine maxCpus='255'>pc-i440fx-2.11</machine>
               <machine canonical='pc-i440fx-2.11' maxCpus='255'>pc</machine>
               <machine maxCpus='1'>isapc</machine>
               <machine maxCpus='255'>pc-1.1</machine>
               <machine maxCpus='255'>pc-1.2</machine>
               <machine maxCpus='255'>pc-1.3</machine>
               <machine maxCpus='255'>pc-i440fx-2.8</machine>
               <machine maxCpus='255'>pc-1.0</machine>
               <machine maxCpus='255'>pc-i440fx-2.9</machine>
               <machine maxCpus='255'>pc-i440fx-2.6</machine>
               <machine maxCpus='255'>pc-i440fx-2.7</machine>
               <machine maxCpus='128'>xenfv</machine>
               <machine maxCpus='255'>pc-i440fx-2.3</machine>
               <machine maxCpus='255'>pc-i440fx-2.4</machine>
               <machine maxCpus='255'>pc-i440fx-2.5</machine>
               <machine maxCpus='255'>pc-i440fx-2.1</machine>
               <machine maxCpus='255'>pc-i440fx-2.2</machine>
               <machine maxCpus='255'>pc-i440fx-2.0</machine>
               <machine maxCpus='288'>pc-q35-2.11</machine>
               <machine maxCpus='288'>q35</machine>
               <machine maxCpus='1'>xenpv</machine>
               <machine maxCpus='288'>pc-q35-2.10</machine>
               <machine maxCpus='255'>pc-i440fx-1.7</machine>
               <machine maxCpus='288'>pc-q35-2.9</machine>
               <machine maxCpus='255'>pc-0.15</machine>
               <machine maxCpus='255'>pc-i440fx-1.5</machine>
               <machine maxCpus='255'>pc-q35-2.7</machine>
               <machine maxCpus='255'>pc-i440fx-1.6</machine>
               <machine maxCpus='288'>pc-q35-2.8</machine>
               <machine maxCpus='255'>pc-0.13</machine>
               <machine maxCpus='255'>pc-0.14</machine>
               <machine maxCpus='255'>pc-q35-2.4</machine>
               <machine maxCpus='255'>pc-q35-2.5</machine>
               <machine maxCpus='255'>pc-q35-2.6</machine>
               <machine maxCpus='255'>pc-i440fx-1.4</machine>
               <machine maxCpus='255'>pc-i440fx-2.10</machine>
               <machine maxCpus='255'>pc-0.11</machine>
               <machine maxCpus='255'>pc-0.12</machine>
               <machine maxCpus='255'>pc-0.10</machine>
             </domain>
           </arch>
           <features>
             <cpuselection/>
             <deviceboot/>
             <disksnapshot default='on' toggle='no'/>
             <acpi default='on' toggle='yes'/>
             <apic default='on' toggle='no'/>
             <pae/>
             <nonpae/>
           </features>
         </guest>''',

    'x86_64': '''
        <guest>
          <os_type>hvm</os_type>
          <arch name='x86_64'>
            <wordsize>64</wordsize>
            <emulator>/usr/bin/qemu-system-x86_64</emulator>
            <machine maxCpus='255'>pc-i440fx-2.11</machine>
            <machine canonical='pc-i440fx-2.11' maxCpus='255'>pc</machine>
            <machine maxCpus='1'>isapc</machine>
            <machine maxCpus='255'>pc-1.1</machine>
            <machine maxCpus='255'>pc-1.2</machine>
            <machine maxCpus='255'>pc-1.3</machine>
            <machine maxCpus='255'>pc-i440fx-2.8</machine>
            <machine maxCpus='255'>pc-1.0</machine>
            <machine maxCpus='255'>pc-i440fx-2.9</machine>
            <machine maxCpus='255'>pc-i440fx-2.6</machine>
            <machine maxCpus='255'>pc-i440fx-2.7</machine>
            <machine maxCpus='128'>xenfv</machine>
            <machine maxCpus='255'>pc-i440fx-2.3</machine>
            <machine maxCpus='255'>pc-i440fx-2.4</machine>
            <machine maxCpus='255'>pc-i440fx-2.5</machine>
            <machine maxCpus='255'>pc-i440fx-2.1</machine>
            <machine maxCpus='255'>pc-i440fx-2.2</machine>
            <machine maxCpus='255'>pc-i440fx-2.0</machine>
            <machine maxCpus='288'>pc-q35-2.11</machine>
            <machine canonical='pc-q35-2.11' maxCpus='288'>q35</machine>
            <machine maxCpus='1'>xenpv</machine>
            <machine maxCpus='288'>pc-q35-2.10</machine>
            <machine maxCpus='255'>pc-i440fx-1.7</machine>
            <machine maxCpus='288'>pc-q35-2.9</machine>
            <machine maxCpus='255'>pc-0.15</machine>
            <machine maxCpus='255'>pc-i440fx-1.5</machine>
            <machine maxCpus='255'>pc-q35-2.7</machine>
            <machine maxCpus='255'>pc-i440fx-1.6</machine>
            <machine maxCpus='288'>pc-q35-2.8</machine>
            <machine maxCpus='255'>pc-0.13</machine>
            <machine maxCpus='255'>pc-0.14</machine>
            <machine maxCpus='255'>pc-q35-2.4</machine>
            <machine maxCpus='255'>pc-q35-2.5</machine>
            <machine maxCpus='255'>pc-q35-2.6</machine>
            <machine maxCpus='255'>pc-i440fx-1.4</machine>
            <machine maxCpus='255'>pc-i440fx-2.10</machine>
            <machine maxCpus='255'>pc-0.11</machine>
            <machine maxCpus='255'>pc-0.12</machine>
            <machine maxCpus='255'>pc-0.10</machine>
            <domain type='qemu'/>
            <domain type='kvm'>
              <emulator>/usr/bin/qemu-kvm</emulator>
              <machine maxCpus='255'>pc-i440fx-2.11</machine>
              <machine canonical='pc-i440fx-2.11' maxCpus='255'>pc</machine>
              <machine maxCpus='1'>isapc</machine>
              <machine maxCpus='255'>pc-1.1</machine>
              <machine maxCpus='255'>pc-1.2</machine>
              <machine maxCpus='255'>pc-1.3</machine>
              <machine maxCpus='255'>pc-i440fx-2.8</machine>
              <machine maxCpus='255'>pc-1.0</machine>
              <machine maxCpus='255'>pc-i440fx-2.9</machine>
              <machine maxCpus='255'>pc-i440fx-2.6</machine>
              <machine maxCpus='255'>pc-i440fx-2.7</machine>
              <machine maxCpus='128'>xenfv</machine>
              <machine maxCpus='255'>pc-i440fx-2.3</machine>
              <machine maxCpus='255'>pc-i440fx-2.4</machine>
              <machine maxCpus='255'>pc-i440fx-2.5</machine>
              <machine maxCpus='255'>pc-i440fx-2.1</machine>
              <machine maxCpus='255'>pc-i440fx-2.2</machine>
              <machine maxCpus='255'>pc-i440fx-2.0</machine>
              <machine maxCpus='288'>pc-q35-2.11</machine>
              <machine canonical='pc-q35-2.11' maxCpus='288'>q35</machine>
              <machine maxCpus='1'>xenpv</machine>
              <machine maxCpus='288'>pc-q35-2.10</machine>
              <machine maxCpus='255'>pc-i440fx-1.7</machine>
              <machine maxCpus='288'>pc-q35-2.9</machine>
              <machine maxCpus='255'>pc-0.15</machine>
              <machine maxCpus='255'>pc-i440fx-1.5</machine>
              <machine maxCpus='255'>pc-q35-2.7</machine>
              <machine maxCpus='255'>pc-i440fx-1.6</machine>
              <machine maxCpus='288'>pc-q35-2.8</machine>
              <machine maxCpus='255'>pc-0.13</machine>
              <machine maxCpus='255'>pc-0.14</machine>
              <machine maxCpus='255'>pc-q35-2.4</machine>
              <machine maxCpus='255'>pc-q35-2.5</machine>
              <machine maxCpus='255'>pc-q35-2.6</machine>
              <machine maxCpus='255'>pc-i440fx-1.4</machine>
              <machine maxCpus='255'>pc-i440fx-2.10</machine>
              <machine maxCpus='255'>pc-0.11</machine>
              <machine maxCpus='255'>pc-0.12</machine>
              <machine maxCpus='255'>pc-0.10</machine>
            </domain>
          </arch>
          <features>
            <cpuselection/>
            <deviceboot/>
            <disksnapshot default='on' toggle='no'/>
            <acpi default='on' toggle='yes'/>
            <apic default='on' toggle='no'/>
          </features>
        </guest>''',

    'aarch64': '''
        <guest>
          <os_type>hvm</os_type>
          <arch name='aarch64'>
            <wordsize>64</wordsize>
            <emulator>/usr/bin/qemu-system-aarch64</emulator>
            <machine maxCpus='1'>integratorcp</machine>
            <machine maxCpus='2'>ast2600-evb</machine>
            <machine maxCpus='1'>borzoi</machine>
            <machine maxCpus='1'>spitz</machine>
            <machine maxCpus='255'>virt-2.7</machine>
            <machine maxCpus='2'>nuri</machine>
            <machine maxCpus='2'>mcimx7d-sabre</machine>
            <machine maxCpus='1'>romulus-bmc</machine>
            <machine maxCpus='512'>virt-3.0</machine>
            <machine maxCpus='512'>virt-5.0</machine>
            <machine maxCpus='255'>virt-2.10</machine>
            <machine maxCpus='255'>virt-2.8</machine>
            <machine maxCpus='2'>musca-b1</machine>
            <machine maxCpus='4'>realview-pbx-a9</machine>
            <machine maxCpus='1'>versatileab</machine>
            <machine maxCpus='1'>kzm</machine>
            <machine maxCpus='2'>musca-a</machine>
            <machine maxCpus='512'>virt-3.1</machine>
            <machine maxCpus='1'>mcimx6ul-evk</machine>
            <machine maxCpus='512'>virt-5.1</machine>
            <machine canonical='virt-5.1' maxCpus='512'>virt</machine>
            <machine maxCpus='2'>smdkc210</machine>
            <machine maxCpus='1'>sx1</machine>
            <machine maxCpus='4'>raspi2</machine>
            <machine maxCpus='255'>virt-2.11</machine>
            <machine maxCpus='1'>imx25-pdk</machine>
            <machine maxCpus='255'>virt-2.9</machine>
            <machine maxCpus='4'>orangepi-pc</machine>
            <machine maxCpus='1'>z2</machine>
            <machine maxCpus='1'>xilinx-zynq-a9</machine>
            <machine maxCpus='6'>xlnx-zcu102</machine>
            <machine maxCpus='4'>raspi3</machine>
            <machine maxCpus='1'>tosa</machine>
            <machine maxCpus='255'>virt-2.12</machine>
            <machine maxCpus='2'>mps2-an521</machine>
            <machine maxCpus='4'>sabrelite</machine>
            <machine maxCpus='1'>mps2-an511</machine>
            <machine maxCpus='1'>canon-a1100</machine>
            <machine maxCpus='1'>realview-eb</machine>
            <machine maxCpus='1'>emcraft-sf2</machine>
            <machine maxCpus='1'>realview-pb-a8</machine>
            <machine maxCpus='512'>sbsa-ref</machine>
            <machine maxCpus='512'>virt-4.0</machine>
            <machine maxCpus='1'>palmetto-bmc</machine>
            <machine maxCpus='1'>sx1-v1</machine>
            <machine maxCpus='1'>n810</machine>
            <machine maxCpus='2'>tacoma-bmc</machine>
            <machine maxCpus='1'>n800</machine>
            <machine maxCpus='512'>virt-4.1</machine>
            <machine maxCpus='1'>versatilepb</machine>
            <machine maxCpus='1'>terrier</machine>
            <machine maxCpus='1'>mainstone</machine>
            <machine maxCpus='4'>realview-eb-mpcore</machine>
            <machine maxCpus='512'>virt-4.2</machine>
            <machine maxCpus='1'>witherspoon-bmc</machine>
            <machine maxCpus='1'>swift-bmc</machine>
            <machine maxCpus='4'>vexpress-a9</machine>
            <machine maxCpus='4'>midway</machine>
            <machine maxCpus='1'>musicpal</machine>
            <machine maxCpus='1'>lm3s811evb</machine>
            <machine maxCpus='1'>lm3s6965evb</machine>
            <machine maxCpus='1'>microbit</machine>
            <machine maxCpus='1'>mps2-an505</machine>
            <machine maxCpus='1'>mps2-an385</machine>
            <machine maxCpus='1'>cubieboard</machine>
            <machine maxCpus='1'>verdex</machine>
            <machine maxCpus='1'>netduino2</machine>
            <machine maxCpus='2'>xlnx-versal-virt</machine>
            <machine maxCpus='4'>vexpress-a15</machine>
            <machine maxCpus='1'>sonorapass-bmc</machine>
            <machine maxCpus='1'>cheetah</machine>
            <machine maxCpus='255'>virt-2.6</machine>
            <machine maxCpus='1'>ast2500-evb</machine>
            <machine maxCpus='4'>highbank</machine>
            <machine maxCpus='1'>akita</machine>
            <machine maxCpus='1'>connex</machine>
            <machine maxCpus='1'>netduinoplus2</machine>
            <machine maxCpus='1'>collie</machine>
            <domain type='qemu'/>
          </arch>
          <features>
            <acpi default='on' toggle='yes'/>
            <cpuselection/>
            <deviceboot/>
            <disksnapshot default='on' toggle='no'/>
          </features>
        </guest>''',

    'armv7l': '''
        <guest>
          <os_type>hvm</os_type>
          <arch name='armv7l'>
            <wordsize>32</wordsize>
            <emulator>/usr/bin/qemu-system-arm</emulator>
            <machine>integratorcp</machine>
            <machine>vexpress-a9</machine>
            <machine>syborg</machine>
            <machine>musicpal</machine>
            <machine>mainstone</machine>
            <machine>n800</machine>
            <machine>n810</machine>
            <machine>n900</machine>
            <machine>cheetah</machine>
            <machine>sx1</machine>
            <machine>sx1-v1</machine>
            <machine>beagle</machine>
            <machine>beaglexm</machine>
            <machine>tosa</machine>
            <machine>akita</machine>
            <machine>spitz</machine>
            <machine>borzoi</machine>
            <machine>terrier</machine>
            <machine>connex</machine>
            <machine>verdex</machine>
            <machine>lm3s811evb</machine>
            <machine>lm3s6965evb</machine>
            <machine>realview-eb</machine>
            <machine>realview-eb-mpcore</machine>
            <machine>realview-pb-a8</machine>
            <machine>realview-pbx-a9</machine>
            <machine>versatilepb</machine>
            <machine>versatileab</machine>
            <domain type='qemu'>
            </domain>
          </arch>
          <features>
            <deviceboot/>
          </features>
        </guest>''',

    'mips': '''
        <guest>
          <os_type>hvm</os_type>
          <arch name='mips'>
            <wordsize>32</wordsize>
            <emulator>/usr/bin/qemu-system-mips</emulator>
            <machine>malta</machine>
            <machine>mipssim</machine>
            <machine>magnum</machine>
            <machine>pica61</machine>
            <machine>mips</machine>
            <domain type='qemu'>
            </domain>
          </arch>
          <features>
            <deviceboot/>
          </features>
        </guest>''',

    'mipsel': '''
        <guest>
          <os_type>hvm</os_type>
          <arch name='mipsel'>
            <wordsize>32</wordsize>
            <emulator>/usr/bin/qemu-system-mipsel</emulator>
            <machine>malta</machine>
            <machine>mipssim</machine>
            <machine>magnum</machine>
            <machine>pica61</machine>
            <machine>mips</machine>
            <domain type='qemu'>
            </domain>
          </arch>
          <features>
            <deviceboot/>
          </features>
        </guest>''',

    'sparc': '''
        <guest>
          <os_type>hvm</os_type>
          <arch name='sparc'>
            <wordsize>32</wordsize>
            <emulator>/usr/bin/qemu-system-sparc</emulator>
            <machine>SS-5</machine>
            <machine>leon3_generic</machine>
            <machine>SS-10</machine>
            <machine>SS-600MP</machine>
            <machine>SS-20</machine>
            <machine>Voyager</machine>
            <machine>LX</machine>
            <machine>SS-4</machine>
            <machine>SPARCClassic</machine>
            <machine>SPARCbook</machine>
            <machine>SS-1000</machine>
            <machine>SS-2000</machine>
            <machine>SS-2</machine>
            <domain type='qemu'>
            </domain>
          </arch>
        </guest>''',

    'ppc': '''
        <guest>
          <os_type>hvm</os_type>
          <arch name='ppc'>
            <wordsize>32</wordsize>
            <emulator>/usr/bin/qemu-system-ppc</emulator>
            <machine>g3beige</machine>
            <machine>virtex-ml507</machine>
            <machine>mpc8544ds</machine>
            <machine>bamboo-0.13</machine>
            <machine>bamboo-0.12</machine>
            <machine>ref405ep</machine>
            <machine>taihu</machine>
            <machine>mac99</machine>
            <machine>prep</machine>
            <domain type='qemu'>
            </domain>
          </arch>
          <features>
            <deviceboot/>
          </features>
        </guest>'''
}

DOMCAPABILITIES_SPARC = """
<domainCapabilities>
  <path>/usr/bin/qemu-system-sparc</path>
  <domain>qemu</domain>
  <machine>SS-5</machine>
  <arch>sparc</arch>
  <vcpu max='1'/>
  <os supported='yes'>
    <loader supported='yes'>
      <enum name='type'>
        <value>rom</value>
        <value>pflash</value>
      </enum>
      <enum name='readonly'>
        <value>yes</value>
        <value>no</value>
      </enum>
      <enum name='secure'>
        <value>yes</value>
        <value>no</value>
      </enum>
    </loader>
  </os>
  <cpu>
    <mode name='host-passthrough' supported='no'/>
    <mode name='host-model' supported='no'/>
    <mode name='custom' supported='no'/>
  </cpu>
  <devices>
    <disk supported='yes'>
      <enum name='diskDevice'>
        <value>disk</value>
        <value>cdrom</value>
        <value>floppy</value>
        <value>lun</value>
      </enum>
      <enum name='bus'>
        <value>fdc</value>
        <value>scsi</value>
        <value>virtio</value>
      </enum>
    </disk>
    <graphics supported='yes'>
      <enum name='type'>
        <value>sdl</value>
        <value>vnc</value>
        <value>spice</value>
      </enum>
    </graphics>
    <video supported='yes'>
      <enum name='modelType'/>
    </video>
    <hostdev supported='yes'>
      <enum name='mode'>
        <value>subsystem</value>
      </enum>
      <enum name='startupPolicy'>
        <value>default</value>
        <value>mandatory</value>
        <value>requisite</value>
        <value>optional</value>
      </enum>
      <enum name='subsysType'>
        <value>usb</value>
        <value>pci</value>
        <value>scsi</value>
      </enum>
      <enum name='capsType'/>
      <enum name='pciBackend'/>
    </hostdev>
  </devices>
  <features>
    <gic supported='no'/>
  </features>
</domainCapabilities>
"""

DOMCAPABILITIES_ARMV7 = """
<domainCapabilities>
  <path>/usr/bin/qemu-system-arm</path>
  <domain>qemu</domain>
  <machine>virt-2.11</machine>
  <arch>armv7l</arch>
  <vcpu max='255'/>
  <os supported='yes'>
    <loader supported='yes'>
      <enum name='type'>
        <value>rom</value>
        <value>pflash</value>
      </enum>
      <enum name='readonly'>
        <value>yes</value>
        <value>no</value>
      </enum>
      <enum name='secure'>
        <value>yes</value>
        <value>no</value>
      </enum>
    </loader>
  </os>
  <cpu>
    <mode name='host-passthrough' supported='no'/>
    <mode name='host-model' supported='no'/>
    <mode name='custom' supported='yes'>
      <model usable='unknown'>pxa262</model>
      <model usable='unknown'>pxa270-a0</model>
      <model usable='unknown'>arm1136</model>
      <model usable='unknown'>cortex-a15</model>
      <model usable='unknown'>pxa260</model>
      <model usable='unknown'>arm1136-r2</model>
      <model usable='unknown'>pxa261</model>
      <model usable='unknown'>pxa255</model>
      <model usable='unknown'>arm926</model>
      <model usable='unknown'>arm11mpcore</model>
      <model usable='unknown'>pxa250</model>
      <model usable='unknown'>ti925t</model>
      <model usable='unknown'>sa1110</model>
      <model usable='unknown'>arm1176</model>
      <model usable='unknown'>sa1100</model>
      <model usable='unknown'>pxa270-c5</model>
      <model usable='unknown'>cortex-a9</model>
      <model usable='unknown'>cortex-a8</model>
      <model usable='unknown'>pxa270-c0</model>
      <model usable='unknown'>cortex-a7</model>
      <model usable='unknown'>arm1026</model>
      <model usable='unknown'>pxa270-b1</model>
      <model usable='unknown'>cortex-m3</model>
      <model usable='unknown'>cortex-m4</model>
      <model usable='unknown'>pxa270-b0</model>
      <model usable='unknown'>arm946</model>
      <model usable='unknown'>cortex-r5</model>
      <model usable='unknown'>pxa270-a1</model>
      <model usable='unknown'>pxa270</model>
    </mode>
  </cpu>
  <devices>
    <disk supported='yes'>
      <enum name='diskDevice'>
        <value>disk</value>
        <value>cdrom</value>
        <value>floppy</value>
        <value>lun</value>
      </enum>
      <enum name='bus'>
        <value>fdc</value>
        <value>scsi</value>
        <value>virtio</value>
        <value>usb</value>
        <value>sata</value>
      </enum>
    </disk>
    <graphics supported='yes'>
      <enum name='type'>
        <value>sdl</value>
        <value>vnc</value>
        <value>spice</value>
      </enum>
    </graphics>
    <video supported='yes'>
      <enum name='modelType'>
        <value>vga</value>
        <value>virtio</value>
      </enum>
    </video>
    <hostdev supported='yes'>
      <enum name='mode'>
        <value>subsystem</value>
      </enum>
      <enum name='startupPolicy'>
        <value>default</value>
        <value>mandatory</value>
        <value>requisite</value>
        <value>optional</value>
      </enum>
      <enum name='subsysType'>
        <value>usb</value>
        <value>pci</value>
        <value>scsi</value>
      </enum>
      <enum name='capsType'/>
      <enum name='pciBackend'/>
    </hostdev>
  </devices>
  <features>
    <gic supported='yes'>
      <enum name='version'>
        <value>2</value>
        <value>3</value>
      </enum>
    </gic>
  </features>
</domainCapabilities>
"""

DOMCAPABILITIES_AARCH64 = """
<domainCapabilities>
  <path>/usr/bin/qemu-system-aarch64</path>
  <domain>qemu</domain>
  <machine>virt-5.1</machine>
  <arch>aarch64</arch>
  <vcpu max='512'/>
  <iothreads supported='yes'/>
  <os supported='yes'>
    <enum name='firmware'>
      <value>efi</value>
    </enum>
    <loader supported='yes'>
      <value>/usr/share/AAVMF/AAVMF_CODE.fd</value>
      <enum name='type'>
        <value>rom</value>
        <value>pflash</value>
      </enum>
      <enum name='readonly'>
        <value>yes</value>
        <value>no</value>
      </enum>
      <enum name='secure'>
        <value>no</value>
        <value>yes</value>
      </enum>
    </loader>
  </os>
  <cpu>
    <mode name='host-passthrough' supported='no'/>
    <mode name='host-model' supported='no'/>
    <mode name='custom' supported='yes'>
      <model usable='unknown'>pxa270-c0</model>
      <model usable='unknown'>cortex-a15</model>
      <model usable='unknown'>pxa270-b0</model>
      <model usable='unknown'>cortex-a57</model>
      <model usable='unknown'>cortex-m4</model>
      <model usable='unknown'>pxa270-a0</model>
      <model usable='unknown'>arm1176</model>
      <model usable='unknown'>pxa270-b1</model>
      <model usable='unknown'>cortex-a7</model>
      <model usable='unknown'>pxa270-a1</model>
      <model usable='unknown'>cortex-a8</model>
      <model usable='unknown'>cortex-r5</model>
      <model usable='unknown'>ti925t</model>
      <model usable='unknown'>cortex-r5f</model>
      <model usable='unknown'>arm1026</model>
      <model usable='unknown'>cortex-a9</model>
      <model usable='unknown'>cortex-m7</model>
      <model usable='unknown'>pxa270</model>
      <model usable='unknown'>pxa260</model>
      <model usable='unknown'>pxa250</model>
      <model usable='unknown'>pxa270-c5</model>
      <model usable='unknown'>pxa261</model>
      <model usable='unknown'>pxa262</model>
      <model usable='unknown'>sa1110</model>
      <model usable='unknown'>sa1100</model>
      <model usable='unknown'>max</model>
      <model usable='unknown'>cortex-a53</model>
      <model usable='unknown'>cortex-m0</model>
      <model usable='unknown'>cortex-m33</model>
      <model usable='unknown'>cortex-a72</model>
      <model usable='unknown'>arm946</model>
      <model usable='unknown'>pxa255</model>
      <model usable='unknown'>arm11mpcore</model>
      <model usable='unknown'>arm926</model>
      <model usable='unknown'>arm1136</model>
      <model usable='unknown'>arm1136-r2</model>
      <model usable='unknown'>cortex-m3</model>
    </mode>
  </cpu>
  <devices>
    <disk supported='yes'>
      <enum name='diskDevice'>
        <value>disk</value>
        <value>cdrom</value>
        <value>floppy</value>
        <value>lun</value>
      </enum>
      <enum name='bus'>
        <value>fdc</value>
        <value>scsi</value>
        <value>virtio</value>
        <value>usb</value>
        <value>sata</value>
      </enum>
      <enum name='model'>
        <value>virtio</value>
        <value>virtio-transitional</value>
        <value>virtio-non-transitional</value>
      </enum>
    </disk>
    <graphics supported='yes'>
      <enum name='type'>
        <value>sdl</value>
        <value>vnc</value>
        <value>spice</value>
      </enum>
    </graphics>
    <video supported='yes'>
      <enum name='modelType'>
        <value>vga</value>
        <value>cirrus</value>
        <value>vmvga</value>
        <value>qxl</value>
        <value>virtio</value>
        <value>none</value>
        <value>bochs</value>
        <value>ramfb</value>
      </enum>
    </video>
    <hostdev supported='yes'>
      <enum name='mode'>
        <value>subsystem</value>
      </enum>
      <enum name='startupPolicy'>
        <value>default</value>
        <value>mandatory</value>
        <value>requisite</value>
        <value>optional</value>
      </enum>
      <enum name='subsysType'>
        <value>usb</value>
        <value>pci</value>
        <value>scsi</value>
      </enum>
      <enum name='capsType'/>
      <enum name='pciBackend'/>
    </hostdev>
    <rng supported='yes'>
      <enum name='model'>
        <value>virtio</value>
        <value>virtio-transitional</value>
        <value>virtio-non-transitional</value>
      </enum>
      <enum name='backendModel'>
        <value>random</value>
        <value>egd</value>
        <value>builtin</value>
      </enum>
    </rng>
  </devices>
  <features>
    <gic supported='yes'>
      <enum name='version'>
        <value>2</value>
        <value>3</value>
      </enum>
    </gic>
    <vmcoreinfo supported='yes'/>
    <genid supported='no'/>
    <backingStoreInput supported='yes'/>
    <backup supported='no'/>
    <sev supported='no'/>
  </features>
</domainCapabilities>
"""

DOMCAPABILITIES_PPC = """
<domainCapabilities>
  <path>/usr/bin/qemu-system-ppc</path>
  <domain>qemu</domain>
  <machine>g3beige</machine>
  <arch>ppc</arch>
  <vcpu max='1'/>
  <os supported='yes'>
    <loader supported='yes'>
      <enum name='type'>
        <value>rom</value>
        <value>pflash</value>
      </enum>
      <enum name='readonly'>
        <value>yes</value>
        <value>no</value>
      </enum>
      <enum name='secure'>
        <value>yes</value>
        <value>no</value>
      </enum>
    </loader>
  </os>
  <cpu>
    <mode name='host-passthrough' supported='no'/>
    <mode name='host-model' supported='no'/>
    <mode name='custom' supported='no'/>
  </cpu>
  <devices>
    <disk supported='yes'>
      <enum name='diskDevice'>
        <value>disk</value>
        <value>cdrom</value>
        <value>floppy</value>
        <value>lun</value>
      </enum>
      <enum name='bus'>
        <value>ide</value>
        <value>fdc</value>
        <value>scsi</value>
        <value>virtio</value>
        <value>usb</value>
        <value>sata</value>
      </enum>
    </disk>
    <graphics supported='yes'>
      <enum name='type'>
        <value>sdl</value>
        <value>vnc</value>
        <value>spice</value>
      </enum>
    </graphics>
    <video supported='yes'>
      <enum name='modelType'>
        <value>vga</value>
        <value>virtio</value>
      </enum>
    </video>
    <hostdev supported='yes'>
      <enum name='mode'>
        <value>subsystem</value>
      </enum>
      <enum name='startupPolicy'>
        <value>default</value>
        <value>mandatory</value>
        <value>requisite</value>
        <value>optional</value>
      </enum>
      <enum name='subsysType'>
        <value>usb</value>
        <value>pci</value>
        <value>scsi</value>
      </enum>
      <enum name='capsType'/>
      <enum name='pciBackend'/>
    </hostdev>
  </devices>
  <features>
    <gic supported='no'/>
  </features>
</domainCapabilities>
"""

DOMCAPABILITIES_MIPS = """
<domainCapabilities>
  <path>/usr/bin/qemu-system-mips</path>
  <domain>qemu</domain>
  <machine>malta</machine>
  <arch>mips</arch>
  <vcpu max='16'/>
  <os supported='yes'>
    <loader supported='yes'>
      <enum name='type'>
        <value>rom</value>
        <value>pflash</value>
      </enum>
      <enum name='readonly'>
        <value>yes</value>
        <value>no</value>
      </enum>
      <enum name='secure'>
        <value>yes</value>
        <value>no</value>
      </enum>
    </loader>
  </os>
  <cpu>
    <mode name='host-passthrough' supported='no'/>
    <mode name='host-model' supported='no'/>
    <mode name='custom' supported='no'/>
  </cpu>
  <devices>
    <disk supported='yes'>
      <enum name='diskDevice'>
        <value>disk</value>
        <value>cdrom</value>
        <value>floppy</value>
        <value>lun</value>
      </enum>
      <enum name='bus'>
        <value>ide</value>
        <value>fdc</value>
        <value>scsi</value>
        <value>virtio</value>
        <value>usb</value>
        <value>sata</value>
      </enum>
    </disk>
    <graphics supported='yes'>
      <enum name='type'>
        <value>sdl</value>
        <value>vnc</value>
        <value>spice</value>
      </enum>
    </graphics>
    <video supported='yes'>
      <enum name='modelType'>
        <value>vga</value>
        <value>cirrus</value>
        <value>vmvga</value>
        <value>virtio</value>
      </enum>
    </video>
    <hostdev supported='yes'>
      <enum name='mode'>
        <value>subsystem</value>
      </enum>
      <enum name='startupPolicy'>
        <value>default</value>
        <value>mandatory</value>
        <value>requisite</value>
        <value>optional</value>
      </enum>
      <enum name='subsysType'>
        <value>usb</value>
        <value>pci</value>
        <value>scsi</value>
      </enum>
      <enum name='capsType'/>
      <enum name='pciBackend'/>
    </hostdev>
  </devices>
  <features>
    <gic supported='no'/>
  </features>
</domainCapabilities>
"""

DOMCAPABILITIES_MIPSEL = """
<domainCapabilities>
  <path>/usr/bin/qemu-system-mipsel</path>
  <domain>qemu</domain>
  <machine>malta</machine>
  <arch>mipsel</arch>
  <vcpu max='16'/>
  <os supported='yes'>
    <loader supported='yes'>
      <enum name='type'>
        <value>rom</value>
        <value>pflash</value>
      </enum>
      <enum name='readonly'>
        <value>yes</value>
        <value>no</value>
      </enum>
      <enum name='secure'>
        <value>yes</value>
        <value>no</value>
      </enum>
    </loader>
  </os>
  <cpu>
    <mode name='host-passthrough' supported='no'/>
    <mode name='host-model' supported='no'/>
    <mode name='custom' supported='no'/>
  </cpu>
  <devices>
    <disk supported='yes'>
      <enum name='diskDevice'>
        <value>disk</value>
        <value>cdrom</value>
        <value>floppy</value>
        <value>lun</value>
      </enum>
      <enum name='bus'>
        <value>ide</value>
        <value>fdc</value>
        <value>scsi</value>
        <value>virtio</value>
        <value>usb</value>
        <value>sata</value>
      </enum>
    </disk>
    <graphics supported='yes'>
      <enum name='type'>
        <value>sdl</value>
        <value>vnc</value>
        <value>spice</value>
      </enum>
    </graphics>
    <video supported='yes'>
      <enum name='modelType'>
        <value>vga</value>
        <value>cirrus</value>
        <value>vmvga</value>
        <value>virtio</value>
      </enum>
    </video>
    <hostdev supported='yes'>
      <enum name='mode'>
        <value>subsystem</value>
      </enum>
      <enum name='startupPolicy'>
        <value>default</value>
        <value>mandatory</value>
        <value>requisite</value>
        <value>optional</value>
      </enum>
      <enum name='subsysType'>
        <value>usb</value>
        <value>pci</value>
        <value>scsi</value>
      </enum>
      <enum name='capsType'/>
      <enum name='pciBackend'/>
    </hostdev>
  </devices>
  <features>
    <gic supported='no'/>
  </features>
</domainCapabilities>
"""

# NOTE(sean-k-mooney): yes i686 is actually the i386 emulator
# the qemu-system-i386 binary is used for all 32bit x86
# instruction sets.
DOMCAPABILITIES_I686 = """
<domainCapabilities>
  <path>/usr/bin/qemu-system-i386</path>
  <domain>kvm</domain>
  <machine>pc-i440fx-2.11</machine>
  <arch>i686</arch>
  <vcpu max='255'/>
  <os supported='yes'>
    <loader supported='yes'>
      <enum name='type'>
        <value>rom</value>
        <value>pflash</value>
      </enum>
      <enum name='readonly'>
        <value>yes</value>
        <value>no</value>
      </enum>
      <enum name='secure'>
        <value>yes</value>
        <value>no</value>
      </enum>
    </loader>
  </os>
  <cpu>
    <mode name='host-passthrough' supported='yes'/>
    <mode name='host-model' supported='yes'>
      <model fallback='forbid'>Skylake-Client-IBRS</model>
      <vendor>Intel</vendor>
      <feature policy='require' name='ss'/>
      <feature policy='require' name='vmx'/>
      <feature policy='require' name='hypervisor'/>
      <feature policy='require' name='tsc_adjust'/>
      <feature policy='require' name='clflushopt'/>
      <feature policy='require' name='md-clear'/>
      <feature policy='require' name='ssbd'/>
      <feature policy='require' name='xsaves'/>
      <feature policy='require' name='pdpe1gb'/>
    </mode>
    <mode name='custom' supported='yes'>
      <model usable='no'>qemu64</model>
      <model usable='yes'>qemu32</model>
      <model usable='no'>phenom</model>
      <model usable='yes'>pentium3</model>
      <model usable='yes'>pentium2</model>
      <model usable='yes'>pentium</model>
      <model usable='yes'>n270</model>
      <model usable='yes'>kvm64</model>
      <model usable='yes'>kvm32</model>
      <model usable='yes'>coreduo</model>
      <model usable='yes'>core2duo</model>
      <model usable='no'>athlon</model>
      <model usable='yes'>Westmere</model>
      <model usable='yes'>Westmere-IBRS</model>
      <model usable='no'>Skylake-Server</model>
      <model usable='no'>Skylake-Server-IBRS</model>
      <model usable='yes'>Skylake-Client</model>
      <model usable='yes'>Skylake-Client-IBRS</model>
      <model usable='yes'>SandyBridge</model>
      <model usable='yes'>SandyBridge-IBRS</model>
      <model usable='yes'>Penryn</model>
      <model usable='no'>Opteron_G5</model>
      <model usable='no'>Opteron_G4</model>
      <model usable='no'>Opteron_G3</model>
      <model usable='no'>Opteron_G2</model>
      <model usable='yes'>Opteron_G1</model>
      <model usable='yes'>Nehalem</model>
      <model usable='yes'>Nehalem-IBRS</model>
      <model usable='yes'>IvyBridge</model>
      <model usable='yes'>IvyBridge-IBRS</model>
      <model usable='yes'>Haswell-noTSX</model>
      <model usable='yes'>Haswell-noTSX-IBRS</model>
      <model usable='yes'>Haswell</model>
      <model usable='yes'>Haswell-IBRS</model>
      <model usable='no'>EPYC</model>
      <model usable='no'>EPYC-IBPB</model>
      <model usable='yes'>Conroe</model>
      <model usable='yes'>Broadwell-noTSX</model>
      <model usable='yes'>Broadwell-noTSX-IBRS</model>
      <model usable='yes'>Broadwell</model>
      <model usable='yes'>Broadwell-IBRS</model>
      <model usable='yes'>486</model>
    </mode>
  </cpu>
  <devices>
    <disk supported='yes'>
      <enum name='diskDevice'>
        <value>disk</value>
        <value>cdrom</value>
        <value>floppy</value>
        <value>lun</value>
      </enum>
      <enum name='bus'>
        <value>ide</value>
        <value>fdc</value>
        <value>scsi</value>
        <value>virtio</value>
        <value>usb</value>
        <value>sata</value>
      </enum>
    </disk>
    <graphics supported='yes'>
      <enum name='type'>
        <value>sdl</value>
        <value>vnc</value>
        <value>spice</value>
      </enum>
    </graphics>
    <video supported='yes'>
      <enum name='modelType'>
        <value>vga</value>
        <value>cirrus</value>
        <value>vmvga</value>
        <value>qxl</value>
        <value>virtio</value>
      </enum>
    </video>
    <hostdev supported='yes'>
      <enum name='mode'>
        <value>subsystem</value>
      </enum>
      <enum name='startupPolicy'>
        <value>default</value>
        <value>mandatory</value>
        <value>requisite</value>
        <value>optional</value>
      </enum>
      <enum name='subsysType'>
        <value>usb</value>
        <value>pci</value>
        <value>scsi</value>
      </enum>
      <enum name='capsType'/>
      <enum name='pciBackend'/>
    </hostdev>
  </devices>
  <features>
    <gic supported='no'/>
  </features>
</domainCapabilities>
"""

STATIC_DOMCAPABILITIES = {
    Architecture.ARMV7: DOMCAPABILITIES_ARMV7,
    Architecture.AARCH64: DOMCAPABILITIES_AARCH64,
    Architecture.SPARC: DOMCAPABILITIES_SPARC,
    Architecture.PPC: DOMCAPABILITIES_PPC,
    Architecture.MIPS: DOMCAPABILITIES_MIPS,
    Architecture.MIPSEL: DOMCAPABILITIES_MIPSEL,
    Architecture.I686: DOMCAPABILITIES_I686
}

# NOTE(aspiers): see the above note for CAPABILITIES_GUEST which
# explains why the <machine> element here needs to be parametrised.
#
# The <features> element needs to be parametrised for emulating
# environments with and without the SEV feature.
DOMCAPABILITIES_X86_64_TEMPLATE = """
<domainCapabilities>
  <path>/usr/bin/qemu-kvm</path>
  <domain>kvm</domain>
  <machine>%(mtype)s</machine>
  <arch>x86_64</arch>
  <vcpu max='255'/>
  <os supported='yes'>
    <enum name='firmware'>
      <value>efi</value>
    </enum>
    <loader supported='yes'>
      <value>/usr/share/edk2/ovmf/OVMF_CODE.fd</value>
      <value>/usr/share/edk2/ovmf/OVMF_CODE.secboot.fd</value>
      <enum name='type'>
        <value>rom</value>
        <value>pflash</value>
      </enum>
      <enum name='readonly'>
        <value>yes</value>
        <value>no</value>
      </enum>
      <enum name='secure'>
        <value>yes</value>
        <value>no</value>
      </enum>
    </loader>
  </os>
  <cpu>
    <mode name='host-passthrough' supported='yes'/>
    <mode name='host-model' supported='yes'>
      <model fallback='forbid'>EPYC-IBPB</model>
      <vendor>AMD</vendor>
      <feature policy='require' name='x2apic'/>
      <feature policy='require' name='tsc-deadline'/>
      <feature policy='require' name='hypervisor'/>
      <feature policy='require' name='tsc_adjust'/>
      <feature policy='require' name='cmp_legacy'/>
      <feature policy='require' name='invtsc'/>
      <feature policy='require' name='virt-ssbd'/>
      <feature policy='disable' name='monitor'/>
    </mode>
    <mode name='custom' supported='yes'>
      <model usable='yes'>qemu64</model>
      <model usable='yes'>qemu32</model>
      <model usable='no'>phenom</model>
      <model usable='yes'>pentium3</model>
      <model usable='yes'>pentium2</model>
      <model usable='yes'>pentium</model>
      <model usable='no'>n270</model>
      <model usable='yes'>kvm64</model>
      <model usable='yes'>kvm32</model>
      <model usable='no'>coreduo</model>
      <model usable='no'>core2duo</model>
      <model usable='no'>athlon</model>
      <model usable='yes'>Westmere</model>
      <model usable='no'>Westmere-IBRS</model>
      <model usable='no'>Skylake-Server</model>
      <model usable='no'>Skylake-Server-IBRS</model>
      <model usable='no'>Skylake-Client</model>
      <model usable='no'>Skylake-Client-IBRS</model>
      <model usable='yes'>SandyBridge</model>
      <model usable='no'>SandyBridge-IBRS</model>
      <model usable='yes'>Penryn</model>
      <model usable='no'>Opteron_G5</model>
      <model usable='no'>Opteron_G4</model>
      <model usable='yes'>Opteron_G3</model>
      <model usable='yes'>Opteron_G2</model>
      <model usable='yes'>Opteron_G1</model>
      <model usable='yes'>Nehalem</model>
      <model usable='no'>Nehalem-IBRS</model>
      <model usable='no'>IvyBridge</model>
      <model usable='no'>IvyBridge-IBRS</model>
      <model usable='no'>Haswell</model>
      <model usable='no'>Haswell-noTSX</model>
      <model usable='no'>Haswell-noTSX-IBRS</model>
      <model usable='no'>Haswell-IBRS</model>
      <model usable='yes'>EPYC</model>
      <model usable='yes'>EPYC-IBPB</model>
      <model usable='yes'>Conroe</model>
      <model usable='no'>Broadwell</model>
      <model usable='no'>Broadwell-noTSX</model>
      <model usable='no'>Broadwell-noTSX-IBRS</model>
      <model usable='no'>Broadwell-IBRS</model>
      <model usable='yes'>486</model>
    </mode>
  </cpu>
  <devices>
    <disk supported='yes'>
      <enum name='diskDevice'>
        <value>disk</value>
        <value>cdrom</value>
        <value>floppy</value>
        <value>lun</value>
      </enum>
      <enum name='bus'>
        <value>ide</value>
        <value>fdc</value>
        <value>scsi</value>
        <value>virtio</value>
        <value>usb</value>
        <value>sata</value>
      </enum>
    </disk>
    <graphics supported='yes'>
      <enum name='type'>
        <value>sdl</value>
        <value>vnc</value>
        <value>spice</value>
      </enum>
    </graphics>
    <video supported='yes'>
      <enum name='modelType'>
        <value>vga</value>
        <value>cirrus</value>
        <value>vmvga</value>
        <value>qxl</value>
        <value>virtio</value>
      </enum>
    </video>
    <hostdev supported='yes'>
      <enum name='mode'>
        <value>subsystem</value>
      </enum>
      <enum name='startupPolicy'>
        <value>default</value>
        <value>mandatory</value>
        <value>requisite</value>
        <value>optional</value>
      </enum>
      <enum name='subsysType'>
        <value>usb</value>
        <value>pci</value>
        <value>scsi</value>
      </enum>
      <enum name='capsType'/>
      <enum name='pciBackend'>
        <value>default</value>
        <value>vfio</value>
      </enum>
    </hostdev>
  </devices>
%(features)s
</domainCapabilities>
"""

_fake_NodeDevXml = {
    "pci_0000_04_00_3": """
        <device>
        <name>pci_0000_04_00_3</name>
        <parent>pci_0000_00_01_1</parent>
        <driver>
            <name>igb</name>
        </driver>
        <capability type='pci'>
            <domain>0</domain>
            <bus>4</bus>
            <slot>0</slot>
            <function>3</function>
            <product id='0x1521'>I350 Gigabit Network Connection</product>
            <vendor id='0x8086'>Intel Corporation</vendor>
            <capability type='virt_functions'>
              <address domain='0x0000' bus='0x04' slot='0x10' function='0x3'/>
              <address domain='0x0000' bus='0x04' slot='0x10' function='0x7'/>
              <address domain='0x0000' bus='0x04' slot='0x11' function='0x3'/>
              <address domain='0x0000' bus='0x04' slot='0x11' function='0x7'/>
            </capability>
        </capability>
      </device>""",
    "pci_0000_04_10_7": """
      <device>
         <name>pci_0000_04_10_7</name>
         <parent>pci_0000_04_00_3</parent>
         <driver>
         <name>igbvf</name>
         </driver>
         <capability type='pci'>
          <domain>0</domain>
          <bus>4</bus>
          <slot>16</slot>
          <function>7</function>
          <product id='0x1520'>I350 Ethernet Controller Virtual Function
            </product>
          <vendor id='0x8086'>Intel Corporation</vendor>
          <capability type='phys_function'>
             <address domain='0x0000' bus='0x04' slot='0x00' function='0x3'/>
          </capability>
          <capability type='virt_functions'>
          </capability>
        </capability>
    </device>""",
    "pci_0000_04_11_7": """
      <device>
         <name>pci_0000_04_11_7</name>
         <parent>pci_0000_04_00_3</parent>
         <driver>
         <name>igbvf</name>
         </driver>
         <capability type='pci'>
          <domain>0</domain>
          <bus>4</bus>
          <slot>17</slot>
          <function>7</function>
          <product id='0x1520'>I350 Ethernet Controller Virtual Function
            </product>
          <vendor id='0x8086'>Intel Corporation</vendor>
          <numa node='0'/>
          <capability type='phys_function'>
             <address domain='0x0000' bus='0x04' slot='0x00' function='0x3'/>
          </capability>
          <capability type='virt_functions'>
          </capability>
        </capability>
    </device>""",
    "pci_0000_04_00_1": """
    <device>
      <name>pci_0000_04_00_1</name>
      <path>/sys/devices/pci0000:00/0000:00:02.0/0000:04:00.1</path>
      <parent>pci_0000_00_02_0</parent>
      <driver>
        <name>mlx5_core</name>
      </driver>
      <capability type='pci'>
        <domain>0</domain>
        <bus>4</bus>
        <slot>0</slot>
        <function>1</function>
        <product id='0x1013'>MT27700 Family [ConnectX-4]</product>
        <vendor id='0x15b3'>Mellanox Technologies</vendor>
        <iommuGroup number='15'>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x0'/>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x1'/>
        </iommuGroup>
        <numa node='0'/>
        <pci-express>
          <link validity='cap' port='0' speed='8' width='16'/>
          <link validity='sta' speed='8' width='16'/>
        </pci-express>
      </capability>
    </device>""",
    # libvirt  >= 1.3.0 nodedev-dumpxml
    "pci_0000_03_00_0": """
    <device>
        <name>pci_0000_03_00_0</name>
        <path>/sys/devices/pci0000:00/0000:00:02.0/0000:03:00.0</path>
        <parent>pci_0000_00_02_0</parent>
        <driver>
        <name>mlx5_core</name>
        </driver>
        <capability type='pci'>
        <domain>0</domain>
        <bus>3</bus>
        <slot>0</slot>
        <function>0</function>
        <product id='0x1013'>MT27700 Family [ConnectX-4]</product>
        <vendor id='0x15b3'>Mellanox Technologies</vendor>
        <capability type='virt_functions' maxCount='16'>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x2'/>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x3'/>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x4'/>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x5'/>
        </capability>
        <iommuGroup number='15'>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x0'/>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x1'/>
        </iommuGroup>
        <numa node='0'/>
        <pci-express>
          <link validity='cap' port='0' speed='8' width='16'/>
          <link validity='sta' speed='8' width='16'/>
        </pci-express>
      </capability>
    </device>""",
    "pci_0000_03_00_1": """
    <device>
      <name>pci_0000_03_00_1</name>
      <path>/sys/devices/pci0000:00/0000:00:02.0/0000:03:00.1</path>
      <parent>pci_0000_00_02_0</parent>
      <driver>
        <name>mlx5_core</name>
      </driver>
      <capability type='pci'>
        <domain>0</domain>
        <bus>3</bus>
        <slot>0</slot>
        <function>1</function>
        <product id='0x1013'>MT27700 Family [ConnectX-4]</product>
        <vendor id='0x15b3'>Mellanox Technologies</vendor>
        <capability type='virt_functions' maxCount='16'/>
        <iommuGroup number='15'>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x0'/>
          <address domain='0x0000' bus='0x03' slot='0x00' function='0x1'/>
        </iommuGroup>
        <numa node='0'/>
        <pci-express>
          <link validity='cap' port='0' speed='8' width='16'/>
          <link validity='sta' speed='8' width='16'/>
        </pci-express>
      </capability>
    </device>""",
        "net_enp2s1_02_9a_a1_37_be_54": """
    <device>
      <name>net_enp2s1_02_9a_a1_37_be_54</name>
      <path>/sys/devices/pci0000:00/0000:04:00.3/0000:04:10.7/net/enp2s1</path>
      <parent>pci_0000_04_10_7</parent>
      <capability type='net'>
        <interface>enp2s1</interface>
        <address>02:9a:a1:37:be:54</address>
        <link state='down'/>
        <feature name='rx'/>
        <feature name='tx'/>
        <feature name='sg'/>
        <feature name='tso'/>
        <feature name='gso'/>
        <feature name='gro'/>
        <feature name='rxvlan'/>
        <feature name='txvlan'/>
        <capability type='80203'/>
      </capability>
    </device>""",
    "net_enp2s2_02_9a_a1_37_be_54": """
    <device>
      <name>net_enp2s2_02_9a_a1_37_be_54</name>
      <path>/sys/devices/pci0000:00/0000:00:02.0/0000:02:02.0/net/enp2s2</path>
      <parent>pci_0000_04_11_7</parent>
      <capability type='net'>
        <interface>enp2s2</interface>
        <address>02:9a:a1:37:be:54</address>
        <link state='down'/>
        <feature name='rx'/>
        <feature name='tx'/>
        <feature name='sg'/>
        <feature name='tso'/>
        <feature name='gso'/>
        <feature name='gro'/>
        <feature name='rxvlan'/>
        <feature name='txvlan'/>
        <capability type='80203'/>
      </capability>
    </device>""",
     "pci_0000_06_00_0": """
    <device>
      <name>pci_0000_06_00_0</name>
      <path>/sys/devices/pci0000:00/0000:00:06.0</path>
      <parent></parent>
      <driver>
        <name>nvidia</name>
      </driver>
      <capability type="pci">
        <domain>0</domain>
        <bus>10</bus>
        <slot>1</slot>
        <function>5</function>
        <product id="0x0FFE">GRID M60-0B</product>
        <vendor id="0x10DE">Nvidia</vendor>
        <numa node="8"/>
        <capability type='mdev_types'>
          <type id='nvidia-11'>
            <name>GRID M60-0B</name>
            <deviceAPI>vfio-pci</deviceAPI>
            <availableInstances>16</availableInstances>
          </type>
        </capability>
      </capability>
    </device>""",
     "pci_0000_06_00_1": """
    <device>
      <name>pci_0000_06_00_1</name>
      <path>/sys/devices/pci0000:00/0000:00:06.1</path>
      <parent></parent>
      <driver>
        <name>i915</name>
      </driver>
      <capability type="pci">
        <domain>0</domain>
        <bus>6</bus>
        <slot>0</slot>
        <function>1</function>
        <product id="0x591d">HD Graphics P630</product>
        <vendor id="0x8086">Intel Corporation</vendor>
        <capability type='mdev_types'>
          <type id='i915-GVTg_V5_8'>
            <deviceAPI>vfio-pci</deviceAPI>
            <availableInstances>2</availableInstances>
          </type>
        </capability>
      </capability>
    </device>""",
     "mdev_4b20d080_1b54_4048_85b3_a6a62d165c01": """
    <device>
      <name>mdev_4b20d080_1b54_4048_85b3_a6a62d165c01</name>
      <path>/sys/devices/pci0000:00/0000:00:02.0/4b20d080-1b54-4048-85b3-a6a62d165c01</path>
      <parent>pci_0000_00_02_0</parent>
      <driver>
        <name>vfio_mdev</name>
      </driver>
      <capability type='mdev'>
        <type id='nvidia-11'/>
        <iommuGroup number='12'/>
      </capability>
    </device>
    """,
    # A PF with the VPD capability.
    "pci_0000_82_00_0": """
    <device>
      <name>pci_0000_82_00_0</name>
      <path>/sys/devices/pci0000:80/0000:80:03.0/0000:82:00.0</path>
      <parent>pci_0000_80_03_0</parent>
      <driver>
        <name>mlx5_core</name>
      </driver>
      <capability type='pci'>
        <class>0x020000</class>
        <domain>0</domain>
        <bus>130</bus>
        <slot>0</slot>
        <function>0</function>
        <product id='0xa2d6'>MT42822 BlueField-2 integrated ConnectX-6 Dx network controller</product>
        <vendor id='0x15b3'>Mellanox Technologies</vendor>
        <capability type='virt_functions' maxCount='8'>
          <address domain='0x0000' bus='0x82' slot='0x00' function='0x3'/>
          <address domain='0x0000' bus='0x82' slot='0x00' function='0x4'/>
          <address domain='0x0000' bus='0x82' slot='0x00' function='0x5'/>
          <address domain='0x0000' bus='0x82' slot='0x00' function='0x6'/>
          <address domain='0x0000' bus='0x82' slot='0x00' function='0x7'/>
          <address domain='0x0000' bus='0x82' slot='0x01' function='0x0'/>
          <address domain='0x0000' bus='0x82' slot='0x01' function='0x1'/>
          <address domain='0x0000' bus='0x82' slot='0x01' function='0x2'/>
        </capability>
        <capability type='vpd'>
          <name>BlueField-2 DPU 25GbE Dual-Port SFP56, Crypto Enabled, 16GB on-board DDR, 1GbE OOB management, Tall Bracket</name>
          <fields access='readonly'>
            <change_level>B1</change_level>
            <manufacture_id>foobar</manufacture_id>
            <part_number>MBF2H332A-AEEOT</part_number>
            <serial_number>MT2113X00000</serial_number>
            <vendor_field index='0'>PCIeGen4 x8</vendor_field>
            <vendor_field index='2'>MBF2H332A-AEEOT</vendor_field>
            <vendor_field index='3'>3c53d07eec484d8aab34dabd24fe575aa</vendor_field>
            <vendor_field index='A'>MLX:MN=MLNX:CSKU=V2:UUID=V3:PCI=V0:MODL=BF2H332A</vendor_field>
          </fields>
          <fields access='readwrite'>
            <asset_tag>fooasset</asset_tag>
            <vendor_field index='0'>vendorfield0</vendor_field>
            <vendor_field index='2'>vendorfield2</vendor_field>
            <vendor_field index='A'>vendorfieldA</vendor_field>
            <system_field index='B'>systemfieldB</system_field>
            <system_field index='0'>systemfield0</system_field>
          </fields>
        </capability>
        <iommuGroup number='65'>
          <address domain='0x0000' bus='0x82' slot='0x00' function='0x0'/>
        </iommuGroup>
        <numa node='1'/>
        <pci-express>
          <link validity='cap' port='0' speed='16' width='8'/>
          <link validity='sta' speed='8' width='8'/>
        </pci-express>
      </capability>
    </device>""",  # noqa:E501
    # A VF without the VPD capability with a PF that has a VPD capability.
    "pci_0000_82_00_3": """
    <device>
      <name>pci_0000_82_00_3</name>
      <path>/sys/devices/pci0000:80/0000:80:03.0/0000:82:00.3</path>
      <parent>pci_0000_80_03_0</parent>
      <driver>
        <name>mlx5_core</name>
      </driver>
      <capability type='pci'>
        <class>0x020000</class>
        <domain>0</domain>
        <bus>130</bus>
        <slot>0</slot>
        <function>3</function>
        <product id='0x101e'>ConnectX Family mlx5Gen Virtual Function</product>
        <vendor id='0x15b3'>Mellanox Technologies</vendor>
        <capability type='phys_function'>
          <address domain='0x0000' bus='0x82' slot='0x00' function='0x0'/>
        </capability>
        <iommuGroup number='99'>
          <address domain='0x0000' bus='0x82' slot='0x00' function='0x3'/>
        </iommuGroup>
        <numa node='1'/>
        <pci-express>
          <link validity='cap' port='0' speed='16' width='8'/>
          <link validity='sta' width='0'/>
        </pci-express>
      </capability>
    </device>""",
    # A VF with the VPD capability but without a parent defined in test data
    # so that the VPD cap is extracted from the VF directly.
    "pci_0001_82_00_3": """
    <device>
      <name>pci_0001_82_00_3</name>
      <path>/sys/devices/pci0001:80/0001:80:03.0/0001:82:00.3</path>
      <parent>pci_0001_80_03_0</parent>
      <driver>
        <name>mlx5_core</name>
      </driver>
      <capability type='pci'>
        <class>0x020000</class>
        <domain>1</domain>
        <bus>130</bus>
        <slot>0</slot>
        <function>3</function>
        <product id='0x101e'>ConnectX Family mlx5Gen Virtual Function</product>
        <vendor id='0x15b3'>Mellanox Technologies</vendor>
        <capability type='phys_function'>
          <address domain='0x0001' bus='0x82' slot='0x00' function='0x0'/>
        </capability>
        <capability type='vpd'>
          <name>BlueField-2 DPU 25GbE Dual-Port SFP56, Crypto Enabled, 16GB on-board DDR, 1GbE OOB management, Tall Bracket</name>
          <fields access='readonly'>
            <change_level>B1</change_level>
            <part_number>MBF2H332A-AEEOT</part_number>
            <serial_number>MT2113XBEEF0</serial_number>
            <vendor_field index='2'>MBF2H332A-AEEOT</vendor_field>
            <vendor_field index='3'>9644e3586190eb118000b8cef671bf3e</vendor_field>
            <vendor_field index='A'>MLX:MN=MLNX:CSKU=V2:UUID=V3:PCI=V0:MODL=BF2H332A</vendor_field>
            <vendor_field index='0'>PCIeGen4 x8</vendor_field>
          </fields>
        </capability>
        <iommuGroup number='99'>
          <address domain='0x0001' bus='0x82' slot='0x00' function='0x3'/>
        </iommuGroup>
        <numa node='1'/>
        <pci-express>
          <link validity='cap' port='0' speed='16' width='8'/>
          <link validity='sta' width='0'/>
        </pci-express>
      </capability>
    </device>""",  # noqa:E501
    # A VF without the VPD capability and without a parent PF defined
    # in the test data.
    "pci_0002_82_00_3": """
    <device>
      <name>pci_0002_82_00_3</name>
      <path>/sys/devices/pci0002:80/0002:80:03.0/0002:82:00.3</path>
      <parent>pci_0002_80_03_0</parent>
      <driver>
        <name>mlx5_core</name>
      </driver>
      <capability type='pci'>
        <class>0x020000</class>
        <domain>2</domain>
        <bus>130</bus>
        <slot>0</slot>
        <function>3</function>
        <product id='0x101e'>ConnectX Family mlx5Gen Virtual Function</product>
        <vendor id='0x15b3'>Mellanox Technologies</vendor>
        <capability type='phys_function'>
          <address domain='0x0002' bus='0x82' slot='0x00' function='0x0'/>
        </capability>
        <iommuGroup number='99'>
          <address domain='0x0002' bus='0x82' slot='0x00' function='0x3'/>
        </iommuGroup>
        <numa node='1'/>
        <pci-express>
          <link validity='cap' port='0' speed='16' width='8'/>
          <link validity='sta' width='0'/>
        </pci-express>
      </capability>
    </device>""",  # noqa:E501
}

_fake_NodeDevXml_parents = {
    name: etree.fromstring(xml).find("parent").text
    for name, xml in _fake_NodeDevXml.items()
}

_fake_NodeDevXml_children = collections.defaultdict(list)
for key, val in _fake_NodeDevXml_parents.items():
    _fake_NodeDevXml_children[val].append(key)
