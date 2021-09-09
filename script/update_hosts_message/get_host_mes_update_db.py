#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/3/11 10:56
    @FileName: get_host_mes_update_db.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, print_function
import django
import sys
import os
import logging
from django.db import Error
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Opsys.settings")
django.setup()
script_logger = logging.getLogger('scripts')
from devopsApp import models
from threading import Thread
from common.exec_shell_command.exec_comm import command
import re
import json
from threading import BoundedSemaphore


def get_host_mes():
    try:
        host_obj = models.Host.objects.filter().values_list('ip', 'os_version', 'hostname', 'net_card_mes', 'cpu_num',
                                                            'cpu_model', 'mem_total', 'disk_num', 'disk_mes',
                                                            'disk_total_volume')
    except Error, e:
        script_logger.error('查询数据库报错，错误信息：%s' %e.message)
        return False
    else:
        script_logger.info('获取hosts信息成功')
        return list(host_obj)


class MyThread(Thread):
    def __init__(self, ip, sem, *args, **kwargs):
        super(MyThread, self).__init__(*args, **kwargs)
        self._sem = sem
        self._ip = ip
        self.result = None

    def _get_os_version(self):
        os_version = command('ssh %s "cat /etc/redhat-release"' %self._ip)
        if os_version[0] is False:
            script_logger.error('获取%s os_version 失败：%s' %(self._ip, os_version[1]))
            return
        else:
            return os_version[1][0].strip()

    def _get_hostname(self):
        hostname = command('ssh %s "hostname"' %self._ip)
        if hostname[0] is False:
            script_logger.error('获取%s hostname失败：%s' %(self._ip, hostname[1]))
            return
        else:
            return hostname[1][0]

    def _get_net_card_mes(self):
        net_mes = command('ssh %s "ifconfig"' %self._ip)
        if net_mes[0] is False:
            script_logger.error('获取%s 网卡信息失败：%s' %(self._ip, net_mes[1]))
            return
        else:
            ifconfig_mes = net_mes[1][0]
            net = re.findall(r'(.*): flags.*', ifconfig_mes)
            ip = re.findall(r'inet (.*)  netmask', ifconfig_mes)
            net_card = zip(net, ip)
            net_card_mes = ''
            for item in net_card:
                net_card_mes = net_card_mes + item[0].strip() + ':' + item[1].strip() + ','
            else:
                return net_card_mes

    def _get_cpu_mes(self):
        cpu_mes = command('ssh %s "cat /proc/cpuinfo"' %self._ip)
        if cpu_mes[0] is False:
            script_logger.error('获取%s cpu信息失败：%s' %(self._ip, cpu_mes[1]))
            return None, None
        else:
            cpu_mes_str = cpu_mes[1][0]
            cpu_num = len(re.findall(r'processor', cpu_mes_str))
            cpu_model = re.search(r'model name.*:.*', cpu_mes_str).group().split('\t')[1].strip(':').strip()
            return cpu_num, cpu_model

    def _get_mem_total(self):
        mem_mes = command('ssh %s "cat /proc/meminfo"' %self._ip)
        if mem_mes[0] is False:
            script_logger.error('获取%s mem信息失败：%s' %(self._ip, mem_mes[1]))
            return
        else:
            mem_mes_str = mem_mes[1][0]
            mem_total = int(re.findall(r'MemTotal:\s+(\d+) kB', mem_mes_str)[0]) * 1024
            return mem_total

    def _get_disk_mes(self):
        disk_mes_obj = command('ssh %s "fdisk -l"' %self._ip)
        if disk_mes_obj[0] is False:
            script_logger.error('获取%s disk信息失败：%s' %(self._ip, disk_mes_obj[1]))
            return None, None, None
        else:
            disk_mes_str = disk_mes_obj[1][0]
            disk_mes_list = re.findall(r'/dev/(.*d.?):.*, (.*) bytes', disk_mes_str)
            disk_num = len(disk_mes_list)
            disk_mes = ''
            disk_total_volume = 0
            for item in disk_mes_list:
                disk_total_volume = disk_total_volume + int(item[1])
                disk_mes = disk_mes + item[0] + ':' + str(int(item[1])/1024/1024/1024) + 'GB' + ','
            else:
                return disk_num, disk_mes, disk_total_volume

    def run(self):
        os_version = self._get_os_version()
        hostname = self._get_hostname()
        net_card_mes = self._get_net_card_mes()
        cpu_num, cpu_model = self._get_cpu_mes()
        mem_total = self._get_mem_total()
        disk_num, disk_mes, disk_total_volume = self._get_disk_mes()
        result = (self._ip, os_version.strip(), hostname.strip(), net_card_mes.strip().strip(','), cpu_num,
                  cpu_model.strip(), mem_total, disk_num, disk_mes.strip().strip(','), disk_total_volume)
        if not result.count(None):
            self.result = result
        self._sem.release()

    @property
    def get_result(self):
        return self.result


if __name__ == '__main__':
    host_mes = get_host_mes()
    if host_mes is False:
        sys.exit()
    sem = BoundedSemaphore(10)
    res_t = []
    for item in host_mes:
        sem.acquire()
        t = MyThread(item[0], sem)
        t.start()
        res_t.append(t)
    res_list = []
    for item in res_t:
        if item.is_alive():
            item.join()
        res = item.get_result
        if res:
            res_list.append(res)

    need_update = set(res_list) - set(host_mes)
    # 更新变化过得主机信息
    for item in need_update:
        try:
            models.Host.objects.filter(ip=item[0]).update(os_version=item[1], hostname=item[2], net_card_mes=item[3],
                                                      cpu_num=item[4], cpu_model=item[5], mem_total=item[6],
                                                      disk_num=item[7], disk_mes=item[8], disk_total_volume=item[9]
                                                      )
        except Error, e:
            script_logger.error('更新host %s信息失败错误信息：%s' %(json.dumps(item), e.message))
        else:
            script_logger.info('更新host %s信息成功' %json.dumps(item))
