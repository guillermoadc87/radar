from constants import MGN_INTERFACES, NEW_WIFI_MGN, OLD_WIFI_MGN
import re
from tqdm import tqdm
import yaml
import xlsxwriter
from datetime import datetime
from helper_functions import open_ssh_session, send_command, get_loopbacks, get_oui_for, get_market, create_host
from custom_tasks import get_neighbors, get_vlans, get_bundle_ids, get_arp
from nornir import InitNornir
from nornir.core.filter import F
from nornir.plugins.tasks.networking import netmiko_send_command
from .models import Device, Interface

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
        dev, create = Device.objects.get_or_create(mgn=pe)
    if not_inv_hosts:
        with open('geomap/inventory/hosts.yaml', "w") as f:
            yaml.dump(inventory, f)

def update_inv(inventory, result, elem_key='neighbor_id'):
    for hostname, data in result.items():
        data = data[0].result
        inventory[hostname]['data']['ospf']['stub_neighbor'] = []

        if type(data) == str:
            inventory[hostname]['data']['ospf']['stub'] = True
            continue

        for elem in data:
            neighbor = inventory.get(elem[elem_key], False)
            if neighbor and len(data) > 1:
                if neighbor['data']['ospf'].get('stub', False):
                    inventory[hostname]['data']['ospf']['stub_neighbor'].append(elem[elem_key])

        inventory[hostname]['data']['ospf']['neighbor'] = [elem[elem_key] for elem in data]

        not_stub_neigh = len(inventory[hostname]['data']['ospf']['neighbor']) - len(inventory[hostname]['data']['ospf']['stub_neighbor'])

        if len(data) < 2 or not_stub_neigh < 2:
            inventory[hostname]['data']['ospf']['stub'] = True
        else:
            inventory[hostname]['data']['ospf']['stub'] = False

