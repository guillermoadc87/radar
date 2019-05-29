# Generated by Django 2.1.2 on 2019-03-11 03:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0014_auto_20190206_0306'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='equiment',
            name='hostname',
        ),
        migrations.AddField(
            model_name='equiment',
            name='configured',
            field=models.DateField(blank=True, null=True, verbose_name='Configured'),
        ),
        migrations.AddField(
            model_name='equiment',
            name='installed',
            field=models.DateField(blank=True, null=True, verbose_name='Installed'),
        ),
        migrations.AddField(
            model_name='equiment',
            name='model',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='equiment',
            name='type',
            field=models.CharField(choices=[('router', 'Router'), ('switch', 'Switch'), ('chassis', 'Chassis'), ('ONT', 'ONT')], max_length=120, null=True),
        ),
    ]
