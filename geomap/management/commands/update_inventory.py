import os
from geomap.nornir_api import add_routers, add_switches
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    args = '<foo bar ...>'
    help = 'our help string comes here'

    def _update_inventory(self):
        print(os.getcwd())
        add_routers()
        add_switches()

    def handle(self, *args, **options):
        self._update_inventory()