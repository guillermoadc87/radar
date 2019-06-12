# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from geomap.nornir_api import add_routers, add_switches, update_connections, get_host_names

class Command(BaseCommand):
    args = '<foo bar ...>'
    help = 'our help string comes here'

    def _update_inventory(self):
        #add_routers()
        #get_host_names()
        #add_switches()
        update_connections()

    def handle(self, *args, **options):
        self._update_inventory()
