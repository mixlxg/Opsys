# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-05-13 17:26
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devopsApp', '0023_auto_20200421_1729'),
    ]

    operations = [
        migrations.CreateModel(
            name='mysqldeadlock_log',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deadlock_id', models.DateTimeField(null=True, verbose_name=b'\xe6\xad\xbb\xe9\x94\x81\xe6\x97\xb6\xe9\x97\xb4')),
                ('deadlock_transaction_content', models.TextField(null=True, verbose_name=b'\xe4\xba\x8b\xe5\x8a\xa1\xe5\x86\x85\xe5\xae\xb9')),
                ('create_date', models.DateTimeField(auto_now_add=True, null=True, verbose_name=b'\xe5\x88\x9b\xe5\xbb\xba\xe6\x97\xb6\xe9\x97\xb4')),
            ],
        ),
        migrations.CreateModel(
            name='MysqlInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mysql_cluster_name', models.CharField(max_length=100)),
                ('version', models.CharField(max_length=50)),
                ('host_ip', models.CharField(max_length=50)),
                ('conf_path', models.CharField(max_length=150)),
                ('base_path', models.CharField(max_length=150)),
                ('service_port', models.IntegerField(max_length=10)),
                ('role', models.CharField(max_length=10)),
                ('db_type', models.CharField(max_length=10)),
                ('service_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.RemoveField(
            model_name='dbrelation',
            name='host',
        ),
        migrations.RemoveField(
            model_name='dbrelation',
            name='opusername',
        ),
        migrations.AlterField(
            model_name='deployversion',
            name='deploy_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 5, 13, 17, 26, 56, 341000)),
        ),
        migrations.AlterField(
            model_name='hostpowerapply',
            name='apply_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 5, 13, 17, 26, 56, 354000)),
        ),
        migrations.AlterField(
            model_name='jenkinsdeploylog',
            name='deploy_start_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 5, 13, 17, 26, 56, 339000)),
        ),
        migrations.AlterField(
            model_name='service',
            name='online_date',
            field=models.DateTimeField(default=datetime.datetime(2020, 5, 13, 17, 26, 56, 332000)),
        ),
        migrations.DeleteModel(
            name='DbRelation',
        ),
        migrations.DeleteModel(
            name='DbUser',
        ),
    ]
