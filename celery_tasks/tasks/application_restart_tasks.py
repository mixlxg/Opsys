#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@File    : application_restart_tasks.py
@Time    : 2019/10/23 13:49
@Author  : 吕秀刚
@Software: PyCharm
"""
from __future__ import absolute_import, unicode_literals, print_function
import json
import time
import threading
import telnetlib
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded,TimeLimitExceeded
from ..lib.pyssh import PySsh
from ..celery import app

logger = get_task_logger(__name__)


@app.task(bind=True, soft_time_limit=120, time_limit=150)
def app_restart(self, *args, **kwargs):
    try:
        try:
           sshclient = PySsh(ip=kwargs['ip'], paswword=kwargs['password'], username='root')
        except Exception, e:
            logger.error('初始化%s ssh链接失败错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False), e.message))
            return {'result': False, 'error_mess': '创建ssh链接失败', 'data':kwargs}
        else:
            # 停止进程
            try:
                stop_res = app_stop(sshclient, kwargs)
            except Exception, e:
                return {'result': False, 'error_mess': '停止进程失败,错误信息：%s' % e.message, 'data': kwargs}
            else:
                if stop_res['result'] is False:
                    return {'result': False, 'error_mess': '停止进程失败', 'data': kwargs}
            # 启动进程
            try:
                start_res = app_start(sshclient, kwargs)
            except Exception, e:
                return {'result': False, 'error_mess': '启动进程失败错误信息：%s' % e.message, 'data': kwargs}
            else:
                if start_res['result'] is False:
                    return {'result': False, 'error_mess': '启动进程失败', 'data': kwargs}
            # 校验端口是否正常
            # 休眠30秒钟
            time.sleep(30)
            try:
                check_res = check_port(kwargs)
            except Exception, e:
                return {'result': False, 'error_mess': '服务没有起来，错误信息：%s' % e.message, 'data': kwargs}
            else:
                if check_res['result'] is False:
                    return {'result': False, 'error_mess': '服务没有起来', 'data': kwargs}
    except SoftTimeLimitExceeded, e:
        logger.error('重启应用%s 超时，错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False), e.message))
        return {'result': False, 'error_mess': '重启超时', 'data': kwargs}
    except TimeLimitExceeded as e:
        logger.error('重启应用%s 超时，错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False), e.message))
        return {'result': False, 'error_mess': '重启超时', 'data': kwargs}
    else:
        return {'result': True, 'data': kwargs}


@app.task(bind=True, soft_time_limit=120, time_limit=150)
def app_stop_task(self, *args, **kwargs):
    try:
        try:
            sshclient = PySsh(ip=kwargs['ip'], paswword=kwargs['password'], username='root')
        except Exception, e:
            logger.error('初始化%s ssh链接失败错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False), e.message))
            return {'result': False, 'error_mess': '创建ssh链接失败', 'data': kwargs}
        else:
            try:
                stop_res = app_stop(sshclient, kwargs)
            except Exception, e:
                return {'result': False, 'error_mess': '停止进程失败,错误信息：%s' % e.message, 'data': kwargs}
            else:
                if stop_res['result'] is False:
                    return {'result': False, 'error_mess': '停止进程失败', 'data': kwargs}
            time.sleep(5)
            try:
                check_res = check_port(kwargs)
            except Exception, e:
                return {'result': False, 'error_mess': '检测服务端口发生异常：%s' % e.message, 'data': kwargs}
            else:
                if check_res['result']:
                    return {'result': False, 'error_mess': '进程停止失败', 'data': kwargs}
    except SoftTimeLimitExceeded, e:
        logger.error('停止任务%s 超时' % json.dumps(kwargs, ensure_ascii=False))
        return {'result': False, 'error_mess': '停止超时', 'data': kwargs}
    except TimeLimitExceeded as e:
        logger.error('停止任务%s 超时' % json.dumps(kwargs, ensure_ascii=False))
        return {'result': False, 'error_mess': '停止超时', 'data': kwargs}
    else:
        return {'result': True, 'data': kwargs}


def app_stop(ssh, kwargs):
    stop_script = kwargs['stop_script']
    try:
        res = ssh.invoke_comm(['su - webapp', stop_script])
    except Exception, e:
        logger.error('%s停止服务进程失败，错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False),e.message))
        return {'result': False}
    else:
        if res[0]:
            return {'result': True}
        else:
            logger.error('%s停止服务进程失败错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False),res[1]))
            return {'result': False}


def app_start(ssh, kwargs):
    start_script = kwargs['start_script']
    try:
        res = ssh.invoke_comm(['su - webapp', start_script])
    except Exception, e:
        logger.error('%s启动进程失败，错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False),e.message))
        return {'result': False}
    else:
        if res[0]:
            return {'result': True}
        else:
            logger.error('%s启动进程失败，错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False), res[1]))
            return {'result': False}


def check_port(kwargs):
    ip = kwargs['ip']
    service_port = kwargs['service_port']
    if service_port == 0:
        try:
            sshclient = PySsh(ip=kwargs['ip'], paswword=kwargs['password'], username='root')
        except Exception, e:
            logger.error('初始化%s ssh链接失败错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False), e.message))
            return {'result': False, 'error_mess': '创建ssh链接失败', 'data': kwargs}
        else:
            if sshclient.connect_status:
               res = sshclient.comm('ps -ef|grep %s|grep -v root' % kwargs['package_deploy_path'])
               if res[0]:
                   if len(res[1]) == 0:
                       return {'result': False}
                   else:
                       return {'result': True}
               else:
                   logger.error('%s查看进程失败，错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False), res[2]))
                   return {'result': False, 'error_mess': res[2]}

            else:
                return {'result': False, 'error_mess': '创建ssh链接失败', 'data': kwargs}
    else:
        try:
            obj = telnetlib.Telnet(host=ip, port=service_port, timeout=1)
        except Exception, e:
            logger.error('%s 检测服务端口失败，错误信息：%s' % (json.dumps(kwargs, ensure_ascii=False), json.dumps(e.args, ensure_ascii=False)))
            return {'result': False}
        else:
            obj.close()
            return {'result': True}


class CheckPortThtread(threading.Thread):

    def __init__(self, mkwargs, *args, **kwargs):
        self.__kwargs = mkwargs
        self.__result = None
        super(CheckPortThtread, self).__init__(*args, **kwargs)

    def run(self):
        try:
           res = check_port(self.__kwargs)
        except Exception, e:
            self.__result = {'result': False, 'error_mess': e.message}
        else:
            self.__result = res

    def get_result(self):
        return self.__result