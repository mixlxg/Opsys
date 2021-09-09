#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/3/7 11:15
    @FileName: service_discovery.py
    @Software: PyCharm
"""
from __future__ import unicode_literals,print_function
from mylogging import logger
import requests
import sys
import json
log_name = '/opt/usr/zabbix/externalscripts/service_discovery.log'
mlogger = logger(__file__, log_name)

if __name__ == '__main__':
    ip = sys.argv[1]
    zabbix_discovery_api = 'http://192.200.239.187/Opsys/interface/zabbix_service_discovery'
    try:
        result = requests.post(zabbix_discovery_api, data={'ip': ip})
    except Exception, e:
        mlogger.error('zabbix_agent %s 发起post请求失败，错误信息:%s' %(ip, e.message))
        print(json.dumps({'data': []}))
    else:
        if result.status_code != 200:
            mlogger.error('zabbix_agent %s 发起post 请求失败返回错误码：%s' %(ip, result.status_code))
            print(json.dumps({'data': []}))
        else:
            data = result.json()
            mlogger.info('zabbix_agent %s 发起post请求成功，成功数据：%s' %(ip, json.dumps(data)) )
            print(data['result'])

