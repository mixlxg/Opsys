# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-09-06 10:48
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devopsApp', '0005_auto_20190903_0848'),
    ]

    operations = [
        migrations.AddField(
            model_name='deployprojectapply',
            name='really_deploy_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='deployversion',
            name='deploy_time',
            field=models.DateTimeField(default=datetime.datetime(2019, 9, 6, 10, 48, 29, 304000)),
        ),
        migrations.AlterField(
            model_name='jenkinsdeploylog',
            name='deploy_start_time',
            field=models.DateTimeField(default=datetime.datetime(2019, 9, 6, 10, 48, 29, 301000)),
        ),
        migrations.AlterField(
            model_name='service',
            name='online_date',
            field=models.DateTimeField(default=datetime.datetime(2019, 9, 6, 10, 48, 29, 294000)),
        ),
    ]