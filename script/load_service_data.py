#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/3/6 14:48
    @FileName: load_service_data.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, absolute_import, print_function
import django
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Opsys.settings")
django.setup()
from devopsApp import models

with open('/tmp/service.csv', 'r') as f:
    service_data = f.readlines()
    service_data = service_data[1:]

# 处理csv数据成字典类型，方便入库处理
service_last_data = []
for item in service_data:
    tmp_list = item.strip().split(',')
    tmp_dict = {'service_name': tmp_list[0].strip(), 'type': tmp_list[2].strip(), 'service_port': tmp_list[3].strip(),
                'base_path': tmp_list[4].strip(), 'status': tmp_list[5].strip(), 'ip': tmp_list[8].strip()}
    service_last_data.append(tmp_dict)

# 开始入库，并添加多对多关系
for item in service_last_data:
    host_ip = item['ip']
    del(item['ip'])
    service_tuple = models.Service.objects.get_or_create(**item)
    service_obj = service_tuple[0]
    host_obj = models.Host.objects.filter(ip=host_ip)
    service_obj.host.add(*host_obj)

service_obj = models.Service.objects.filter(service_name='woService-listen')
service_obj.values('service_name', 'host__ip')

