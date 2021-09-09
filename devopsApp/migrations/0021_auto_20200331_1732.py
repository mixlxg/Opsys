# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-03-31 17:32
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devopsApp', '0020_auto_20200331_1719'),
    ]

    operations = [
        migrations.CreateModel(
            name='RedisExecLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=50)),
                ('exec_time', models.DateTimeField()),
                ('exec_com', models.TextField(max_length=4000)),
                ('exec_result', models.TextField(max_length=4000)),
            ],
        ),
        migrations.AlterField(
            model_name='deployversion',
            name='deploy_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 3, 31, 17, 32, 2, 360000)),
        ),
        migrations.AlterField(
            model_name='hostpowerapply',
            name='apply_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 3, 31, 17, 32, 2, 377000)),
        ),
        migrations.AlterField(
            model_name='jenkinsdeploylog',
            name='deploy_start_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 3, 31, 17, 32, 2, 355000)),
        ),
        migrations.AlterField(
            model_name='service',
            name='online_date',
            field=models.DateTimeField(default=datetime.datetime(2020, 3, 31, 17, 32, 2, 340000)),
        ),
    ]
