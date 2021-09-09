# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-10-25 09:55
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devopsApp', '0007_auto_20190906_1121'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppRestart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=50)),
                ('service_name', models.CharField(max_length=100)),
                ('group_task_id', models.CharField(max_length=20)),
            ],
        ),
        migrations.AlterField(
            model_name='deployversion',
            name='deploy_time',
            field=models.DateTimeField(default=datetime.datetime(2019, 10, 25, 9, 55, 21, 204000)),
        ),
        migrations.AlterField(
            model_name='jenkinsdeploylog',
            name='deploy_start_time',
            field=models.DateTimeField(default=datetime.datetime(2019, 10, 25, 9, 55, 21, 203000)),
        ),
        migrations.AlterField(
            model_name='service',
            name='online_date',
            field=models.DateTimeField(default=datetime.datetime(2019, 10, 25, 9, 55, 21, 195000)),
        ),
    ]
