#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/9/4 14:25
    @FileName: Mjenkins.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
import jenkins
import logging
logger = logging.getLogger('django.request')

jenkins_user_dict = {
    'url': 'http://10.201.255.79/wxci_new/',
    'username': 'admin',
    'password': '8HqzQRJUDqvWwyGDYXFYPVrW7xGEFvNE'
}

# 创建jenkins 操作对象
try:
    Mjenkins = jenkins.Jenkins(**jenkins_user_dict)
except jenkins.JenkinsException, e:
    logger.error('创建jenkins链接失败错误信息：%s' %e.message)