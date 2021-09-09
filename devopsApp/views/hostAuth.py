#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2020/3/12 11:07 
# @Author : 吕秀刚
# @File : hostAuth.py

from __future__ import unicode_literals
import logging
import json
import time
import datetime
from devopsApp import models
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.utils.decorators import method_decorator
from common.PermissonDecorator import permission_controller
from django.contrib.auth.decorators import login_required
from django_redis import get_redis_connection
from django.db import Error
from common.time_format import s_to_dhms
from common.k8s_yaml_parse import K8sYamlParse
# 初始化一个认知logger
logger = logging.getLogger('django.request')


# 定义一个堡垒机刷权限接口
@method_decorator(login_required, 'dispatch')
class HostPowerApi(View):
    def dispatch(self, request, *args, **kwargs):
        return super(HostPowerApi, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        """
        :return: 字典格式
        {username:{"项目名称":{应用名称:{ip:[],start_time:}}}}
        """
        # get 接受一个参数 flag 如果flag 为 one 两种情况，如果为admin角色返回所有的admin可查看的权限，如果为普通用户则查看当前用户所拥有的所有权限
        # flag 为all时 查看所有用户的分配的权限 一般是给管理查看已经授权的情况的
        flag = request.GET.get('flag')
        username = request.user.get_full_name()
        # 获取role 角色对象，用于判断角色是否为admin角色
        try:
            role_obj = models.MyUser.objects.filter(first_name=username, role__name='admin')
        except Error as e:
            logger.error('查询数据库判断用户是否有admin角色失败，错误信息：%s' % json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        # 判断flag 是否为None，当flag为None说明接口没有传参数，返回错误
        if flag is None:
            return JsonResponse({'result': False, 'error_mess': '请传递flag参数'})
        # 初始化一个redis链接
        redis_conn = get_redis_connection()
        # 开始判断角色是否为admin角色
        if role_obj.exists():
            # 为admin角色可以查看所有权限
            # 判断flag 为one还是all 如果one是查看admin角色用户拥有的权限，为all查看所有普通用户的权限
            if flag == 'one':
                admin_p = redis_conn.get('admin_permission')
                if admin_p is None:
                    return JsonResponse({'result': False, 'error_mess': '获取redis权限数据为空,可能数据已经过期'})
                else:
                    tmp = json.loads(admin_p)
                    return JsonResponse({'result': True, 'data': {username: tmp}})
            else:
                # 查询所有的数据普通用户返回授权数据
                all_p = redis_conn.keys('*_permission:*')
                # 定义一个临时dict 用于存放返回数据
                tmp = {}
                for one_k in all_p:
                    one_p_v = json.loads(redis_conn.get(one_k))
                    ttl = redis_conn.ttl(one_k)
                    k_username = one_k.split('_')[0].strip()
                    # 给取出来的one_p_v 添加时间标签
                    for project_k, project_v in one_p_v.items():
                        for service_k, service_v in one_p_v[project_k].items():
                            if 'namespace' in service_v.keys():
                                one_p_v[project_k][service_k] = {'long_time': s_to_dhms(ttl), 'ip': None}
                            else:
                                one_p_v[project_k][service_k] = {'long_time': s_to_dhms(ttl), 'ip': service_v['ip']}
                    # 生成最终结果
                    if k_username in tmp.keys():
                        for p_k, p_v in one_p_v.items():
                            if p_k in tmp[k_username].keys():
                                for s_k, s_v in p_v.items():
                                    tmp[k_username][p_k][s_k] = s_v
                            else:
                                tmp[k_username][p_k] = p_v
                    else:
                        tmp[k_username] = one_p_v
                return JsonResponse({'result': True, 'data': tmp})
        else:
            # 普通角色，获取自己的所有权限
            username_key = '%s_permission:*' % username
            all_p = redis_conn.keys(username_key)
            # 定义临时字典用于存放结果数据
            tmp = {}
            for one_k in all_p:
                one_p_v = json.loads(redis_conn.get(one_k))
                ttl = redis_conn.ttl(one_k)
                # 给取出来的one_p_v 添加时间标签
                for project_k, project_v in one_p_v.items():
                    for service_k, service_v in one_p_v[project_k].items():
                        if 'namespace' in service_v.keys():
                            one_p_v[project_k][service_k] = {'long_time': s_to_dhms(ttl), 'ip': None}
                        else:
                            one_p_v[project_k][service_k] = {'long_time': s_to_dhms(ttl), 'ip': service_v['ip']}
                        # 生成最终结果
                if username in tmp.keys():
                    for p_k, p_v in one_p_v.items():
                        if p_k in tmp[username].keys():
                            for s_k, s_v in p_v.items():
                                tmp[username][p_k][s_k] = s_v
                        else:
                            tmp[username][p_k] = p_v
                else:
                    tmp[username] = one_p_v

            return JsonResponse({'result': True, 'data': tmp})

    def post(self, request):
        """
        :return: 返回json {"result":True|False}
        """
        # data json: keys 一个是 username：用户名，service_name：list service名字，flag可选， start_time 时间格式，end_time 时间格式
        post_data = request.POST.get('data')
        if post_data is None:
            return JsonResponse({'result': False, 'error_mess': '传参数不能为空'})
        # 反序列化
        post_data = json.loads(post_data)
        username = post_data.get('username')
        flag = post_data.get('flag')
        service_name_list = post_data.get('service_name_list')
        # 获取一个redis 链接
        redis_conn = get_redis_connection()
        # 生成一个时间戳用于开始时间
        start_timestamp = time.mktime(time.localtime())
        # 大数据列表
        big_data_ip = ['192.200.251.51', '192.200.251.52', '192.200.251.53', '192.200.251.54', '192.200.251.55', '192.200.251.56', '192.200.251.57',
                       '192.200.251.58', '192.200.251.59', '192.200.251.60', '192.200.251.61', '192.200.251.62', '192.200.251.63', '192.200.251.64',
                       '192.200.251.65', '192.200.251.73', '192.200.251.74', '192.200.251.75', '192.200.251.81', '192.200.251.82', '192.200.251.83',
                       '192.200.251.84', '192.200.251.85', '192.200.251.86', '192.200.251.87', '192.200.251.88', '192.200.251.89', '192.200.251.90',
                       '192.200.251.91', '192.200.251.92', '192.200.251.93', '192.200.251.94', '192.200.251.95', '192.200.251.96', '192.200.251.97', '192.200.251.98',
                       '192.200.251.99', '192.200.251.100', '192.200.251.80']
        jemter_ip = ['192.200.251.45', '192.200.251.46', '192.200.251.47']
        special_flag = post_data.get('special_flag')
        if special_flag is not None and special_flag == 'bigdata':
            p_key = '%s_permission:bigdata' % username
            tmp_bigdata_dict = {'特殊权限': {'大数据主机': {'ip': big_data_ip, 'start_time': start_timestamp}}}
            redis_conn.set(p_key, json.dumps(tmp_bigdata_dict))
            return JsonResponse({'result': True})
        # 判断如果flag为None表示是普通用户刷权限，根据service_name_list里面的内容授权
        # 如果flag 不为None表示为admin角色用户刷全部权限
        if flag is not None:
            # 需要刷所有的可配置的权限到redis里面
            # 定义一个临时字典
            admin_permission_dict = {}
            # 获取应用的全部权限
            try:
                s_obj = models.Service.objects.exclude(status='offline')
                for s_item in s_obj:
                    project_name = s_item.project_name.project_name
                    service_name = s_item.service_name
                    ip_list = [item[0] for item in s_item.host.values_list('ip')]
                    if project_name in admin_permission_dict.keys():
                        admin_permission_dict[project_name][service_name] = {'ip': ip_list, 'start_time': start_timestamp}
                    else:
                        admin_permission_dict[project_name] = {service_name: {'ip': ip_list, 'start_time': start_timestamp}}
            except Error as e:
                logger.error('查询数据失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 获取k8s项目的所有权限
            try:
                k8s_obj = models.K8sApp.objects.exclude(status='offline')
                for k8s_item in k8s_obj:
                    project_name = k8s_item.project_name.project_name
                    service_name = k8s_item.service_name
                    yaml_name = k8s_item.deploy_yaml
                    if yaml_name == '':
                        continue
                    yaml_obj = K8sYamlParse(yaml_name)
                    ok, yaml_data = yaml_obj.parse()
                    if ok:
                        namespace = yaml_data[0]['metadata']['namespace']
                        pod_label = yaml_data[0]['spec']['template']['metadata']['labels']['k8s-app']
                        label_selector = 'k8s-app=%s' % pod_label
                        if project_name in admin_permission_dict.keys():
                            admin_permission_dict[project_name][service_name]={
                                'start_time': start_timestamp,
                                'namespace': namespace,
                                'label_selector': label_selector
                            }
                        else:
                            admin_permission_dict[project_name]={service_name:{
                                'start_time': start_timestamp,
                                'namespace': namespace,
                                'label_selector': label_selector
                            }}
                    else:
                        logger.error("解析yaml文件%s失败，错误信息：%s" %(yaml_name, yaml_data))
                        return JsonResponse({'result': False, 'error_mess': yaml_data})
            except Exception as e:
                logger.error('处理k8sl类型应用失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.message})
            # 获取redis信息：
            try:
                redis_obj = models.Redis.objects.filter()
                for redis_item in redis_obj:
                    redis_name = redis_item.clustername
                    redis_ip = [item.strip().split(':')[0]for item in redis_item.ipaddr.strip().split(',')]
                    if 'redis集群' in admin_permission_dict.keys():
                        admin_permission_dict['redis集群'][redis_name] = {'ip': redis_ip, 'start_time': start_timestamp}
                    else:
                        admin_permission_dict['redis集群'] = {redis_name: {'ip': redis_ip, 'start_time': start_timestamp}}
            except Error as e:
                logger.error('查询redis信息数据失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 获取 zk 信息
            try:
                zk_obj = models.ZookeeperList.objects.filter()
                for zk_item in zk_obj:
                    zk_name = zk_item.clustername
                    zk_ip = [item.strip().split(':')[0] for item in zk_item.ip.strip().split(',')]
                    if 'zk集群' in admin_permission_dict.keys():
                        admin_permission_dict['zk集群'][zk_name] = {'ip': zk_ip, 'start_time': start_timestamp}
                    else:
                        admin_permission_dict['zk集群'] = {zk_name: {'ip': zk_ip, 'start_time': start_timestamp}}
            except Error as e:
                logger.error('从数据库获取zk信息失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 获取kafka 信息
            try:
                kafka_obj = models.KafkaList.objects.filter()
                for k_item in kafka_obj:
                    kafka_name = k_item.clustername
                    k_ip = [item.strip().split(':')[0] for item in k_item.ip.strip().split(',')]
                    if 'kafka集群' in admin_permission_dict.keys():
                        admin_permission_dict['kafka集群'][kafka_name] = {'ip': k_ip, 'start_time': start_timestamp}
                    else:
                        admin_permission_dict['kafka集群'] = {kafka_name: {'ip': k_ip, 'start_time': start_timestamp}}
            except Error as e:
                logger.error('从数据库查询kafka信息失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            admin_permission_dict['特殊权限']={}
            # 手动添加大数据主机信息
            admin_permission_dict['特殊权限']['大数据主机'] = {'ip': big_data_ip, 'start_time': start_timestamp}
            # 手动添加jemeter主机信息
            admin_permission_dict['特殊权限']['jemter'] = {'ip': jemter_ip, 'start_time': start_timestamp}
            # 将数据刷入到redis里面
            try:
                redis_conn.set('admin_permission', json.dumps(admin_permission_dict))
            except Exception as e:
                logger.error('插入权限数据到redis失败，错误信息：%s'  % e.message)
                return JsonResponse({'result': False, 'error_mess': e.message})
            else:
                return JsonResponse({'result': True})
        else:
            if service_name_list is None:
                return JsonResponse({'result': False, 'error_mess': '服务列表名不能为空，亲传正确参数'})
            # 将开始时间格式和结束时间格式转换给时间戳格式
            start_time = post_data['start_time']
            end_time = post_data['end_time']
            # 将start_time 和 end_time 转换为时间戳格式
            start_time = time.mktime(time.strptime(start_time, '%Y-%m-%d %H:%M:%S'))
            end_time = time.mktime(time.strptime(end_time, '%Y-%m-%d %H:%M:%S'))
            now_time = time.mktime(time.localtime())
            if end_time - now_time > 0:
                long_time = int(end_time - now_time)
            else:
                long_time = int(end_time - start_time)
            if long_time < 0:
                return JsonResponse({'result': False, 'error_mess': '申请权限的结束时间早于开始时间请重新申请'})
            # 如果long_time 大于7天 则最多按照七天时间算
            if long_time >= 30*24*60*60:
                long_time = 30*24*60*60
            # 循环列表格式刷入数据到redis里面
            for service_name in service_name_list:
                if service_name == 'uip-out':
                    # 当uip-out 是查询的是uip_out 和uip2_out
                    try:
                        s_obj = models.Service.objects.filter(service_name__in=['uip_out', 'uip2_out'])
                        for s_item in s_obj:
                            service_name_tmp = s_item.service_name
                            project_name = s_item.project_name.project_name
                            ip_list = [item[0] for item in s_item.host.values_list('ip')]
                            # 临时数据变量，用于存放输入redis格式
                            tmp = {project_name: {service_name_tmp: {'ip': ip_list, 'start_time': start_time}}}
                            try:
                                p_key = '%s_permission:%s' % (username, service_name_tmp)
                                if redis_conn.ttl(p_key) < long_time:
                                    redis_conn.set(p_key, json.dumps(tmp), ex=long_time)
                            except Exception as e:
                                logger.error("输入redis数据%s失败，错误信息：%s" % (json.dumps(tmp), e.message))
                                return JsonResponse({'result': False, 'error_mess': e.message})
                    except Error as e:
                        logger.error('查询数据失败，错误信息：%s' % json.dumps(e.args))
                        return JsonResponse({'result': False, 'error_mess': e.args})
                elif service_name == 'octopus-event-wechat':
                    # 当octopus-event-wechat 时，查询是的octopus-event-wechat 和octopus-event2-wechat
                    try:
                        s_obj = models.Service.objects.filter(service_name__in=['octopus-event-wechat', 'octopus-event2-wechat'])
                        for s_item in s_obj:
                            service_name_tmp = s_item.service_name.strip()
                            project_name = s_item.project_name.project_name
                            ip_list = [item[0] for item in s_item.host.values_list('ip')]
                            # 临时数据变量，用于存放输入redis格式
                            tmp = {project_name: {service_name_tmp: {'ip': ip_list, 'start_time': start_time}}}
                            try:
                                p_key = '%s_permission:%s' % (username, service_name_tmp)
                                if redis_conn.ttl(p_key) < long_time:
                                    redis_conn.set(p_key, json.dumps(tmp), ex=long_time)
                            except Exception as e:
                                logger.error("输入redis数据:%s失败，错误信息：%s" % (json.dumps(tmp), e.message))
                                return JsonResponse({'result': False, 'error_mess': e.message})
                    except Error as e:
                        logger.error('查询数据库失败，错误信息：%s' % json.dumps(e.args))
                        return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    # 开始获取数据并刷入到redis
                    try:
                        service_obj = models.Service.objects.get(service_name=service_name)
                        project_name = service_obj.project_name.project_name
                        ip_list = [item[0] for item in service_obj.host.values_list('ip')]
                        tmp = {project_name: {service_name: {'ip': ip_list, 'start_time': start_time}}}
                        p_key = '%s_permission:%s' % (username, service_name)
                        # 刷入数据到redis
                        try:
                            if redis_conn.ttl(p_key) < long_time:
                                redis_conn.set(p_key, json.dumps(tmp), ex=long_time)
                        except Exception as e:
                            logger.error('输入数据%s到redis报错，错误信息：%s' % (json.dumps(tmp), e.message))
                            return JsonResponse({'result': False, 'error_mess': e.message})
                    except Exception as e:
                        try:
                            k8s_obj = models.K8sApp.objects.get(service_name=service_name)
                            project_name = k8s_obj.project_name.project_name
                            service_name = k8s_obj.service_name
                            yaml_name = k8s_obj.deploy_yaml
                            if yaml_name == '':
                                continue
                            yaml_obj = K8sYamlParse(yaml_name)
                            ok, yaml_data = yaml_obj.parse()
                            if ok:
                                namespace = yaml_data[0]['metadata']['namespace']
                                pod_label = yaml_data[0]['spec']['template']['metadata']['labels']['k8s-app']
                                label_selector = 'k8s-app=%s' % pod_label
                                tmp = {project_name: {service_name: {'start_time': start_time,'namespace': namespace, 'label_selector': label_selector}}}
                                p_key = '%s_permission:%s' % (username, service_name)
                                # 刷入数据到redis
                                try:
                                    if redis_conn.ttl(p_key) < long_time:
                                        redis_conn.set(p_key, json.dumps(tmp), ex=long_time)
                                except Exception as e:
                                    logger.error('输入数据%s到redis报错，错误信息：%s' % (json.dumps(tmp), e.message))
                                    return JsonResponse({'result': False, 'error_mess': e.message})
                            else:
                                logger.error("解析yaml文件%s失败，错误信息：%s" % (yaml_name, yaml_data))
                                return JsonResponse({'result': False, 'error_mess': yaml_data})
                        except Exception as e:
                            logger.error('处理k8sl类型应用失败，错误信息：%s' % e.message)
                            return JsonResponse({'result': False, 'error_mess': e.message})
            else:
                return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class HostPowerQuery(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(HostPowerQuery, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'host-application-query.html', {'role_name': self.role})


@method_decorator(login_required, 'dispatch')
class HostPowerAdminQuery(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(HostPowerAdminQuery, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'host-application-query-admin.html', {'role_name': self.role})


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class HostPowerApply(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(HostPowerApply, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            # 如果为ajax调用的get请求返回一个应用服务列表
            try:
                s_obj = models.Service.objects.exclude(status='offline')
                # 定义临时字典用于存放获取到的数据
                tmp = {}
                for s_obj_item in s_obj:
                    project_name = s_obj_item.project_name.project_name
                    if project_name in tmp.keys():
                        tmp[project_name].append(s_obj_item.service_name)
                    else:
                        tmp[project_name] = [s_obj_item.service_name]
                k8s_obj = models.K8sApp.objects.exclude(status='offline')
                for k8s_obj_item in k8s_obj:
                    project_name = k8s_obj_item.project_name.project_name
                    if project_name in tmp.keys():
                        tmp[project_name].append(k8s_obj_item.service_name)
                    else:
                        tmp[project_name] = [k8s_obj_item.service_name]
            except Error as e:
                logger.error('查询数据库获取服务信息失败，错误信息如下：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True, 'data': tmp})
        else:
            return render(request, 'host-application-apply.html', {'role_name': self.role})

    def post(self, request):
        username = request.user.get_full_name()
        service_name = ','.join(list(set(request.POST.get('service_name').split(','))))
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        apply_reason = request.POST.get('reason')
        # 入库
        try:
            models.HostPowerApply.objects.create(username=username,
                                                 service_name=service_name,
                                                 start_time=start_time,
                                                 end_time=end_time,
                                                 apply_reason=apply_reason,
                                                 apply_time=datetime.datetime.now())
        except Error as e:
            logger.error("插入申请主机权限数据入库失败，错误信息：%s" % json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class HostPowerApplyVerifyStatus(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(HostPowerApplyVerifyStatus, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            # 判断用户是否为admin角色用户，如果是admin角色用户返回近七天所有用户申请权限的返回数据
            # 如果是普通用户返回近七天这个用户的所有权限
            try:
                is_admin_obj = models.MyUser.objects.filter(username=request.user.get_username(),role__name='admin')
            except Error as e:
                logger.error('查询数据库失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 定义一个临时list 用于存放返回数据
            tmp_lit = []
            if is_admin_obj.exists():
                # 判断为admin角色用户
                try:
                    host_apply_order_obj = models.HostPowerApply.objects.filter(apply_time__gt=(datetime.datetime.now() - datetime.timedelta(days=7))).order_by('-apply_time')
                except Error as e:
                    logger.error("查询申请主机权限上线单失败，错误信息：%s" % json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                # 普通用户
                try:
                    host_apply_order_obj = models.HostPowerApply.objects.filter(username=request.user.get_full_name(), apply_time__gt=(datetime.datetime.now() - datetime.timedelta(days=7))).order_by('-apply_time')
                except Error as e:
                    logger.error("查询申请主机权限上线单失败，错误信息：%s" % json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
            # 查询完成数据库，获取到数据对象，开始格式化数据返回给前端
            for order_item in host_apply_order_obj:
                tmp_lit.append({
                    'id': order_item.id,
                    'username': order_item.username,
                    'apply_time': order_item.apply_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'service_name': order_item.service_name,
                    'start_time': order_item.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': order_item.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_agree': order_item.is_agree,
                    'apply_reason': order_item.apply_reason,
                    'apply_result': order_item.apply_result
                })
            else:
                return JsonResponse({'result': True, 'data': tmp_lit})
        else:
            return render(request, 'host-application-apply-verify-status.html', {'role_name': self.role})


@method_decorator(login_required, 'dispatch')
class HostPowerApplyVerify(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(HostPowerApplyVerify, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            # 查询未审批的权限
            try:
                order_obj = models.HostPowerApply.objects.filter(is_agree=None).order_by('-apply_time')
            except Error as e:
                logger.error('审批权限时候查询数据库失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 格式化数据返回给前端
            tmp_list = []
            for order_item in order_obj:
                tmp_list.append({
                    'id': order_item.id,
                    'username': order_item.username,
                    'apply_time': order_item.apply_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'service_name': order_item.service_name,
                    'start_time': order_item.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': order_item.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_agree': order_item.is_agree,
                    'apply_reason': order_item.apply_reason,
                    'apply_result': order_item.apply_result
                })
            else:
                return JsonResponse({'result': True, 'data': tmp_list})
        else:
            return render(request, 'host-application-apply-verify.html', {'role_name': self.role})

    def post(self, request):
        nid = request.POST.get('id')
        is_agree = request.POST.get('is_agree')
        apply_result = request.POST.get('result')
        # 更新结果
        try:
            models.HostPowerApply.objects.filter(id=nid).update(is_agree=is_agree, apply_result=apply_result)
        except Error as e:
            logger.error("更新id为%s的数据失败，错误信息：%s" % (nid, json.dumps(e.args)))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class HostPowerApplyManager(View):
    def dispatch(self, request, *args, **kwargs):
        return super(HostPowerApplyManager, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                username_obj = models.MyUser.objects.exclude(role__name='admin').values_list('first_name')
            except Error as e:
                logger.error('查询用户别名失败，错误信息：%s' %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True, 'data': [item[0] for item in username_obj]})
        else:
            return render(request, 'host-application-apply-manger.html')

    def post(self, request):
        username = request.POST.get('username')
        service_name = request.POST.get('service_name')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        apply_result = request.POST.get('apply_result')
        apply_reason = request.POST.get('reason')
        # 开始插入数据到数据库
        try:
            models.HostPowerApply.objects.create(
                username=username,
                service_name=service_name,
                start_time=start_time,
                end_time=end_time,
                apply_result=apply_result,
                apply_reason=apply_reason,
                apply_time=datetime.datetime.now(),
                is_agree=0
            )
        except Error as e:
            logger.error("插入申请主机权限表失败，错误信息：%s" % e.args)
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})