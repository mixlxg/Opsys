#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2020/9/2 9:38 
# @Author : 吕秀刚
# @File : jmx.py
"""
@explain: 定时任务获取jmx信息插入到influxdb数据库通过调用url：http://192.200.239.187:8088/jmx/getJmxToInfluxDb
"""
import requests
import time
if __name__ == '__main__':
    try:
        res = requests.post(url='http://192.200.239.187:8088/jmx/getJmxToInfluxDb')
    except Exception as e:
        print time.asctime(time.localtime()), e
    else:
        print time.asctime(time.localtime()), res.json()
