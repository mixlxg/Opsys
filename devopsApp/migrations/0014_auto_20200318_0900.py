# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-03-18 09:00
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devopsApp', '0013_auto_20200313_1053'),
    ]

    operations = [
        migrations.CreateModel(
            name='HostPowerApply',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=50)),
                ('project_name', models.CharField(max_length=100)),
                ('service_name', models.CharField(max_length=2000)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('apply_reason', models.CharField(max_length=1000)),
                ('is_agree', models.IntegerField(blank=True, max_length=2)),
            ],
        ),
        migrations.AlterField(
            model_name='deployversion',
            name='deploy_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 3, 18, 9, 0, 39, 141000)),
        ),
        migrations.AlterField(
            model_name='jenkinsdeploylog',
            name='deploy_start_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 3, 18, 9, 0, 39, 139000)),
        ),
        migrations.AlterField(
            model_name='service',
            name='online_date',
            field=models.DateTimeField(default=datetime.datetime(2020, 3, 18, 9, 0, 39, 133000)),
        ),
    ]
