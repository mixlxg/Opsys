#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/5/21 11:03
    @FileName: create_job_id.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, absolute_import
import hashlib


def create_job_id(username, servicename):
    md5 = hashlib.md5()
    md5.update('%s|%s' % (username, servicename))
    return md5.hexdigest()
