# Generated by Django 2.1.2 on 2019-05-09 00:12

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('reachability_tool', '0021_auto_20190508_0138'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='target',
            field=models.DateTimeField(default=datetime.datetime(2019, 6, 20, 0, 12, 7, 835370, tzinfo=utc)),
        ),
    ]
