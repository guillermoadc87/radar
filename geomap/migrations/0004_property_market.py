# Generated by Django 2.1.2 on 2018-12-02 18:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0003_property_channel_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='market',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
