# Generated by Django 2.1.2 on 2019-05-31 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0012_device_node_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='statistics',
            name='maxin',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='statistics',
            name='maxout',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
