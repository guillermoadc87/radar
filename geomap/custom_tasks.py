import re
import textfsm
from nornir.plugins.tasks.networking import netmiko_send_command
from .helper_functions import down_interfaces, port_slot_card_pos
from .constants import SHOW_MODULE_TMP, SHOW_MODULE_KEYS, SLOT_COUNT

def get_arp(task):
    platform = task.host.platform
    if platform == 'ios' or platform == 'nxos' or platform == 'cisco_xe':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ip arp',
            use_textfsm=True
        )
    elif platform == 'iosxr':
        r = task.run(
            task=netmiko_send_command,
            command_string='show arp',
            use_textfsm=True
        )

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

    return r[0].result

def get_vlans(task):
    vlans = []
    platform = task.host.platform

    if platform == 'nxos' or platform == 'ios':
        r = task.run(
            task=netmiko_send_command,
            command_string='show vlan',
            use_textfsm=True
        )
        vlans = [int(data['vlan_id']) for data in r[0].result]
    elif platform == 'iosxr':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ipv4 interface brief',
            use_textfsm=True
        )
        vlans = [int(data['intf'][3:]) for data in r[0].result if 'BVI' in data['intf']]
        vlans.extend([1, 1002, 1003, 1004])
    elif platform == 'cisco_xe':
        r = task.run(
            task=netmiko_send_command,
            command_string='show ip interface brief',
            use_textfsm=True
        )
        vlans = [int(data['intf'])[3:] for data in r[0].result if 'BDI' in data['intf']]
        vlans.extend([1, 1002, 1003, 1004])
    return vlans

def get_bundle_parameters(task):
    bundles = []
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
        bundles = [{'l2_bundles': l2_bundles, 'l3_bundles': l3_bundles}]
    return bundles

def get_interfaces_bundle(task):
    ints = {}
    platform = task.host.platform
    if platform == 'iosxr':
        r = task.run(
            task=netmiko_send_command,
            command_string='show bundle',
        )

        output = r[0].result
        bundle = None
        p = re.compile('(Te|Gi)\d\/\d\/\d\/\d+|Bundle-Ether\d+')

        for match in p.finditer(output):
            int = match.group()
            if 'Bundle-Ether' in int:
                bundle = int[int.rfind('r') + 1:]
            else:
                ints[int] = bundle
    return ints

def get_interfaces(task):
    r = task.run(
        task=netmiko_send_command,
        command_string='show interface description',
        use_textfsm=True
    )

    avail_ints = down_interfaces(r[0].result)

    return [inter['port'] for inter in avail_ints]

def get_avail_interfaces(task):
    slot_matrix = {}
    platform = task.host.platform

    r = task.run(
        task=netmiko_send_command,
        command_string='show interface description',
        use_textfsm=True
       )

    avail_ints = down_interfaces(r[0].result)

    if platform == 'iosxr':
        r = task.run(
            task=netmiko_send_command,
            command_string='admin show platform',
            use_textfsm=True
        )

        slots = [slot for slot in r[0].result if slot['state'] != 'READY' and 'RSP' not in slot['node']]

        for slot in slots:
            slot_num, slot_port = slot['node'].split('/')[1:3]
            slot_num = int(slot_num) + 1
            slot_port = slot_port if 'CPU' not in slot_port else '0'
            if 'MOD' not in slot['type']:
                #print(slot['type'])
                if not slot_matrix.get(slot_num):
                    slot_matrix[slot_num] = {}
                slot_matrix[slot_num][f"{slot_port}-{slot['type']}"] = []

        r = task.run(
            task=netmiko_send_command,
            command_string='show version',
            use_textfsm=True
        )
        model = r[0].result[0].get('hardware')
        max_slots = SLOT_COUNT.get(model, 0)
        for slot_num in range(1, max_slots+1):
            if not slot_matrix.get(slot_num):
                slot_matrix[slot_num] = {}
                slot_matrix[slot_num][''] = []
    elif platform == 'ios':
        r = task.run(
            task=netmiko_send_command,
            command_string='show module',
            use_textfsm=True
        )
        re_table = textfsm.TextFSM(SHOW_MODULE_TMP)
        data = re_table.ParseText(r[0].result)
        for slot in data:
            slot = dict(zip(SHOW_MODULE_KEYS, slot))
            slot_num = int(slot['module'])
            if not slot_matrix.get(slot_num):
                slot_matrix[slot_num] = {}
            slot_matrix[slot_num][slot['model']] = []
    for inter in avail_ints:
        int_slot_num, int_card_num = port_slot_card_pos(platform, inter['port'])
        for i, card in enumerate(slot_matrix[int_slot_num]):
            if i == int_card_num:
                slot_matrix[int_slot_num][card].append(inter['port'])

    return slot_matrix
