#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/5/15 15:37
    @FileName: application_tasks.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, absolute_import
from ..celery import app
from ..lib.pyssh import PySsh
from celery.utils.log import get_task_logger
from celery.exceptions import SoftTimeLimitExceeded,TimeLimitExceeded
import json

logger = get_task_logger(__name__)
@app.task(bind=True, soft_time_limit=120,time_limit=150)
def create_new_application(self, kwargs):
    """
    :param self: task instance self
    :param kwargs: {"ip":xx,"username":username,"paswword":password,"port":port,"service_name","service_type":'springboot",jdk_version:jdk1.8}
    :return: { 'result':True/False}
    """
    ip = kwargs['ip']
    username = kwargs['username']
    password = kwargs['password']
    port = kwargs['port']
    service_name = kwargs['service_name']
    service_type = kwargs['service_type']
    jdk_version = kwargs['jdk_version']
    try:
        ssh = PySsh(ip=ip, username=username, paswword=password, port=port)
        if ssh.connect_status:
            logger.info('%s,ssh 连接成功' %json.dumps(kwargs, ensure_ascii=False))
            if service_type == 'springboot':
                # springboot 类型应用处理函数入口
                if springboot_service_init(ssh, service_name, jdk_version) is False:
                    return {'result': False, 'error_mess': '安装jdk或者创建相关的目录失败'}
            else:
                pass
        else:
            logger.error("使用%s用户连接服务器%s失败：%s" %(username, ip, ssh.error))
            return {'result': False, 'error_mess': ssh.error}
    except SoftTimeLimitExceeded, e:
        logger.error('任务执行超时')
        return {'result': False, 'error_mess': '任务执行超时'}
    except TimeLimitExceeded as e:
        logger.error('任务执行超时')
        return {'result': False, 'error_mess': '任务执行超时'}
    else:
        return {'result': True}
    finally:
        if ssh.connect_status:
            ssh.close()


def install_jdk18(ssh, env=False):
    ssh.comm('wget http://192.200.239.188:81/source/jdk-8u201-linux-x64.tar.gz -O /tmp/jdk-8u201-linux-x64.tar.gz && tar -zxf /tmp/jdk-8u201-linux-x64.tar.gz -C /opt/usr/',timeout=120)
    java_check_res = ssh.comm('[ -d "/opt/usr/jdk1.8.0_201" -o  -d "/opt/usr/jdk1.8" ] && echo 0 || echo 1')
    if java_check_res[0] is False or java_check_res[1][0] == '1':
        return False
    if env:
        ssh.comm('echo -e "\n\nJAVA_HOME=/opt/usr/jdk1.8.0_201\nCLASSPATH=.:\$JAVA_HOME/lib/tools.jar:\$JAVA_HOME/lib/dt.jar\nPATH=\$JAVA_HOME/bin:\$HOME/bin:\$HOME/.local/bin:\$PATH" >> /etc/profile')
    return True


def install_jdk(ssh, jdk_version):
    # 判断当前系统是否存在jdk，如果不存在配置jdk1.8版本，如果曾在根据jdk_version 来判断是否需要安装
    java_version = ssh.comm('java -version')
    logger.info(json.dumps(java_version, ensure_ascii=False))
    if java_version[0]:
        if jdk_version == 'jdk1.8':
            if java_version[2][0].__contains__('1.7'):
                java_check_res = ssh.comm('[ -d "/opt/usr/jdk1.8.0_201" -o -d "/opt/usr/jdk1.8" ] && echo 0 || echo 1')
                if java_check_res[0]:
                    if java_check_res[1][0].strip() == '1':
                        if install_jdk18(ssh) is False:
                            return False
                else:
                    return False
            elif java_version[2][0].__contains__('1.8'):
                java_check_res = ssh.comm('[ -d "/opt/usr/jdk1.8.0_201" -o -d "/opt/usr/jdk1.8" ] && echo 0 || echo 1')
                if java_check_res[0]:
                    if java_check_res[1][0].strip() == '1':
                        if install_jdk18(ssh, env=True) is False:
                            return False
                else:
                    return False
            else:
                if install_jdk18(ssh, env=True) is False:
                    return False
    else:
        return False


def springboot_service_init(ssh, service_name, jdk_version):
    """
    :param ssh: paramiko 的sshclient对象
    :param service_name: 应用名称
    :return:
    """
    #检测安装jdk
    if install_jdk(ssh, jdk_version) is False:
        return False
    # 安照规则创建springboot工程的工程目录
    mkdir_res = ssh.comm('mkdir -pv /webapp/%s/{bin,lib} && chown -R webapp.webapp /webapp/%s' %(service_name, service_name))
    logger.info(json.dumps(mkdir_res, ensure_ascii=False))
    if mkdir_res[0] is False:
        return False
    # 创建日志目录
    mkdir_bizlog_res = ssh.comm('mkdir -pv /bizlog/%s && chown -R webapp.webapp /bizlog/%s' %(service_name, service_name))
    logger.info(json.dumps(mkdir_bizlog_res, ensure_ascii=False))
    return mkdir_bizlog_res[0]