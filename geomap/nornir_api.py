import re
from tqdm import tqdm
import yaml
import xlsxwriter
from datetime import datetime
from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.tasks.networking import netmiko_send_command
from .custom_tasks import get_neighbors, get_vlans, get_bundle_ids, get_arp, get_avail_interfaces
from .helper_functions import create_host, get_oui_for, open_ssh_session, get_loopbacks, get_standard_port
from .constants import CISCO_USERNAME, CISCO_PASSWORD, MGN_INTERFACES, NOT_PHY_INTS
from .models import Device, Interface
from django.db.models import Q
from geomap.constants import CISCO_USERNAME

vlan_tag = {
    '20': 'MGN',
    '21': 'VOICE',
    '41': 'VOICE',
    '45': 'IPTV',
    '30': 'DATA',
    '50': 'DATA',
    '69': 'WIFI_DATA',
    '700': 'WIFI_DATA',
    '70': 'WIFI_ROUTER',
}

def get_vlan_tag(vlan):
    return vlan_tag.get(vlan, 'UNKNOWN')

def add_routers():
    with open('geomap/inventory/hosts.yaml') as f:
        inventory = yaml.safe_load(f)

    if inventory:
        inv_hosts = list(inventory.keys())
        live_hosts = get_loopbacks()
        not_inv_hosts = list(set(live_hosts) - set(inv_hosts))
    else:
        inventory = {}
        not_inv_hosts = get_loopbacks()
    print(not_inv_hosts)
    for pe in tqdm(not_inv_hosts):
        create_host(inventory, pe, pe)
        Device.objects.get_or_create(mgn=pe)

    if not_inv_hosts:
        with open('geomap/inventory/hosts.yaml', "w") as f:
            yaml.dump(inventory, f)

