#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/5/10 15:28
    @FileName: celery.py
    @Software: PyCharm
"""
from __future__ import unicode_literals,absolute_import
from celery import Celery
from . import celeryconfig
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
app = Celery('celery_tasks')
app.config_from_object(celeryconfig)

if __name__ == '__main__':
    app.start()
