# Generated by Django 2.1.2 on 2018-11-03 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0015_auto_20181103_1551'),
    ]

    operations = [
        migrations.AlterField(
            model_name='property',
            name='router',
            field=models.CharField(choices=[('7600', '7600'), ('ASR9006', 'ASR9006')], max_length=200),
        ),
    ]
