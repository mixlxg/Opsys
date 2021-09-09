#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2020/1/16 9:33 
# @Author : 吕秀刚
# @File : application_offline_tasks.py

from __future__ import absolute_import, unicode_literals, print_function
import json
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded,TimeLimitExceeded
from ..lib.pyssh import PySsh
from ..celery import app

logger = get_task_logger(__name__)


@app.task(bind=True, soft_time_limit=300, time_limit=360)
def application_offline(self, *args, **kwargs):
    try:
        if kwargs['offline_type'] == 'static':
            return application_static_offline(**kwargs)
        elif kwargs['offline_type'] == 'java':
            return application_java_offline(**kwargs)
        else:
            pass
    except SoftTimeLimitExceeded as e:
        logger.error('下线%s 失败错误信息：%s' % (json.dumps(kwargs), e.message))
        return {'result': False, 'error_mess': "下线超时"}
    except TimeLimitExceeded as e:
        logger.error('下线%s 失败错误信息：%s' % (json.dumps(kwargs), e.message))
        return {'result': False, 'error_mess': "下线超时"}


def application_java_offline(*args, **kwargs):
    ip = kwargs['ip']
    username = kwargs['username']
    password = kwargs['password']
    stop_script = kwargs['stop_script']
    try:
        sshclient = PySsh(ip=ip, username=username, paswword=password)
    except Exception as e:
        logger.error('初始化%s sshclient停止节点服务失败，错误信息：%s' % (json.dumps(kwargs), e.message))
        return {'result': False, 'error_mess': e.message}
    else:
        try:
           result, mess = sshclient.invoke_comm(['su - webapp', stop_script])
        except Exception as e:
            logger.error('%s 下线失败，错误信息:%s' % (json.dumps(kwargs), mess))
            return {'result': False, 'error_mess': mess}
        else:
            if result:
                return {'result': True}
            else:
                return {'result': False, 'error_mess': mess}


def application_static_offline(*args, **kwargs):
    ip = kwargs['ip']
    target_path = kwargs['target_path']
    username = kwargs['username']
    password = kwargs['password']
    try:
        sshclient = PySsh(ip=ip, username=username, paswword=password)
    except Exception as e:
        logger.error('初始化%s sshclient执行删除nginx代码命令失败错误信息：%s' % (json.dumps(kwargs), e.message))
        return {'result': False, 'error_mess': e.message}
    else:
        cmd = 'rm -rvf %s' % target_path
        try:
           result, stdout_mess, stderr_mess = sshclient.comm(cmd)
        except Exception as e:
            logger.error('%s 下线失败，错误信息：%s' % (json.dumps(kwargs), e.message))
            return {'result': False, 'error_mess': e.message}
        else:
            if result:
                if len(stderr_mess) == 0:
                    return {'result': True}
                else:
                    return {'result': False, 'error_mess': ','.join(stderr_mess)}
            else:
                return {'result': False, 'error_mess': stderr_mess}
