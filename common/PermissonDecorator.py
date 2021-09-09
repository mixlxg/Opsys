#!/usr/bin/env python
# -coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/2/12 15:25
    @FileName: PermissonDecorator.py
    @Software: PyCharm
"""
from devopsApp.models import MyUser, Permissions
from django.db import Error
from django.shortcuts import render
import logging
logger = logging.getLogger('auth')


def permission_controller(func):
    def inner(request, *args, **kwargs):
        user = request.user.get_username()
        url = request.path if request.path.endswith('/') else request.path + '/'
        if not Permissions.objects.filter(url=url).exists():
            try:
                Permissions.objects.create(url=url)
            except Error, e:
                logger.error('权限认证时自动注册未注册的url %s失败，错误信息：%s' %(url, e.message))
        user_obj = MyUser.objects.get(username=user)
        if user_obj.role_id == 2 or user_obj.is_superuser ==1:
            return func(request, *args, **kwargs)
        res = user_obj.role.permissions.all()
        p_url = [item.url for item in res]
        if url in p_url:
            return func(request, *args, **kwargs)
        else:
            return render(request, 'permissions_denied.html')
    return inner
