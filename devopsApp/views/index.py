#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/2/13 13:54
    @FileName: index.py
    @Software: PyCharm
"""
from  __future__ import unicode_literals
from django.http import HttpResponse
from  django.shortcuts import render
from common.PermissonDecorator import permission_controller
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class Index(View):
    def dispatch(self, request, *args, **kwargs):
        return super(Index, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'base.html')


def error(request):
    if request.method == 'GET':
        error_mess = request.GET.get('error_mess')
        return render(request, 'base_error.html', {'error_mess': error_mess})


@method_decorator(login_required, 'dispatch')
class Test(View):
    def dispatch(self, request, *args, **kwargs):
        return super(Test, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'base_test.html')
