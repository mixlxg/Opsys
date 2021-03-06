# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-04-21 17:29
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('devopsApp', '0022_auto_20200331_1814'),
    ]

    operations = [
        migrations.CreateModel(
            name='DbRelation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('dbtype', models.CharField(max_length=10)),
                ('isMaster', models.IntegerField(max_length=1)),
                ('conf_name', models.CharField(max_length=100)),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='devopsApp.Host')),
            ],
        ),
        migrations.CreateModel(
            name='DbUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=50)),
                ('password', models.CharField(max_length=64)),
            ],
        ),
        migrations.AlterField(
            model_name='deployversion',
            name='deploy_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 4, 21, 17, 29, 20, 755000)),
        ),
        migrations.AlterField(
            model_name='hostpowerapply',
            name='apply_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 4, 21, 17, 29, 20, 765000)),
        ),
        migrations.AlterField(
            model_name='jenkinsdeploylog',
            name='deploy_start_time',
            field=models.DateTimeField(default=datetime.datetime(2020, 4, 21, 17, 29, 20, 753000)),
        ),
        migrations.AlterField(
            model_name='service',
            name='online_date',
            field=models.DateTimeField(default=datetime.datetime(2020, 4, 21, 17, 29, 20, 746000)),
        ),
        migrations.AddField(
            model_name='dbrelation',
            name='opusername',
            field=models.ManyToManyField(to='devopsApp.DbUser'),
        ),
    ]
