# Generated by Django 2.2.2 on 2019-06-18 13:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0016_auto_20190618_1327'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='markets',
            field=models.CharField(blank=True, choices=[('sefl', 'SEFL'), ('swfl', 'SWFL'), ('cfl', 'cFL'), ('nc_sc', 'NC/SC'), ('atl', 'ATL')], max_length=50, null=True),
        ),
    ]
