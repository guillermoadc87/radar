# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime
import googlemaps
from geomap.helper_functions import get_radar, excel_number_to_date
from django.core.management.base import BaseCommand
from geomap.models import Property
from django.contrib.gis.geos import Point
import xlrd

types = {
    'New Coonstruction': 'NC',
    'Conversion/OverBuild': 'LC'
}

business_units = {
    'Fision Home': 'FH',
    'Fision Plus': 'FP',
    'Fision Stay': 'FS',
    'Fision Encore': 'FE,',
    'Fision Work': 'FW',
    'Fision U': 'FU',
    'Demo': 'Demo'
}

class Command(BaseCommand):
    args = '<foo bar ...>'
    help = 'our help string comes here'

    def _update_databse(self, excel=True):
        gmaps = googlemaps.Client(key='AIzaSyDbPjoUnqsFrFhzzB3Q3AuXwrF2cD9v2sI')
        if excel:
            wb = xlrd.open_workbook('My Radar- Engineering Division.xlsx')
            sh = wb.sheet_by_index(0)
            for rownum in range(2, sh.nrows):
                row_data = sh.row_values(rownum)
                name = row_data[1]
                address = row_data[13]
                status = row_data[2]
                property = Property.objects.filter(name=name)
                if address and not property and status != 'LOST  ':
                    geocode_result = gmaps.geocode(address)
                    if geocode_result:
                        lng = geocode_result[0]['geometry']['location']['lng']
                        lat = geocode_result[0]['geometry']['location']['lat']

                    units = row_data[6] if isinstance(row_data[6], int) else 1
                    business_unit = row_data[7]
                    _type = row_data[14]
                    mr_cert = excel_number_to_date(row_data[5])
                    gear_ready = excel_number_to_date(row_data[25])
                    gear_installed = excel_number_to_date(row_data[26])
                    cross_connect = excel_number_to_date(row_data[27])
                    print(name, units, status, status != 'LOST', type(status))
                    Property(name=name,
                             address=address,
                             location=Point(lng, lat),
                             units=units,
                             business_unit=business_unit,
                             type=_type,
                             mr_cert=mr_cert,
                             mdf_ready=gear_ready,
                             gear_installed=gear_installed,
                             cross_connect=cross_connect).save()
        else:
            radar = get_radar()

            for row in range(2, radar.row_count):
                name = radar.cell(row, 2).value
                address = radar.cell(row, 14).value
                units = radar.cell(row, 7).value
                business_unit = radar.cell(row, 8).value
                _type = radar.cell(row, 15).value
                gear_ready = radar.cell(row, 26).value
                gear_installed = radar.cell(row, 26).value
                cross_connect = radar.cell(row, 26).value
                mr_cert = radar.cell(row, 6).value
                print(name, units, gear_ready)
                property = Property.objects.filter(name=name)
                if property:
                    property[0].units = units
                    property[0].business_unit = business_units.get(business_unit, None)
                    property[0].type = types.get(_type, None)
                    try:
                        property[0].gear_ready = datetime.strptime(gear_ready, '%m/%d/%Y')
                        property[0].gear_installed = datetime.strptime(gear_installed, '%m/%d/%Y')
                        property[0].cross_connect = datetime.strptime(cross_connect, '%m/%d/%Y')
                        property[0].mr_cert = datetime.strptime(mr_cert, '%d-%b-%Y')
                    except ValueError:
                        print('Incorrect date format for %s' % (name,))
                    property[0].save()
                property.reverse()
                if address and not property:
                    print('google')
                    geocode_result = gmaps.geocode(address)
                    if geocode_result:
                        lng = geocode_result[0]['geometry']['location']['lng']
                        lat = geocode_result[0]['geometry']['location']['lat']

                        Property(name=name, address=address, location=Point(lng, lat)).save()
                time.sleep(1.5)
    def handle(self, *args, **options):
        self._update_databse()