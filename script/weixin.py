#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/4/16 16:04
    @FileName: weixin.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
import sys
import requests
import json
if __name__ == '__main__':
    id = sys.argv[2]
    cont = sys.argv[3]
    requests.post('http://192.200.239.202:8888/', data=json.dumps({'id': id, 'cont': cont}))