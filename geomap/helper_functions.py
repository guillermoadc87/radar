import os, re, time
import paramiko
import gspread
import xmltodict
import xlrd
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from .constants import MARKETS, CISCO_USERNAME, CISCO_PASSWORD, Q_ROUTER, NOT_PHY_INTS, STANDARD_PORT_NAMES

def get_standard_port(port):
    m = re.search("\d", port)
    if m:
        port_name = port[:m.start()]
        port_number = port[m.start():]
        s_port_name = STANDARD_PORT_NAMES.get(port_name)
        return s_port_name + port_number if s_port_name else port
    return port

def down_interfaces(interfaces):
    l = []
    for interface in interfaces:
        if not interface['descrip'] and interface['port'][:2] not in NOT_PHY_INTS and 'down' in interface['status']:
            l.append(interface)
    return l

def port_slot_card_pos(platform, port):
    if platform == 'iosxr':
        slot, card = port.split('/')[1:3]
        return [int(slot)+1, int(card)]
    elif platform == 'ios':
        num = port[2:].split('/')[0]
        return map(int, [num, 0])
    else:
        return map(int, port[3:].split('/'))


def get_market(ip):
    octet = ip.split('.')[1]
    return MARKETS.get(octet, 'unknown')

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

def create_host(inv, ip, market_ip):
    xe = re.compile("IOS-XE")
    ios = re.compile("Cisco IOS Software")
    xr = re.compile("Cisco IOS XR Software")
    nxos = re.compile("NXOS: version")
    ssh = open_ssh_session(ip, CISCO_USERNAME, CISCO_PASSWORD, 22)

    if ssh and ssh != 2:
        chan = ssh.invoke_shell()
        output = send_command(chan, 'sh ver')
        xe = xe.search(output)
        ios = ios.search(output)
        xr = xr.search(output)
        nxos = nxos.search(output)
        if xe:
            inv[ip] = init_host(ip, groups=['cisco-xe', get_market(market_ip)])
        elif ios:
            inv[ip] = init_host(ip, groups=['cisco-ios', get_market(market_ip)])
        elif xr:
            inv[ip] = init_host(ip, groups=['cisco-xr', get_market(market_ip)])
        elif nxos:
            inv[ip] = init_host(ip, groups=['nxos', get_market(market_ip)])
        else:
            inv[ip] = init_host(ip, groups=['sg350', get_market(market_ip)])
    elif ssh == 2:
        inv[ip] = init_host(ip, groups=['sg350', get_market(market_ip)])
        inv[ip]['data']['tacacs'] = False
    else:
        inv[ip] = init_host(ip, groups=['unknown', get_market(market_ip)])
        inv[ip]['data']['tacacs'] = False
    if ip != market_ip:
        inv[ip]['data']['router'] = market_ip
        inv[ip]['groups'].append('switch')

def get_oui_for(vendor):
    ouis = []
    with open('geomap/vendorMacs.xml', encoding='latin1') as fd:
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

def get_loopbacks(ip=Q_ROUTER, username=CISCO_USERNAME, password=CISCO_PASSWORD):
    ssh = open_ssh_session(ip, username, password, 22)

    if ssh:
        chan = ssh.invoke_shell()
        output = send_command(chan, 'sh ip route | i /32')
        p = re.compile("10\.(63|68|84|86|88|92|93|94|98|110|199)\.255\.\d{1,3}\/32")
        return [pe.group()[:-3] for pe in p.finditer(output)]

    return []

def get_radar():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('Radar-8d27863f5496.json', scope)
    print(os.getcwd())

    client = gspread.authorize(creds)

    return client.open('My Radar- Engineering Division').sheet1

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return '{0}/{1}/{2}'.format(instance.property.slug, filename)

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