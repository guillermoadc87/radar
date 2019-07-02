from datetime import datetime
from orionsdk import SwisClient
from geomap.constants import NOT_PHY_INTS, NPM_SERVER, CISCO_USERNAME, CISCO_PASSWORD
from geomap.helper_functions import get_standard_port
from geomap.models import Device, Interface, Statistics
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    args = '<foo bar ...>'
    help = 'our help string comes here'

    def _update_stats(self):
        date = datetime.now()
        swis = SwisClient(NPM_SERVER, CISCO_USERNAME, CISCO_PASSWORD)
        results = swis.query(
            "SELECT I.InterfaceAlias, I.Name, I.NodeID, ROUND(MaxOutBpsToday/1000000000,2) AS MaxOutGbpsToday, I.MaxInBpsToday/1000000000 AS MaxInGbpsToday FROM Orion.NPM.Interfaces I WHERE I.Speed >=10000000000 AND I.AdminStatus=1")
        for row in results['results']:
            device = Device.objects.filter(node_id=row['NodeID'])
            if device and row['Name'][:2] not in NOT_PHY_INTS:
                device = Device.objects.get(node_id=row['NodeID'])
                s_port_name = get_standard_port(row['Name'])
                maxin = row['MaxInGbpsToday']
                maxout = row['MaxOutGbpsToday']
                interface, c = Interface.objects.get_or_create(name=s_port_name, device=device)
                stats, c = Statistics.objects.get_or_create(interface=interface, date=date)
                stats.maxin=maxin
                stats.maxout=maxout
                stats.save()

    def handle(self, *args, **options):
        self._update_stats()
