#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2020/9/7 14:05 
# @Author : 吕秀刚
# @File : flush_wx_app_power.py
from __future__ import unicode_literals, absolute_import
import os
import sys
import django
import json
import time
import redis
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Opsys.settings")
django.setup()
from devopsApp import models
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "./%s   用户名" % sys.argv[0]
        sys.exit()
    else:
        obj = models.MyUser.objects.filter(first_name=sys.argv[1].strip())
        if not obj.exists():
            sys.exit("你输入的用户名不存在")

    username = obj[0].first_name
    redis_key = '%s_permission:灾备' % username
    zaibei_data ={'灾备环境':{}}
    try:
        service = models.Service.objects.exclude(status='offline').filter()
    except Exception as e:
        sys.exit("查询数据库失败，错误信息：%s" %json.dumps(e.args))
    else:
        for obj in service:
            service_name = obj.service_name
            service_ip = ['192.200.251.%s' % (int(item[0].strip().split('.')[-1]) - 10) for item in obj.host.all().values_list('ip')]
            zaibei_data['灾备环境'][service_name]={'ip': service_ip, 'start_time': time.mktime(time.localtime())}
        else:
            # 刷入数据到redis中，实现授权
            # 创建一个redis连接
            try:
                redis = redis.Redis(host='192.200.239.202', port=6379, db=0)
                redis.set(redis_key, json.dumps(zaibei_data))
            except Exception as e:
                sys.exit('刷入灾备权限失败，错误信息：%s' % json.dumps(e.args))
            else:
                print "输入灾备应用权限成功"

