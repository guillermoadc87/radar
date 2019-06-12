import os

NEW_WIFI_MGN = ['BVI751', 'BVI752', 'BVI753', 'BVI754', 'BVI755', 'Vlan751', 'Vlan752', 'Vlan753', 'Vlan754', 'Vlan755']
OLD_WIFI_MGN = ['BVI203', 'BVI201', 'Vlan203', 'Vlan201']
MGN_INTERFACES = ['BVI200', 'BVI201', 'Vlan200', 'Vlan201', 'Vlan203', 'Vlan203']
Q_ROUTER = '10.63.255.163'
NPM_SERVER = 'thor.gethotwired.com'
CISCO_USERNAME = 'guillermo.diaz'
CISCO_PASSWORD = 'Wktkm1987*'
MARKETS = {
    '63': 'sefl',
    '64': 'sefl',
    '68': 'sefl',
    '84': 'swfl',
    '85': 'swfl',
    '86': 'cfl',
    '88': 'cfl',
    '89': 'cfl',
    '92': 'cfl',
    '93': 'nc_sc',
    '94': 'nc_sc',
    '98': 'cfl',
    '99': 'cfl',
    '110': 'atl',
    '118': 'atl',
    '199': 'atl',
}
NOT_PHY_INTS = ['BV', 'BD', 'Vl', 'Po', 'BE', 'Mg', 'PT', 'Bu', 'Co', 'Nu']

SHOW_MODULE_TMP = open(os.path.join('geomap', 'ntc-templates', 'templates', 'cisco_ios_show_module.template'))
SHOW_MODULE_KEYS = ['module', 'ports', 'type', 'model', 'serial']

AVAIL_INT_GRAPH = ['cisco ASR9K Series', 'cisco CISCO7606-S', 'cisco CISCO7609-S']

PROJECT_TYPES = (
    (('New Construction'), ('New Construction')),
    (('Conversion/OverBuild'), ('Conversion/OverBuild')),
    (('Update'), ('Update'))
    )

BUSSINESS_UNITS = (
    (('Fision Home'), ('Fision Home')),
    (('Fision Plus'), ('Fision Plus')),
    (('Fision Stay'), ('Fision Stay')),
    (('Fision Encore'), ('Fision Encore')),
    (('Fision Work'), ('Fision Work')),
    (('Fision U'), ('Fision U')),
    (('Demo'), ('Demo')),
)

ROUTER_MODELS = (
    ('7600', '7600'),
    ('ASR9K', 'ASR9K')
    )

SWITCH_MODELS = (
    ('N9K-C93180YC-EX', 'N9K-C93180YC-EX'),
    ('WS-C2960X-24PS-L', 'WS-C2960X-24PS-L'),
    ('WS-C3750G-24PS', 'WS-C3750G-24PS'),
    ('ME-3400-24TS-A', 'ME-3400-24TS-A'),
    ('ME-3400G-12CS-A', 'ME-3400G-12CS-A'),
    ('ASR-920-12CZ-A', 'ASR-920-12CZ-A'),
    ('SF302-08', 'SF302-08'),
    ('SG300-10PP', 'SG300-10PP'),
)

NETWORKS = (
    ('MediaRoom', 'MediaRoom'),
    ('ProIdiom', 'ProIdiom'),
    ('ClearIP', 'ClearIP')
)

ONT_MODELS = (
    ('G0240G-A', 'G0240G-A'),
    ('G0241G-A', 'G0241G-A')
)

CONTRACT_STATUS = (
    ('Not Applicable', 'Not Applicable'),
    ('In Sales Phase', 'In Sales Phase'),
    ('Pendnig', 'Pendnig'),
    ('Received', 'Received'),
    ('LOST', 'LOST'),
    ('NOT Approved to Upgrade', 'NOT Approved to Upgrade'),
)

SLOT_COUNT = {
    'ASR 9006': 4,
    'ASR 9010': 8,
}

STANDARD_PORT_NAMES = {
    'GigabitEthernet': 'Gi',
    'TenGigE': 'Te',
    'TenGigabitEthernet': 'Te',
    'Ethernet': 'Eth'
}

DONT_INCLUDE_IN_SCAN = ['cisco ASR9K Series', 'cisco CISCO7606-S', 'cisco CISCO7609-S']