def add_switches():
    nr = InitNornir(config_file='geomap/config.yaml')
    cisco_ouis = get_oui_for('Cisco Systems, Inc')

    with open('geomap/inventory/hosts.yaml') as f:
        inventory = yaml.safe_load(f)

    result = nr.filter(~F(groups__contains='switch') & ~F(groups__contains='unknown')).run(task=get_arp)

    for router, data in result.items():
        print('Router: ', router)
        r_switches = list(nr.filter(router=router).inventory.hosts.keys())
        print(r_switches)
        data = data[1].result
        if not data or type(data) == str:
            print('Return String ', router)
            continue
        for arp in data:
            if arp['age'] == '-':
                continue
            if arp['address'] not in r_switches and arp['interface'] in MGN_INTERFACES and arp['mac'][:7] in cisco_ouis:
                print('Added Switch: ', arp['address'])
                r_switches.append(arp['address'])
                create_host(inventory, arp['address'], router)
                Device.objects.get_or_create(mgn=arp['address'])

    with open('geomap/inventory/hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def update_connections():
    nr = InitNornir(config_file='geomap/config.yaml')
    m_list = []
    result = nr.filter(~F(groups__contains='sg350') & ~F(groups__contains='unknown')).run(
        task=netmiko_send_command,
        command_string='show cdp neighbor detail',
        use_textfsm=True,
        enable=True
    )

    #with open('hosts.yaml') as f:
    #    inventory = yaml.safe_load(f)

    for ip, data in result.items():
        print(ip)
        #router = nr.filter(hostname=ip).inventory.hosts.get(ip)
        data = data[0].result
        if type(data) == str or len(data) == 1:
            continue
        for entry in data:
            if entry['mgmt_ip'] == ip:
                continue
            #print(entry['platform'] == 'MikroTik', '703' in entry['remote_port'], entry['remote_port'])
            entry['dest_host'] = entry['dest_host'].split('.h')[0] if entry['dest_host'] else ''
            entry['local_port'] = get_standard_port(entry['local_port'])
            entry['remote_port'] = get_standard_port(entry['remote_port'])
            device = nr.inventory.hosts.get(entry['mgmt_ip'])
            if not device:
                device = nr.filter(host_name=entry['dest_host']).inventory.hosts
                for host in device:
                    entry['mgmt_ip'] = device[host].hostname
            if device:
                print(entry['mgmt_ip'], entry['local_port'], entry['remote_port'])
                dev, c = Device.objects.get_or_create(mgn=ip)
                int_l , c = Interface.objects.get_or_create(name=entry['local_port'], device=dev)
                dev, c = Device.objects.get_or_create(mgn=entry['mgmt_ip'])
                dev.hostname = entry['dest_host']
                dev.model = entry['platform']
                dev.save()
                try:
                    int_r, c = Interface.objects.get_or_create(name=entry['remote_port'], device=dev)
                    int_r.connected = int_l
                    int_r.save()
                    int_l.connected = int_r
                    int_l.save()
                except:
                    print('Double check this ports config: ', entry['local_port'])

    #with open('hosts.yaml', "w") as f:
    #    yaml.dump(inventory, f)

    return m_list

def update_interface_status():
    nr = InitNornir(config_file='geomap/config.yaml')

    result = nr.filter(~F(groups__contains='sg350') & ~F(groups__contains='unknown') & ~F(groups__contains='nxos')).run(
        task=netmiko_send_command,
        command_string='show interface description',
        use_textfsm=True
    )
    for ip, data in result.items():
        data = data[0].result
        if type(data) == str:
            continue
        for interface in data:
            if interface['port'][:2] not in NOT_PHY_INTS:
                dev = Device.objects.get(mgn=ip)
                inter, c = Interface.objects.get_or_create(name=interface['port'], device=dev)

def get_host_names():
    nr = InitNornir(config_file='geomap/config.yaml')

    with open('geomap/inventory/hosts.yaml') as f:
        # use safe_load instead load
        inventory = yaml.safe_load(f)

    result = nr.filter(~F(groups__contains='switch') & ~F(groups__contains='unknown') & F(host_name='')).run(
        task=netmiko_send_command,
        command_string='show version',
        use_textfsm=True
    )

    for ip, data in result.items():
        try:
            hostname = data[0].result[0]['hostname']
            inventory[ip]['data']['host_name'] = hostname
        except TypeError:
            print(ip)
            #inventory[ip]['groups'].pop(1)
            #inventory[ip]['groups'].insert(1, 'sg350')
            print(inventory[ip]['groups'])

    with open('geomap/inventory/hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def get_host_and_models():
    devices = Device.objects.get(Q(hostname__isnull=True) | Q(model__isnull=True))



def update_inv(inventory, result):
    for hostname, data in result.items():
        data = data[1].result
        inventory[hostname]['data']['ospf']['stub_neighbor'] = []

        if type(data) == str:
            if 'Traceback' in data:
                print(hostname, data)
                continue
            inventory[hostname]['data']['ospf']['stub'] = True
            continue

        for elem in data:
            neighbor = inventory.get(elem['neighbor_id'], False)
            if neighbor and len(data) > 1:
                if neighbor['data']['ospf'].get('stub', False):
                    inventory[hostname]['data']['ospf']['stub_neighbor'].append(elem['neighbor_id'])

        inventory[hostname]['data']['ospf']['neighbor'] = [elem['neighbor_id'] for elem in data]

        not_stub_neigh = len(inventory[hostname]['data']['ospf']['neighbor']) - len(inventory[hostname]['data']['ospf']['stub_neighbor'])

        if len(data) < 2 or not_stub_neigh < 2:
            inventory[hostname]['data']['ospf']['stub'] = True
        else:
            inventory[hostname]['data']['ospf']['stub'] = False

        #if hostname in ['10.68.255.253']:
        #    print(inventory[hostname]['data']['ospf']['neighbor'], inventory[hostname]['data']['ospf']['stub_neighbor'], inventory[hostname]['data']['ospf']['stub'])

def update_neighbors():
    nr = InitNornir(config_file='geomap/config.yaml')

    with open('geomap/inventory/hosts.yaml') as f:
        # use safe_load instead load
        inventory = yaml.safe_load(f)

    result = nr.filter(~F(groups__contains='switch')).run(task=get_neighbors)

    update_inv(inventory, result)

    with open('geomap/inventory/hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def update_vlans():
    nr = InitNornir(config_file='geomap/config.yaml')
    result = nr.filter(F(groups__contains='cisco-ios') & F(groups__contains='switch') & F(tacacs=True)).run(task=get_vlans)

    with open('hosts.yaml') as f:
        # use safe_load instead load
        inventory = yaml.safe_load(f)

    for hostname, data in result.items():
        vlans = data[1].result
        if not type(vlans) == str:
            vlans = {vlan:get_vlan_tag(vlan)for vlan in vlans}
            inventory[hostname]['data']['vlans'] = vlans
        else:
            print(hostname)
            #for i, group in enumerate(inventory[hostname]['groups']):
            #    if group == 'cisco-ios':
            #        inventory[hostname]['groups'].pop(i)
            #        inventory[hostname]['groups'].insert(i, 'cisco-xe')

    with open('hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def get_bundled_interfaces(ip):
    nr = InitNornir(config_file='geomap/config.yaml')

    result = nr.filter(hostname=ip).run(
        task=netmiko_send_command,
        command_string='show bundle',
        use_textfsm=True
    )

    output = result[ip][0].result
    ints = {}
    bundle = None
    p = re.compile('(Te|Gi)\d\/\d\/\d\/\d+|Bundle-Ether\d+')

    for match in p.finditer(output):
        int = match.group()
        if 'Bundle-Ether' in int:
            bundle = int[int.rfind('r') + 1:]
        else:
            ints[int] = bundle

def get_graph_data(dev):
    if dev.mgn:
        data = [{'id': '0', 'parent': '', 'name': 'Available Int'}]
        nr = InitNornir(config_file='geomap/config.yaml')
        result = nr.filter(hostname=dev.mgn).run(task=get_avail_interfaces)

        chassis = result[dev.mgn][0].result
        print(result[dev.mgn][1].result)
        for i, slot in enumerate(chassis):
            data.append({'id': str(i+1), 'parent': '0', 'name': f'Slot {slot}'})
            for j, card in enumerate(chassis[slot]):
                data.append({'id': str(i+1)+str(j), 'parent': str(i+1), 'name': card if card else 'Empty'})
                if not chassis[slot][card]:
                    data.append({'id': str(i+1)+str(j)+'0', 'parent': str(i+1)+str(j), 'name': 'Full' if card else 'Empty', 'value': 1})
                else:
                    for z, ports in enumerate(chassis[slot][card]):
                        data.append({'id': str(i+1)+str(j)+str(z), 'parent': str(i+1)+str(j), 'name': ports, 'value': 1})
        return data
    return []
def stub_nodes(market=None, stub_neigh=False):
    nr = InitNornir(config_file='geomap/config.yaml')
    nr = nr.filter(F(ospf__stub=True) & ~F(groups__contains='switch'))

    if market:
        nr = nr.filter(F(groups__contains=market))

    stubs = nr.inventory.hosts

    if stub_neigh:
        return [stub for ip, stub in stubs.items() if stub['ospf']['stub_neighbor']]
    else:
        return [stub for ip, stub in stubs.items()]

def get_ospf_runtime(os='cisco-ios'):
    nr = InitNornir(config_file='geomap/config.yaml')

    if os == 'cisco-ios':
        command = 'show ip ospf statistics'
    else:
        command = 'show ospf statistics spf'

    with open('hosts.yaml') as f:
        # use safe_load instead load
        inventory = yaml.safe_load(f)

    result = nr.filter(F(groups__contains=os) & ~F(groups__contains='switch')).run(
        task=netmiko_send_command,
        command_string=command,
        use_textfsm=True
    )

    for ip, data in result.items():
        min_run = float('inf')
        max_run = 0
        for r_data in data[0].result:
            if type(r_data) == str:
                continue
            min_run = min(min_run, int(r_data['runtime']))
            max_run = max(max_run, int(r_data['runtime']))
        inventory[ip]['data']['ospf']['rt_min'] = min_run
        inventory[ip]['data']['ospf']['rt_max'] = max_run

    with open('hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def in_tacacs():
    nr = InitNornir(config_file='geomap/config.yaml')

    with open('geomap/inventory/hosts.yaml') as f:
        inventory = yaml.safe_load(f)

    hosts = nr.inventory.hosts

    for ip, hostdata in hosts.items():
        print(ip)
        #print(inventory[ip]['data']['tacacs'])
        ssh = open_ssh_session(ip, CISCO_USERNAME, CISCO_PASSWORD, 22)
        if ssh and ssh != 2:
            inventory[ip]['data']['tacacs'] = True
        elif ssh == 2:
            for i, group in enumerate(inventory[ip]['groups']):
                if group == 'cisco-ios':
                    inventory[ip]['groups'].pop(i)
                    inventory[ip]['groups'].insert(i, 'sg350')
                    print(inventory[ip]['groups'])
            inventory[ip]['data']['tacacs'] = False
        else:
            inventory[ip]['data']['tacacs'] = False
        print(inventory[ip]['data']['tacacs'])

    with open('geomap/inventory/hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def get_not_in_tacacs():
    data = []

    nr = InitNornir(config_file='geomap/config.yaml')
    hosts = nr.filter(tacacs=False).inventory.hosts

    for ip, hostdata in hosts.items():
        host = nr.filter(hostname=hostdata.data['router']).inventory.hosts[hostdata.data['router']]
        data.append([hostdata.hostname, f"{host.data['host_name']} ({host.hostname})", hostdata.groups[0], hostdata.data['tacacs']])

    return data

def get_old_wifi_mgn(os='cisco-ios'):
    nr = InitNornir(config_file='geomap/config.yaml')

    if os == 'cisco-ios':
        command = 'show ip arp'
    else:
        command = 'show arp'

    result = nr.filter(F(groups__contains=os) & ~F(groups__contains='switch')).run(
        task=netmiko_send_command,
        command_string=command,
        use_textfsm=True
    )

    for ip, data in result.items():
        print(ip)
        data = data[0].result
        for arp in data:
            if arp['interface'] in old_wifi_mgn:
                print(arp)
                for arp in data:
                    if arp['interface'] in new_wifi_mgn:
                        print(arp)
                break

def get_ios_one_sub():
    nr = InitNornir(config_file='geomap/config.yaml')

    result = nr.filter(F(groups__contains='cisco-ios') & ~F(groups__contains='switch')).run(
        task=netmiko_send_command,
        command_string='show inventory',
        use_textfsm=True
    )
    m_count = 0
    for ip, data in result.items():
        data = data[0].result
        if type(data) == str:
            print(ip)
            continue
        for module in data:
            if 'switching' in module['name']:
                m_count += 1
        if m_count <= 1:
            print(ip, 'less')

def equipment_in(ip):
    eq = []

    nr = InitNornir(config_file='geomap/config.yaml')

    result = nr.filter(hostname=ip).run(
        task=netmiko_send_command,
        command_string='show inventory',
        use_textfsm=True
    )
    r_data = result[ip][0].result[0]
    eq.append([r_data['pid'], r_data['sn']])

    result = nr.filter(router=ip, tacacs=True).run(
        task=netmiko_send_command,
        command_string='show inventory',
        use_textfsm=True
    )

    for ip, data in result.items():
        data = data[0].result[0]
        if type(data) == str:
            continue
        eq.append([data['pid'], data['sn']])

    return eq

def get_ruckus():
    #entries = []
    nr = InitNornir(config_file='geomap/config.yaml')
    ruckus_oui = get_oui_for("Ruckus Wireless")

    result = nr.filter(F(groups__contains='cisco-ios') & F(groups__contains='switch') & F(groups__contains='swfl')).run(
        task=netmiko_send_command,
        command_string='show mac address-table',
        use_textfsm=True
    )

    with open('hosts.yaml') as f:
        inventory = yaml.safe_load(f)

    for switch, data in result.items():
        router = nr.filter(hostname=switch).inventory.hosts[switch].data['router']
        data = data[0].result
        if type(data) == str:
            print(switch)
            continue
        for cam in data:
            try:
                if cam['type'] == 'STATIC':
                    continue
            except:
                print(switch)
                continue
            if cam['vlan'] in ['200', '201', '202', '203'] and 'Po' not in cam['destination_port'] and cam['destination_address'][:7] in ruckus_oui:
                inventory[switch]['data']['old_mgn'] = True
                inventory[inventory[switch]['router']]['data']['old_mgn'] = True
                break
                #entries.append([router, switch, cam['destination_address'], cam['destination_port']])

    with open('hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

    #return entries

def get_excel_file(data):
    workbook = xlsxwriter.Workbook('mikrotiks.xlsx')
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, 'Router')
    worksheet.write(0, 1, 'Mikrotik')

    for i, item in enumerate(data):
        #print(item.data)
        try:
            worksheet.write(i + 1, 0, item[0])
            worksheet.write(i + 1, 1, item[1])
        except:
            continue

    workbook.close()

if __name__ == "__main__":
    start = datetime.now()
    #add_routers()
    #netbrains_file()
    #get_host_names()
    #update_vlans()
    #update_neighbors()
    #update_neighbors()
    #update_neighbors()
    #get_ospf_runtime(os='cisco-ios')
    #data = stub_nodes()
    #print(data)
    #get_ospf_runtime()
    add_switches()
    #get_cisco_oui()
    #data = get_not_in_tacacs()
    #data = get_ruckus()
    #data = upadate_upstream_connections()
    #get_excel_file(data)
    #get_old_wifi_mgn()
    #in_tacacs()
    #get_ios_one_sub()
    #print(equipment_in('10.63.255.23'))
    print((datetime.now() - start).total_seconds() / 60)
