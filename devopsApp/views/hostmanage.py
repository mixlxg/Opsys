#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/4/8 14:08
    @FileName: hostmanage.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
import json
import logging
import time
import os
from django.conf import settings
from common import change_host_passwd
from devopsApp import models
from django.db import Error
from django.views.generic import View
from django.utils.decorators import method_decorator
from common.PermissonDecorator import permission_controller
from django.contrib.auth.decorators import login_required
from common.Page_split import Page
from django.shortcuts import render, redirect, reverse
from django.http import JsonResponse
from django.http import HttpResponse,FileResponse

logger = logging.getLogger('django.request')


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class HostManage(View):
    def dispatch(self, request, *args, **kwargs):
        self.role = models.Role.objects.get(myuser__username=request.user.username).name
        return super(HostManage, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        try:
            ip = request.GET.get('ip', False)
            page = request.GET.get('page', 1)
        except Exception, e:
            logger.error('获取GET数据失败：%s' %e.message)
            return render(request, 'base_error.html', {'error_mess': e.message})
        if ip is False or len(ip) == 0:
            host_obj = models.Host.objects.all()
        else:
            host_obj = models.Host.objects.filter(ip=ip)
        page_obj = Page(reverse('Opsys:HostManage'), host_obj.count(), page, per_page_num=15)
        return render(request, 'hostmanage.html', {'data': host_obj[page_obj.start:page_obj.end], 'role': self.role, 'page_str': page_obj.page_html()})

    def post(self, request):
        try:
            ip = request.POST.get('ip')
        except Exception, e:
            logger.error('获取POST数据失败：%s' %e.message)
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.message}))
        else:
            host_obj = models.Host.objects.filter(ip=ip).values()
            return HttpResponse(json.dumps({'hostdata': host_obj[0], 'role': self.role, 'result': True}))


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class HostManageM(View):
    def dispatch(self, request, *args, **kwargs):
        return super(HostManageM, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax() is False:
            return render(request, 'hostmanage_M.html')
        else:
            try:
                host_obj = models.Host.objects.all().values()
            except Error, e:
                logger.error('查询数据库报错，错误信息：%s' %e.args[1])
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args }))
            else:
                return HttpResponse(json.dumps({'result': True, 'data': list(host_obj)}))

    def post(self, request):
        action_type = request.POST.get('action_type')
        data = json.loads(request.POST.get('data'))
        exists_list = []
        if action_type == 'add':
            for item in data:
                print type(data)
                try:
                    if models.Host.objects.filter(ip=item['ip']).exists():
                        exists_list.append(item['ip'])
                        continue
                except Error, e:
                    logger.error('添加host失败：%s' %e.args[1])
                    return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                else:
                    try:
                        models.Host.objects.create(**item)
                    except Error, e:
                        logger.error('添加host失败:%s' %e.args[1])
                        return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            else:
                return HttpResponse(json.dumps({'result': True, 'exists_host': exists_list}))
        elif action_type == 'update':
            try:
                models.Host.objects.filter(ip=data['ip']).update(root_password=data['root_passwd'])
            except Error, e:
                logger.error('更新主机密码失败：%s' %e.args[1])
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            else:
                return HttpResponse(json.dumps({'result': True}))
        elif action_type == 'delete':
            try:
                service_obj = models.Service.objects.filter(host__ip=data['ip']).exclude(status='offline')
                if service_obj.exists():
                    service_name = service_obj.values_list('service_name')
                else:
                    models.Host.objects.filter(ip=data['ip']).delete()
            except Error,e:
                logger.error('查询主机表失败：%s' %e.args[1])
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            else:
                if 'service_name' in dir():
                    exists_service = [item[0] for item in service_name]
                    return HttpResponse(json.dumps({'result': True, 'exists_service': exists_service}))
                else:
                    return HttpResponse(json.dumps({'result': True, 'exists_service': []}))


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class HostChangePassword(View):
    def dispatch(self, request, *args, **kwargs):
        return super(HostChangePassword, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        filename = request.GET.get('filename')
        if filename:
            filename_path = os.path.join(settings.BASE_DIR, 'execl', 'host_password_file', '%s' % filename)
            fp = open(filename_path, 'rb')
            response = FileResponse(fp)
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="%s"' % filename
            return response
        else:
            return render(request, 'hostmanage-change-password.html')

    def post(self, request):
        username = request.POST.get('username')
        if username.__contains__('ALL'):
            modified_users = ['bizlog', 'webapp', 'root']
        else:
            modified_users = [username]
        try:
            filename, result = change_host_passwd.main(modified_users=modified_users)
            # filename = "2019-10-17.xls"
            # result = [['192.200.239.152','bizlog','asdf','success'],['192.200.239.153','bizlog','asdf','failed']]
        except Exception as e:
            logger.error("修改密码失败，错误信息：%s" %e.message)
            return JsonResponse({'result': False, 'error_mess': e.message})
        else:
            time.sleep(10)
            return JsonResponse({'result': True, 'filename': filename, 'data': result})

