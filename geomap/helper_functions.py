import os
import re
import xmltodict
import time
import paramiko
import gspread
import xlrd
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from .constants import ROUTER, CISCO_USERNAME, CISCO_PASSWORD, MARKETS, NOT_INTERFACES

def create_host(inv, ip, market_ip):
    xe = re.compile("IOS-XE")
    ios = re.compile("Cisco IOS Software")
    xr = re.compile("Cisco IOS XR Software")
    nxos = re.compile("NXOS: version")
    ssh = open_ssh_session(ip, CISCO_USERNAME, CISCO_PASSWORD)

    if ssh and ssh != 2:
        chan = ssh.invoke_shell()
        output = send_command(chan, 'sh ver')
        m = xe.search(output)
        if m:
            inv[ip] = init_host(ip, groups=['cisco-xe', get_market(market_ip)])
        m = ios.search(output)
        if m:
            inv[ip] = init_host(ip, groups=['cisco-ios', get_market(market_ip)])
        m = xr.search(output)
        if m:
            inv[ip] = init_host(ip, groups=['cisco-xr', get_market(market_ip)])
        m = nxos.search(output)
        if m:
            inv[ip] = init_host(ip, groups=['cisco-nxos', get_market(market_ip)])
        else:
            inv[ip] = init_host(ip, groups=['sg350', get_market(market_ip)])
    elif ssh == 2:
        inv[ip] = init_host(ip, groups=['sg350', get_market(market_ip)])
        inv[ip]['data']['tacacs'] = False
    else:
        inv[ip] = init_host(ip, groups=['cisco-ios', get_market(market_ip)])
        inv[ip]['data']['tacacs'] = False
    if ip != market_ip:
        inv[ip]['data']['router'] = market_ip
        inv[ip]['groups'].append('switch')

def get_avail_int(ints):
    avail_int = []
    for int in ints:
        if not int['descrip'] and 'down' in int['status'] and int['port'][:2] not in NOT_INTERFACES:
            avail_int.append(int)
    return avail_int

def get_oui_for(vendor):
    ouis = []
    with open('vendorMacs.xml', encoding='latin1') as fd:
        doc = xmltodict.parse(fd.read())
        for key, data in doc.items():
            for key in data:
                if key == 'VendorMapping':
                    for item in data[key]:
                        if item['@vendor_name'] == vendor:
                            oui = item['@mac_prefix'].replace(':', '').lower()
                            oui = oui[:4] + '.' + oui[4:]
                            ouis.append(oui)
    return ouis

def get_loopbacks(ip=ROUTER):
    ssh = open_ssh_session(ip)

    if ssh:
        chan = ssh.invoke_shell()
        output = send_command(chan, 'sh ip route | i /32')
        p = re.compile("10\.(63|68|84|86|88|92|93|94|98|110|199)\.255\.\d{1,3}\/32")
        return [pe.group()[:-3] for pe in p.finditer(output)]

    return []

def init_host(ip, groups=[]):
    return {
        'data': {
            'host_name': '',
            'ospf': {
                'neighbor': [],
                'stub': False,
                'stub_neighbor': []},
            },
        'groups': groups,
        'hostname': ip,
    }

def get_market(ip):
    octet = ip.split('.')[1]
    return MARKETS.get(octet, 'unknown')

def open_ssh_session(hostname, username, password, port=22, channel=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname, username=username, password=password, port=port, sock=channel, allow_agent=False, look_for_keys=False)
    except paramiko.ssh_exception.BadAuthenticationType:
        return 2
    except:
        return False

    return ssh

def get_output(channel):
    chunk = ''
    time.sleep(2)
    while channel.recv_ready():
        chunk += channel.recv(9999).decode('ISO-8859-1')
        time.sleep(1)
    return chunk

def send_command(chan, command):
    get_output(chan)
    chan.send('terminal length 0\n')
    get_output(chan)
    chan.send(command + '\n')
    return get_output(chan)

def count_interfaces(ip, int):
    chan = open_ssh_session(ip)
    output = send_command(chan, 'sh int des | i admin | i %s' % (int,))
    l = output.split('\n')
    l = [line for line in l if int in line]
    line_cards = {}
    for line in l[1:]:
        if 'EDT' in output:
            lcn = line.split('/')[1]
        else:
            lcn = line.split('/')[0][2]
        if not lcn in line_cards:
            line_cards[lcn] = 1
        else:
            line_cards[lcn] += 1
    return line_cards

def get_radar():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('Radar-8d27863f5496.json', scope)
    #print(os.getcwd())

    client = gspread.authorize(creds)

    return client.open('My Radar- Engineering Division').sheet1

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return '{0}/{1}'.format(instance.property.slug, filename)

def excel_number_to_date(number):
    if not number or not isinstance(number, float):
        return None
    return datetime(*xlrd.xldate_as_tuple(number, 0))

def get_subnet(units):
    if units > 1:
        for bit in range(1, 33):
            if 2**bit-3 > units:
                return 32-bit
    return 29

def get_subnets(units):
    pass

def card_bay_number(name):
    try:
        return name.split('/')[1]
    except:
        return 0

def ping_test(ip):
    not_passed = os.system('ping -c 1 %s' % (ip))
    if not not_passed:
        return True
    return False

