from helper_functions import get_avail_int
from nornir.plugins.tasks.networking import netmiko_send_command

def get_neighbors(task):
    platform = task.host.platform
    r = ''
    if platform == 'nxos':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ip ospf neighbor vrf default',
            use_textfsm=True
        )
    elif platform == 'ios':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ip ospf neighbor',
            use_textfsm=True
        )
    elif platform == 'iosxr':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ospf neighbor',
            use_textfsm=True
        )

    return r

def get_vlans(task):
    platform = task.host.platform
    vlans = []
    if platform == 'nxos' or platform == 'ios':
        r = task.run(
            task=netmiko_send_command,
            command_string='show vlan',
            use_textfsm=True
        )
        vlans = [data['vlan_id'] for data in r[0].result]
    elif platform == 'iosxr':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ipv4 interface brief',
            use_textfsm=True
        )
        vlans = [data['intf'][3:] for data in r[0].result if 'BVI' in data['intf']]
    elif platform == 'cisco_xe':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ip interface brief',
            use_textfsm=True
        )
        vlans = [data['intf'][3:] for data in r[0].result if 'BDI' in data['intf']]
    return vlans

def get_arp(task):
    platform = task.host.platform
    if platform == 'iosxr' or platform == 'ios':
        r = task.run(
            task=netmiko_send_command,
            command_string='show arp',
            use_textfsm=True
        )
    else:
        r = task.run(
            task=netmiko_send_command,
            command_string='show ip arp',
            use_textfsm=True
        )

def get_bundle_ids(task):
    l2_bundles = {}
    l3_bundles = {}
    platform = task.host.platform

    if platform == 'iosxr':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ipv4 interface brief',
            use_textfsm=True
        )

        for data in r[0].result:
            if 'Bundle-Ether' in data['intf'] and data['ipaddr'] == 'unassigned':
                int_id = data['intf'][data['intf'].rfind('r')+1:].split('.')
                id = int_id.pop(0)
                if id not in l2_bundles:
                    l2_bundles[id] = []
                if int_id:
                    l2_bundles[id].append(int_id.pop())
            elif 'Bundle-Ether' in data['intf'] and data['ipaddr'] != 'unassigned':
                id = data['intf'][data['intf'].rfind('r') + 1:]
                l3_bundles[id] = data['ipaddr']

    return [{'l2_bundles': l2_bundles, 'l3_bundles': l3_bundles}]

def get_available_interfaces(task):
    platform = task.host.platform
    r = task.run(
        task=netmiko_send_command,
        command_string='show interfaces description',
        use_textfsm=True
    )

    int_avail = get_avail_int(r[0].result)

    if platform == 'iosxr':
        r = task.run(
            task=netmiko_send_command,
            command_string='admin show platform',
            use_textfsm=True
        )
        slots = {}
        for slot in r[0].result:
            if slot['state'] != 'READY' and 'RSP' not in slot['node']:
                num_slot = slot['node'].split('/')[1]
                if 'MOD' not in slot['type']:
                    if not slots.get(num_slot):
                        slots[num_slot] = {}
                    slots[num_slot][slot['type']] = []
        for inter in int_avail:
            int_slot1, int_slot2 = inter['port'].split('/')[1:3]
            for i, mpa in enumerate(slots[int_slot1]):
                if i == int(int_slot2):
                    slots[int_slot1][mpa].append(inter['port'])
        r = task.run(
            task=netmiko_send_command,
            command_string='show version',
            use_textfsm=True
        )
        max_slots = int(r[0].result[0]['slots'])
        for slot in range(max_slots):
            slot = str(slot)
            if not slots.get(slot):
                slots[slot] = {'Empty': ['Empty']}
    else:
        r = task.run(
            task=netmiko_send_command,
            command_string='show module',
            use_textfsm=True
        )
    return slots