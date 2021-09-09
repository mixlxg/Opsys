#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/5/10 16:31
    @FileName: test.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
from  ..celery import app
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@app.task()
def add(x,y):
    print x+y
    return x+y

@app.task()
def mult(x,y):
    return x+y

@app.task(bind=True)
def dump_context(self):
    print self.request

@app.task(bind=True)
def mylog_test(self):
    logger.error(self.request)


@app.task(bind=True)
def add1(self, x, y):
    try:
        print 'test'
        something_raising()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60,max_retries=1)