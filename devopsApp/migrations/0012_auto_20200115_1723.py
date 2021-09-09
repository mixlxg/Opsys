# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-01-15 17:23
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devopsApp', '0011_auto_20191028_1715'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppOffline',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=50)),
                ('service_name', models.CharField(max_length=100)),
                ('group_task_id', models.TextField(default=b'', max_length=4000)),
                ('task_id', models.TextField(default=b'', max_length=2000)),
            ],
        ),
        migrations.AlterField(
            model_name='deployversion',
            name='deploy_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 1, 15, 17, 23, 1, 180000)),
        ),
        migrations.AlterField(
            model_name='jenkinsdeploylog',
            name='deploy_start_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 1, 15, 17, 23, 1, 178000)),
        ),
        migrations.AlterField(
            model_name='service',
            name='online_date',
            field=models.DateTimeField(default=datetime.datetime(2020, 1, 15, 17, 23, 1, 171000)),
        ),
    ]