import os
import gspread
import xlrd
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

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