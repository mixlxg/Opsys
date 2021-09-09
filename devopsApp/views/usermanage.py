#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/2/12 10:47
    @FileName: usermanage.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
from django.shortcuts import render, redirect, reverse
from django.views.generic import View
from django.http import HttpResponse
import json
import logging
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from common.PermissonDecorator import permission_controller
from common.Page_split import Page
from devopsApp import models
from django.db import Error
logger = logging.getLogger('django.request')


class Login(View):
    def dispatch(self, request, *args, **kwargs):
        self.__next = request.GET.get('next') or '/Opsys/Opsys/index/'
        return super(Login, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(self.__next)
        else:
            return render(request, 'login.html')

    def post(self, request):
        user = request.POST.get('username')
        password = request.POST.get('password')
        if user and password:
            login_user = auth.authenticate(username=user, password=password)
            if login_user is None:
                return HttpResponse(json.dumps({'result': False, 'mess': '用户名或者密码错误'}))
            else:
                auth.login(request, login_user)
                logger.info('%s 用户登录成功' %user)
                return HttpResponse(json.dumps({'result': True, 'next': self.__next}))
        else:
            return HttpResponse(json.dumps({'result': False, 'mess': '用户名密码不能为空'}))


@method_decorator(login_required, 'dispatch')
class Logout(View):
    def dispatch(self, request, *args, **kwargs):
        return super(Logout, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        auth.logout(request)
        return redirect(reverse('Opsys:login'))


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class UserManagement(View):
    def dispatch(self, request, *args, **kwargs):
        return super(UserManagement, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        try:
            user_obj = models.MyUser.objects.all().values('last_login', 'is_superuser', 'username', 'email', 'is_active'
                                                          , 'date_joined', 'role__name', 'first_name')
        except Error, e:
            logger.error("查询用户表失败，错误信息：%s"  %e.args[1])
            return render(request, 'userManagement.html', {'error_mes': '查询数据库失败%s' %e.args})
        current_page = request.GET.get('page', 1)
        page_obj = Page(reverse('Opsys:usermanagement'), user_obj.count(), current_page)
        return render(request, 'userManagement.html', {'error_mes': False, 'data': user_obj[page_obj.start:page_obj.end], 'page_str': page_obj.page_html()})


@method_decorator(login_required, 'dispatch')
class UserRegister(View):
    def dispatch(self, request, *args, **kwargs):
        return super(UserRegister, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        try:
            role_obj = models.Role.objects.all()
        except Error, e:
            logger.error('查询数据库role表失败，错误信息：%s' %e.args[1])
            render(request, 'base_error.html', {'error_mess': e.args})
        else:
            return render(request, 'userManagement_reg.html', {'data': role_obj})

    def post(self, request):
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            role = request.POST.get('role')
            first_name = request.POST.get('aliasname')
        except Exception, e:
            result = {'result': False, 'error_mess': e.message}
            logger.error('获取注册提交Post 信息失败：%s' %e.message)
        else:
            if username and email and password and first_name:
                try:
                    user_obj = models.MyUser.objects.filter(username=username)
                except Error, e:
                    logger.error('注册失败：%s' %e.args[1])
                    result = {'result': False, 'error_mess': e.args}
                else:
                    if user_obj.exists():
                        result = {'result': False, 'error_mess': '用户已存在'}
                    else:
                        try:
                            models.MyUser.objects.create_user(username=username, email=email, password=password, role_id=role[0], first_name=first_name)
                        except Error, e:
                            result = {'result': False, 'error_mess': '注册失败：%s' %e.args}
                            logger.error('注册失败：%s' %e.args[1])
                        else:
                            result = {'result': True}
            else:
                result = {'result': False, 'error_mess': '用户名或邮箱或密码或别名不能为空'}

        finally:
            return HttpResponse(json.dumps(result))


@method_decorator(login_required, 'dispatch')
class UserModify(View):
    def dispatch(self, request, *args, **kwargs):
        return super(UserModify, self).dispatch(request, * args, **kwargs)

    def get(self, request):
        try:
            user_obj = models.MyUser.objects.all().values('is_superuser', 'username', 'email', 'is_active','role__name','first_name')
        except Error, e:
            logger.error('查询用户数据报错，错误信息：%s' %e.args[1])
            return render(request, 'base_error.html', {'error_mes': e.args})
        else:
            current_page = request.GET.get('page', 1)
            page_obj = Page(reverse('Opsys:userModify'), user_obj.count(), current_page, per_page_num=10)
            return render(request, 'userManagement_modify.html', {'error_mes': False, 'data': user_obj[page_obj.start:page_obj.end], 'page_str': page_obj.page_html() })

    def post(self, request):
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            is_superuser = request.POST.get('radio_is_superuser')
            is_active = request.POST.get('radio_is_active')
            role = request.POST.get('role')
            first_name = request.POST.get('aliasname')
        except Exception, e:
            res = {'result': False, 'error_mess':e.message}
            logger.error('获取post请求内容失败：%s' %e.message)
        else:
            try:
                role_id = models.Role.objects.get(name=role).id
                models.MyUser.objects.filter(username=username).update(is_superuser=is_superuser, email=email,
                                                                       is_active=is_active, role_id=role_id,first_name=first_name)
            except Exception, e:
                res = {'result': False, 'error_mess': e.message}
                logger.error('更新数据库失败：%s' %e.message)
            else:
                if password == '':
                    res = {'result':True}
                else:
                    try:
                        user_obj=models.MyUser.objects.get(username=username)
                        user_obj.set_password(password)
                        user_obj.save()
                    except Error, e:
                        logger.error('修改密码失败：%s' %e.args[1])
                        res = {'result': False, 'error_mess': '修改密码失败'}
                    else:
                        res = {'result': True}
        finally:
            return HttpResponse(json.dumps(res))


@method_decorator(login_required, 'dispatch')
class DeleteUser(View):
    def dispatch(self, request, *args, **kwargs):
        return super(DeleteUser, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        try:
            username = self.request.POST.get('username')
        except Exception, e:
            logger.error('POST的username有问题，错误信息：%s' %e.message)
            res = {'result': False, 'error_mess':e.message}
        else:
            try:
                models.MyUser.objects.filter(username=username).delete()
            except Error, e:
                logger.error("删除用户%s失败，错误信息：%s" %(username, e.args[1]))
                res = {'result': False, 'error_mess': e.args}
            else:
                res = {'result': True}
        finally:
            return HttpResponse(json.dumps(res))


@method_decorator(login_required, 'dispatch')
class RoleQuery(View):
    """
        查询角色，用户返回{role:[user1,user2]}
    """
    def dispatch(self, request, *args, **kwargs):
        return super(RoleQuery, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        try:
            role_obj = models.Role.objects.all().values('name', 'myuser__username','myuser__first_name', 'myuser__email', 'myuser__is_superuser', 'myuser__is_active' )
        except Error, e:
            logger.error("查询角色信息失败")
            return HttpResponse(json.dumps({'result':False, 'error_mess': e.args}))
            #return render(request, 'userManagement_modify.html', {'error_mes': '查询数据库失败%s' %e.message})
        else:
            tmp_role_user = {}
            for item in role_obj:
                if item['myuser__is_superuser'] == 1:
                    is_superuser = '是'
                else:
                    is_superuser = '否'
                if item['myuser__is_active'] == 1:
                    is_active = '否'
                else:
                    is_active = '是'
                if item['name'] in tmp_role_user.keys():
                    if item['myuser__username'] is not None:
                        tmp_role_user[item['name']].append(
                            {'username': item['myuser__username'],'email': item['myuser__email'], 'is_superuser': is_superuser,
                             'is_active': is_active, 'role_name': item['name'],'first_name':item['myuser__first_name']}
                        )
                else:
                    if item['myuser__username'] is None:
                        tmp_role_user[item['name']] = []
                    else:
                        tmp_role_user[item['name']] = [{'username': item['myuser__username'], 'email': item['myuser__email'], 'is_superuser': is_superuser,
                             'is_active': is_active, 'role_name': item['name'],'first_name':item['myuser__first_name']}]
            else:
                return HttpResponse(json.dumps(tmp_role_user))


@method_decorator(login_required, 'dispatch')
class RoleDelete(View):
    def dispatch(self, request, *args, **kwargs):
        return super(RoleDelete,self).dispatch(request, *args, **kwargs)

    def post(self, request):
        try:
            name = self.request.POST.get('name')
        except Exception, e:
            logger.error('获取role 名失败：%s' %e.message)
            return render(request, 'base_error.html', {'error_mess': e.message})
        # 成功获取到role name 校验是否还有用户在这个role 下
        try:
            role_obj = models.Role.objects.filter(name=name)
            user_obj = models.MyUser.objects.filter(role__name=name)
            if user_obj.exists():
                username_list = []
                for item in user_obj:
                    username_list.append(item.username)
                return HttpResponse(json.dumps({'result': False, 'data': username_list}))
            else:
                role_obj.delete()
                return HttpResponse(json.dumps({'result': True}))
        except Error, e:
            logger.error('删除 role 失败：%s' %e.args[1])
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            #return render(request, 'base_error.html', {'error_mess': e.message})


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class UserManagementRole(View):
    def dispatch(self, request, *args, **kwargs):
        return super(UserManagementRole, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        try:
            data_obj = models.Role.objects.all().values('id','name')
        except Error, e:
            logger.error("查询角色表失败失败信息：%s" %e.args[1])
            return render(request, "base_error.html", {'error_mess': e.args})
        else:
            current_page = request.GET.get('page', 1)
            page_obj = Page(reverse('Opsys:usermanagementRole'), data_obj.count(), current_page)
            return render(request, 'userManagement_role.html', {'data': data_obj[page_obj.start:page_obj.end], 'page_str': page_obj.page_html()})

    def post(self, request):
        try:
            role_name = request.POST.get('role_name')
            if models.Role.objects.filter(name=role_name).exists():
                res = {'result': False, 'error_mess': '角色已存在'}
            else:
                try:
                    models.Role.objects.create(name=role_name)
                except Error, e:
                    logger.info('插入role 角色失败：%s' %e.args[1])
                    return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                    #return render(request, 'base_error.html', {'error_mess': e.message})
                else:
                    res = {'result': True}
        except Exception, e:
            logger.error('添加角色失败：%s' %e.message)
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.message}))
            #return render(request, 'base_error.html', {'error_mess': '添加角色失败，错误信息：%s' %e.message})
        else:
            return HttpResponse(json.dumps(res))


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class UserManagementPermissions(View):
    def dispatch(self, request, *args, **kwargs):
        return super(UserManagementPermissions, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'userManagement_permissions.html')


@method_decorator(login_required, 'dispatch')
class Permissions(View):
    def dispatch(self, request, *args, **kwargs):
        return super(Permissions, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        role_name = request.GET.get('role_name', False)
        if role_name:
            if role_name == 'admin':
                try:
                    permission_obj = models.Permissions.objects.all()
                except Error, e:
                    logger.error('查询用户权限失败：%s' %e.args[1])
                    return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                    #return render(request, 'base_error.html', {'error_mess': e.message})
            else:
                try:
                    permission_obj = models.Permissions.objects.filter(role__name=role_name)
                except Error, e:
                    logger.error('查询用户权限失败：%s' %e.args[1])
                    return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                    #return render(request, 'base_error.html', {'error_mess': e.message})

            result = []
            i = 1
            for item in permission_obj:
                result.append(
                    {'id': i, 'url': item.url}
                )
                i += 1
            else:
                return HttpResponse(json.dumps(result))
        else:
            try:
                result = []
                i = 1
                permission_obj = models.Permissions.objects.all()
                for item in permission_obj:
                    result.append(
                        {'id': i, 'url': item.url}
                    )
                    i += 1
            except Error, e:
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                #return render(request, 'base_error.html', {'error_mess': e.meesage})
            else:
                return HttpResponse(json.dumps(result))

    def post(self, request):
        try:
            url = request.POST.get('url')
            models.Permissions.objects.filter(url=url).delete()
        except Error, e:
            logger.error("删除权限%s 失败，错误信息：%s" %(url, e.args[1]))
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            #return render(request, 'base_error.html', {'error_mess': e.message})
        else:
            return HttpResponse(json.dumps({'result': True}))


@method_decorator(login_required, 'dispatch')
class UserGrants(View):
    def dispatch(self, request, *args, **kwargs):
        return super(UserGrants, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        try:
            username = request.POST.get('username')
            role_name = request.POST.get('rolename')
        except Exception, e:
            logger.error('获取post 数据失败：%s' %e.message)
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.message}))
            #return render(request, 'base_error.html', {'error_mess':e.message})

        try:
            role_id=models.Role.objects.filter(name=role_name)[0].id
            models.MyUser.objects.filter(username=username).update(role_id=role_id)
        except Error, e:
            logger.error('更新数据库失败：%s' %e.args[1])
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            #return render(request, 'base_error.html', {'error_mess':e.message})
        else:
            return HttpResponse(json.dumps({'result': True}))


@method_decorator(login_required, 'dispatch')
class RoleGrants(View):
    def dispatch(self, request, *args, **kwargs):
        return super(RoleGrants,self).dispatch(request, *args, **kwargs)

    def get(self, request):
        try:
            role_name = request.GET.get('role_name')
        except Exception, e:
            logger.error('获取role_name失败：%s' %e.message)
            #return render(request, 'base_error.html', {'error_mess': e.message})
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.message}))
        try:
            has_p = models.Permissions.objects.filter(role__name=role_name).values_list('url')
            nhas_p = models.Permissions.objects.exclude(role__name=role_name).values_list('url')
        except Error, e:
            logger.error('查询权限失败：%s' %e.args[1])
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            #return render(request, 'base_error.html', {'error_mess':e.message})
        else:
            has_p_list=[item[0] for item in has_p]
            nhas_p_list=[item[0] for item in nhas_p]
            return HttpResponse(json.dumps({'result': True, 'has_p': has_p_list, 'nhas_p': nhas_p_list}))

    def post(self, request):
        try:
            url_list = request.POST.getlist('url')
            role_name = request.POST.get('role_name')
        except Exception,e:
            logger.error('获取POST数据失败：%s' %e.message)
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.message}))
            #return render(request, 'base_error.html', {'error_mess':e.message})
        else:
            if(url_list):
                try:
                    role_obj = models.Role.objects.get(name=role_name)
                    curl_list = [item[0] for item in role_obj.permissions.values_list('url')]
                    need_delete = set(curl_list) - set(url_list)
                    need_add = set(url_list) - set(curl_list)
                    print need_add
                    print need_delete
                    for item in need_delete:
                        role_obj.permissions.remove(models.Permissions.objects.get(url=item))
                    for item in need_add:
                        role_obj.permissions.add(models.Permissions.objects.get(url=item))
                except Error, e:
                    logger.error('role 授权失败：%s' %e.args[1])
                    return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                    #return render(request, 'base_error.html', {'error_mess': e.message})
                else:
                    return HttpResponse(json.dumps({'result': True}))
            else:
                try:
                    role_obj = models.Role.objects.get(name=role_name)
                    role_obj.permissions.clear()
                except Error, e:
                    logger.error('清理%s权限失败：%s' %(role_name, e.args[1]))
                    #return render(request, 'base_error.html', {'error_mess': e.message})
                    return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                else:
                    return HttpResponse(json.dumps({'result': True}))