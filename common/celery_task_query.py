#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/5/21 14:18
    @FileName: celery_task_query.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, absolute_import
from celery_tasks.celery import app


def query_task(task_id):
    task_obj = app.AsyncResult(task_id)
    if task_obj.state == 'SUCCESS':
        if task_obj.result['result']:
            return {'result': 'SUCCESS', 'data': task_obj.result}
        else:
            return {'result': 'FAILURE', 'data': task_obj.result}
    elif task_obj.state == 'FAILURE':
        return {'result': 'FAILURE', 'data': task_obj.result.message}
    else:
        return {'result': task_obj.state}


def query_group_task(group_id):
    group_result_list = []
    group_obj = app.GroupResult.restore(group_id)
    for task_obj in group_obj.children:
        if task_obj.state == 'SUCCESS':
            if task_obj.result['result']:
                group_result_list.append({
                    'result': 'SUCCESS', 'data': task_obj.result
                })
            else:
                group_result_list.append(
                    {'result': 'FAILURE', 'data': task_obj.result}
                )
        elif task_obj.state == 'FAILURE':
            group_result_list.append({'result': 'FAILURE', 'data': task_obj.result.message})
        else:
            group_result_list.append({'result': task_obj.state})