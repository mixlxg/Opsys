#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/3/11 14:28
    @FileName: exec_comm.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
import subprocess
import time


def command(comm, timeout=30):
    try:
        result_obj = subprocess.Popen(comm, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    except Exception, e:
        return False, e.message

    for item in range(int(timeout/0.5)):
        if result_obj.poll() is None:
            time.sleep(0.5)
        else:
            return True, result_obj.communicate(), result_obj.returncode
    else:
        return True, result_obj.communicate(), result_obj.returncode
