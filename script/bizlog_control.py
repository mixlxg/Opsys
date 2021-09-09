#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/4/17 11:15
    @FileName: bizlog_control.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
from mylogging import logger
#import readline
import sys
import os
import redis
from django.contrib.auth.hashers import check_password
#实例化一个logger 写日志对象
mlogger = logger('bizlog_control', '/home/bizlog/bizlog_control.log')


class Mredis(object):
    def __init__(self, ip, db=0, port=6379):
        self._ip = ip
        self._db = db
        self._port = port
        if not hasattr(Mredis, 'pool'):
            Mredis.pool = Mredis.__getpool(self._ip, self._db, self._port)
        if Mredis.pool is False:
            Mredis.Redis = False
        else:
            self.Redis = redis.Redis(connection_pool=Mredis.pool)

    @staticmethod
    def __getpool(ip, db, port):
        try:
            pool=redis.ConnectionPool(max_connections=5, host=ip, db=db, port=port)
        except redis.ConnectionError, e:
            mlogger.error('初始化redis报错：%s' %e.message)
            return False
        else:
            return pool



if __name__ == '__main__':
    Rclient = Mredis(ip='192.200.239.202').Redis

