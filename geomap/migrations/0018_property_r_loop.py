# Generated by Django 2.1.2 on 2018-11-03 16:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0017_auto_20181103_1558'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='r_loop',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
