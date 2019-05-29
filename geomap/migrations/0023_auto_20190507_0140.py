# Generated by Django 2.1.2 on 2019-05-07 01:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0022_auto_20190426_0314'),
    ]

    operations = [
        migrations.CreateModel(
            name='Interface',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=200, null=True)),
                ('bundle_id', models.IntegerField(blank=True, null=True)),
                ('connected', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='connected_to', to='geomap.Interface')),
            ],
        ),
        migrations.RemoveField(
            model_name='device',
            name='parent',
        ),
        migrations.AddField(
            model_name='interface',
            name='device',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='geomap.Device'),
        ),
    ]
