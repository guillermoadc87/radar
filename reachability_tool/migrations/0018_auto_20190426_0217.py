# Generated by Django 2.1.2 on 2019-04-26 02:17

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('reachability_tool', '0017_auto_20190402_0324'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='target',
            field=models.DateTimeField(default=datetime.datetime(2019, 6, 7, 2, 17, 24, 539936, tzinfo=utc)),
        ),
    ]
