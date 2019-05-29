# Generated by Django 2.1.2 on 2019-03-23 00:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0017_auto_20190312_0022'),
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', models.CharField(blank=True, max_length=200, null=True)),
                ('loopback', models.GenericIPAddressField()),
                ('type', models.CharField(choices=[('router', 'Router'), ('switch', 'Switch'), ('chassis', 'Chassis'), ('ONT', 'ONT')], max_length=120, null=True)),
                ('configured', models.DateField(blank=True, null=True, verbose_name='Configured')),
                ('installed', models.DateField(blank=True, null=True, verbose_name='Installed')),
                ('prop', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='geomap.Property', verbose_name='Property')),
            ],
        ),
        migrations.CreateModel(
            name='Topology',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.RemoveField(
            model_name='equiment',
            name='prop',
        ),
        migrations.DeleteModel(
            name='Equiment',
        ),
        migrations.AddField(
            model_name='device',
            name='topology',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='geomap.Topology'),
        ),
        migrations.AddField(
            model_name='property',
            name='topology',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='geomap.Topology'),
        ),
    ]
