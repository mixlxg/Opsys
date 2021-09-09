#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/5/9 17:12
    @FileName: celeryconfig.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
## broker config
broker_url = 'redis://192.200.239.202:6379/1'
imports = ('celery_tasks.tasks.application_tasks',
           'celery_tasks.tasks.application_restart_tasks',
           'celery_tasks.tasks.application_offline_tasks',)
result_backend = 'redis://192.200.239.202:6379/1'
enable_utc = False
timezone = 'Asia/Shanghai'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
broker_transport_options = {
    'visibility_timeout': 7200,
    'fanout_prefix': True,
    'fanout_patterns': True
}
result_expires = 604800
# 记录stated 状态
task_track_started = True
#每个进程可执行的最大task数，可以有效地放着内存泄漏
worker_max_tasks_per_child = 1000
worker_max_memory_per_child = 120000