def get_host_names():
    nr = InitNornir()

    with open('hosts.yaml') as f:
        # use safe_load instead load
        inventory = yaml.safe_load(f)

    result = nr.filter(~F(groups__contains='switch') & F(host_name='')).run(
        task=netmiko_send_command,
        command_string='show version',
        use_textfsm=True
    )

    for ip, data in result.items():
        if type(data) == str:
            print(ip)
            continue

        data = data[0].result[0]
        inventory[ip]['data']['host_name'] = data['hostname']
        dev, create = Device.objects.get_or_create(mgn=ip)
        dev.hostname = data['hostname']
        dev.model = data['hardware']
        dev.save()

    with open('hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def get_neighbors():
    nr = InitNornir()

    with open('hosts.yaml') as f:
        # use safe_load instead load
        inventory = yaml.safe_load(f)

    result = nr.filter(F(groups__contains='nxos') & ~F(groups__contains='switch')).run(
        task=netmiko_send_command,
        command_string='show ip ospf neighbor vrf default',
        use_textfsm=True
    )

    print('NXOS')
    update_inv(inventory, result, elem_key='neighbor_ipaddr')

    result = nr.filter(F(groups__contains='cisco-ios') & ~F(groups__contains='switch')).run(
        task=netmiko_send_command,
        command_string='show ip ospf neighbor',
        use_textfsm=True
    )
    print('IOS')
    update_inv(inventory, result)

    result = nr.filter(F(groups__contains='cisco-xr') & ~F(groups__contains='switch')).run(
        task=netmiko_send_command,
        command_string='show ospf neighbor',
        use_textfsm=True
    )
    print('XR')
    update_inv(inventory, result)

    with open('hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def stub_nodes(market=None, stub_neigh=False):
    nr = InitNornir()
    nr = nr.filter(F(ospf__stub=True) & ~F(groups__contains='switch'))

    if market:
        nr = nr.filter(F(groups__contains=market))

    stubs = nr.inventory.hosts

    if stub_neigh:
        return [stub for ip, stub in stubs.items() if stub['ospf']['stub_neighbor']]
    else:
        return [stub for ip, stub in stubs.items()]

def get_ospf_runtime(os='cisco-ios'):
    nr = InitNornir()

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
    nr = InitNornir()

    with open('hosts.yaml') as f:
        inventory = yaml.safe_load(f)

    hosts = nr.filter(tacacs=False).inventory.hosts

    for ip, hostdata in hosts.items():
        print(ip)
        print(inventory[ip]['data']['tacacs'])
        ssh = open_ssh_session(ip)
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

    with open('hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def add_switches():
    nr = InitNornir()
    cisco_ouis = get_oui_for("Cisco Systems, Inc")

    with open('geomap/inventory/hosts.yaml') as f:
        inventory = yaml.safe_load(f)

    result = nr.filter(~F(groups__contains='switch')).run(task=get_arp)

    for ip, data in result.items():
        print(ip)
        r_switches = list(nr.filter(router=ip).inventory.hosts.keys())
        print(r_switches)
        data = data[0].result
        for arp in data:
            try:
                if arp['age'] == '-':
                    continue
            except:
                print(ip, arp)
                break
            if arp['address'] not in r_switches and arp['interface'] in MGN_INTERFACES and arp['mac'][:7] in cisco_ouis:
                r_switches.append(arp['address'])
                create_host(inventory, arp['address'], ip)

    with open('geomap/inventory/hosts.yaml', "w") as f:
        yaml.dump(inventory, f)

def get_not_in_tacacs():
    data = []

    nr = InitNornir()
    hosts = nr.filter(tacacs=False).inventory.hosts

    for ip, hostdata in hosts.items():
        host = nr.filter(hostname=hostdata.data['router']).inventory.hosts[hostdata.data['router']]
        data.append([hostdata.hostname, f"{host.data['host_name']} ({host.hostname})", hostdata.groups[0], hostdata.data['tacacs']])

    return data

def get_old_wifi_mgn(os='cisco-ios'):
    nr = InitNornir(config_file='config.yaml')

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
            if arp['interface'] in OLD_WIFI_MGN:
                print(arp)
                for arp in data:
                    if arp['interface'] in NEW_WIFI_MGN:
                        print(arp)
                break

def get_ios_one_sub():
    nr = InitNornir()

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

    nr = InitNornir()

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

def get_excel_file(data):
    workbook = xlsxwriter.Workbook('cisco_ios_ospf_stats.xlsx')
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0, 'Switch')
    worksheet.write(0, 1, 'Router')
    worksheet.write(0, 2, 'Market')
    worksheet.write(0, 3, 'TACACS')

    for i, item in enumerate(data):
        try:
            worksheet.write(i+1, 0, item[0])
            worksheet.write(i+1, 1, item[1])
            worksheet.write(i+1, 2, item[2].upper())
            worksheet.write(i+1, 3, item[3])
        except:
            continue

    workbook.close()

def update_upstream_connections():
    nr = InitNornir(config_file='geomap/config.yaml')

    result = nr.filter(~F(groups__contains='switch')).run(
        task=netmiko_send_command,
        command_string='show cdp neighbor detail',
        use_textfsm=True
    )

    #with open('hosts.yaml') as f:
    #    inventory = yaml.safe_load(f)

    for ip, data in result.items():
        print(ip)
        q_device = nr.filter(hostname=ip).inventory.hosts[ip]
        data = data[0].result
        if type(data) == str:
            print(data)
            continue
        for entry in data:
            device = nr.filter(hostname=entry['mgmt_ip']).inventory.hosts.get(entry['mgmt_ip'])
            if device and 'switch' in device.groups and ('mgmt' not in entry['local_port'] or 'mgmt' not in entry['remote_port']):
                l_dev, created = Device.objects.get_or_create(mgn=ip)
                if created and 'switch' not in q_device.groups:
                    l_dev.router = True
                    l_dev.save()
                l_int, created = Interface.objects.get_or_create(name=entry['local_port'], device=l_dev)
                r_dev, created = Device.objects.get_or_create(mgn=entry['mgmt_ip'])
                r_dev.hostname = entry['dest_host']
                r_dev.model = entry['platform']
                r_dev.save()
                r_int = Interface.objects.get_or_create(name=entry['remote_port'], device=r_dev, connected=l_int)[0]
                l_int.connected = r_int
                l_int.save()
                print('Downstream Switch ' + entry['mgmt_ip'])
                #inventory[entry['mgmt_ip']]['data']['upstream'] = ip

    #with open('hosts.yaml', "w") as f:
    #    yaml.dump(inventory, f)

if __name__ == "__main__":
    start = datetime.now()
    #add_hosts()
    #get_host_names()
    #get_neighbors()
    #get_ospf_runtime(os='cisco-ios')
    #print(stub_nodes())
    #get_ospf_runtime()
    #add_switchs()
    #add_switchs(os='cisco-xr')
    #add_switchs(os='nxos')
    #get_cisco_oui()
    #data = get_not_in_tacacs()
    #get_excel_file(data)
    #get_old_wifi_mgn()
    #in_tacacs()
    #get_ios_one_sub()
    #print(equipment_in('10.63.255.23'))
    print((datetime.now() - start).total_seconds() / 60)