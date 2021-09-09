#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/5/17 16:26
    @FileName: allocation_port.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, absolute_import
from .exec_shell_command.exec_comm import command
from devopsApp.models import Service
from django.db import Error
import logging

logger = logging.getLogger('django.request')

def allocate_port(ip):
    """
    :param ip: ip如果是字符串必须以，风格，也可以是列表
    :return: 返回处理结果元祖（True,port)
    """
    # 处理ip 如果是字符串转换为list
    # if isinstance(ip, str):
    ip = ip.split(',')
    tmp = []
    # 查询数据库里面已经分配的端口
    try:
        port_obj = Service.objects.filter(host__ip__in=ip).values_list('service_port')
    except Error, e:
        return False, e.args[1]
    else:
        tmp.extend([int(item[0]) for item in port_obj])
    for item in ip:
        try:
           res = command(r'''ssh %s "netstat -anlupt|grep -i listen|awk '{print \$4}'|awk -F':' '{print \$NF}'" ''' %ip)
        except Exception, e:
            return False, e.message

        if res[0]:
            pid_num = [int(item.strip()) for item in res[1][0].strip().split('\n') if len(item) != 0]
            tmp.extend(pid_num)
        else:
            return False, res[1]
    else:
        # 去重将tmp转化为set类型
        tmp = list(set(tmp))
        # 过滤小8080的数据
        tmp = filter(lambda x: x > 8080, tmp)
        tmp.sort()
        port = 8081
        while True:
            if port in tmp:
                port = port+1
                continue
            else:
                return True, port