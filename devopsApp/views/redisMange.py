#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/6/21 16:46
    @FileName: redisMange.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
import json
import datetime
import redis
import re
from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from django.db import Error
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from common.PermissonDecorator import permission_controller
import logging
from devopsApp import models
from django.views.generic import View
from rediscluster import RedisCluster

logger = logging.getLogger('django.request')


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class RedisMange(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role_name = request.user.role.name
        except Error, e:
            logger.error('获取角色信息失败：%s' %e.args[1])
            self.role_name = 'guest'
        return super(RedisMange, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, 'RedisMange.html', {'role_name': self.role_name})


@method_decorator(login_required, 'dispatch')
class AddRedisCluster(View):
    def dispatch(self, request, *args, **kwargs):
        return super(AddRedisCluster, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        clustername = request.GET.get('clustername')
        if clustername is None:
            try:
                redis_obj = models.Redis.objects.filter().values('clustername', 'ipaddr', 'deploy_type')
            except Error, e:
                logger.error('查询redis信息失败：%s' % e.args[1])
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                data = [item for item in redis_obj]
                return JsonResponse({'result': True, 'data': data})
        else:
            try:
                redis_obj = models.Redis.objects.filter(clustername=clustername).values('clustername', 'ipaddr', 'version', 'deploy_type', 'base_path')
            except Error, e:
                logger.error('查询redis信息失败：%s' % e.args[1])
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True, 'data': redis_obj[0]})

    def post(self, request):
        redisclustername = request.POST.get('redisclustername')
        deploy_type = request.POST.get('deploy_type')
        ipaddr = request.POST.get('ipaddr')
        base_path = request.POST.get('base_path')
        version = request.POST.get('version')

        if redisclustername and deploy_type and ipaddr and base_path and version:
            try:
                if models.Redis.objects.filter(clustername=redisclustername).exists():
                    return JsonResponse({'result': False, 'error_mess': '集群已经存在，不能重复添加'})

                models.Redis.objects.create(
                    clustername=redisclustername,
                    deploy_type=deploy_type,
                    ipaddr=ipaddr,
                    base_path=base_path,
                    version=version
                )
            except Error, e:
                logger.error("redis 集群信息入库失败：%s" % e.args[1])
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True})
        else:
            return JsonResponse({'result': False, 'error_mess': '文本框不能为空'})


@method_decorator(login_required, 'dispatch')
class ModifyRedisCluster(View):
    def dispatch(self, request, *args, **kwargs):
        return super(ModifyRedisCluster, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        clustername = request.GET.get('clustername')
        try:
            models.Redis.objects.get(clustername=clustername).delete()
        except Error, e:
            logger.error('删除Redis集群%s失败：%s' % (clustername, e.args[1]))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})

    def post(self, request):
        oldclustername = request.POST.get('oldclustername')
        clustername = request.POST.get('clustername')
        ipaddr = request.POST.get('ipaddr')
        base_path = request.POST.get('base_path')
        version = request.POST.get('version')
        if clustername and ipaddr and base_path and version:
            try:
                models.Redis.objects.filter(clustername=oldclustername).update(clustername=clustername, ipaddr=ipaddr, base_path=base_path, version=version)
            except Error, e:
                logger.error('更新Redis信息失败：%s' %e.args[1])
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True})
        else:
            return JsonResponse({'result': False, 'error_mess': '修改文本框不能为空'})


@method_decorator(login_required, 'dispatch')
class QueryRedisMess(View):
    def dispatch(self, request, *args, **kwargs):
        return super(QueryRedisMess, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        clustername = request.GET.get('clustername')
        try:
            redis_obj = models.Redis.objects.filter(clustername=clustername).values('clustername', 'deploy_type', 'ipaddr', 'version', 'base_path', 'password')
        except Error, e:
            logger.error('查询%s Rdis信息失败：%s' % (clustername, e.args[1]))
            return JsonResponse({'result': False, 'error_mess': e.args})
        redis_mess = redis_obj[0]
        redis_password = redis_mess['password']
        del redis_mess['password']
        if redis_mess['deploy_type'] == 'Cluster':
            startup_nodes = []
            for item in redis_mess['ipaddr'].strip().split(','):
                startup_nodes.append({
                    'host': item.strip().split(':')[0],
                    'port': int(item.strip().split(':')[1])
                })
            try:
                redis_client = RedisCluster(startup_nodes=startup_nodes, socket_timeout=2)
            except Exception, e:
                logger.error('链接Redis集群%s失败：%s' % (redis_mess['ipaddr'], e.message))
                return JsonResponse({'result': False, 'error_mess': e.message})
            try:
                redis_nodes_obj = redis_client.cluster_nodes()

            except Exception, e:
                logger.error('查询redis集群%s节点信息失败:%s' % (redis_mess['ipaddr'], e.message))
                return JsonResponse({'result': False, 'error_mess': e.message})

            redis_nodes_tmp = [{'host': item['host'], 'flags': item['flags'], 'id': item['id'], 'master': item['master'], 'port': item['port']} for item in redis_nodes_obj]
            redis_nodes = []
            for item in redis_nodes_tmp:
                if item['flags'][0] == 'slave' or (item['flags'][0] == 'myself' and item['flags'][1] == 'slave'):
                    for masteritem in redis_nodes_tmp:
                        if item['master'] == masteritem['id']:
                            redis_nodes.append((
                                {'host': item['host'], 'port': item['port'], 'flags': 'slave'},
                                {'host': masteritem['host'], 'port': masteritem['port'], 'flags': 'master'}
                            ))
            try:
                redis_inf_obj = redis_client.info()
            except Exception, e:
                logger.error('查询redis %s info信息失败，错误信息：%s' % (redis_mess['ipaddr'], e.message))
                return JsonResponse({'result': False, 'error_mess': e.message})
            memory_total = 0
            memory_used = 0
            for key, value in redis_inf_obj.items():
                if value['role'] == 'master':
                    memory_total = memory_total + value['maxmemory']
                    memory_used = memory_used + value['used_memory']
            return JsonResponse({'result': True, 'redis_mess': redis_mess, 'redis_memory': {'memory_total': memory_total, 'memory_used': memory_used}, 'redis_nodes': redis_nodes })
        elif redis_mess['deploy_type'] == 'Standone':
            redis_ip, port = redis_mess['ipaddr'].strip().split(':')
            try:
                if redis_password is not None:
                    client = redis.Redis(
                        host=redis_ip,
                        port=port,
                        password=redis_password
                    )
                else:
                    client = redis.Redis(
                        host=redis_ip,
                        port=port,
                    )
            except Exception as e:
                logger.error('创建redis链接失败(%s),错误信息:%s' % (redis_mess['ipaddr'], e.message))
                return JsonResponse({'result': False, 'error_mess': e.message})
            else:
                logger.info('创建redis客户端成功（%s）' % redis_mess['ipaddr'])
                info = client.info()
                memory_total = info['maxmemory'],
                memory_used = info['used_memory']
                return JsonResponse({
                    'result': True,
                    'redis_mess': redis_mess,
                    'redis_memory': {'memory_total': memory_total, 'memory_used': memory_used},
                    'redis_nodes': [[{'host': redis_ip, 'port': port, 'flags': 'master'}]]
                })
        else:
            redis_ip_port_list = redis_mess['ipaddr'].strip().split(',')
            redis_nodes = [[]]
            for ip_port in redis_ip_port_list:
                redis_ip, port = ip_port.strip().split(':')
                try:
                    if redis_password is not None:
                        client = redis.Redis(
                            host=redis_ip,
                            port=port,
                            password=redis_password
                        )
                    else:
                        client = redis.Redis(
                            host=redis_ip,
                            port=port,
                        )
                except Exception as e:
                    logger.error('创建redis链接失败(%s),错误信息:%s' % (redis_mess['ipaddr'], e.message))
                    return JsonResponse({'result': False, 'error_mess': e.message})
                else:
                    logger.info('创建redis客户端成功（%s）' % redis_mess['ipaddr'])
                    info = client.info()
                    if info['role'] == 'slave':
                        redis_nodes[0].append({
                            'host': redis_ip,
                            'port': port,
                            'flags': 'slave'
                        })
                    else:
                        redis_nodes[0].append({
                            'host': redis_ip,
                            'port': port,
                            'flags': 'master'
                        })
                        memory_total = info['maxmemory'],
                        memory_used = info['used_memory']
            else:
                return JsonResponse({
                    'result': True,
                    'redis_mess': redis_mess,
                    'redis_memory': {'memory_total': memory_total, 'memory_used': memory_used},
                    'redis_nodes': redis_nodes
                })


@method_decorator(login_required, 'dispatch')
class RedisExcCom(View):
    def dispatch(self, request, *args, **kwargs):
        return super(RedisExcCom, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        # 查询数据库获取redis集群信息
        try:
            redis_cluster_obj = models.Redis.objects.filter()
        except Error as e:
            logger.error("查询Redis表报错,错误信息：%s"  %json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        # 遍历queryset 集合查询结果返回
        # 定义一个临时list用于数据返回
        result_tmp = []
        for one_redis_item in redis_cluster_obj:
            if one_redis_item.deploy_type == 'Cluster':
                result_tmp.append({'cluster_name': one_redis_item.clustername, 'ipaddr': one_redis_item.ipaddr, 'db': ['db0']})
            else:
                ip_port = one_redis_item.ipaddr.strip().split(',')[0]
                ip, port = ip_port.strip().split(':')
                try:
                    client = redis.Redis(
                        host=ip,
                        port=port,
                        password=one_redis_item.password
                    )
                except Exception as e:
                    logger.error("查询redis（%s）信息失败，错误信息：%s" % (ip_port, e.message))
                    return JsonResponse({'result': False, 'error_mess': e.message})
                else:
                    info = client.info()
                    db = []
                    for item in info.keys():
                        if re.search(r'db\d+', item) is not None:
                            db.append(item)
                    else:
                        result_tmp.append({'cluster_name': one_redis_item.clustername, 'ipaddr': one_redis_item.ipaddr, 'db': db})
        else:
            # 返回最终结果
            return JsonResponse({'result': True, 'data': result_tmp})

    def post(self, request):
        ipaddr = request.POST.get('ipaddr').strip()
        redis_db = request.POST.get('db').strip().replace('db', '')
        ipaddr_list = [{'host': item.strip().split(':')[0], 'port': item.strip().split(':')[1]} for item in ipaddr.split(',')]
        cluster_com_str = request.POST.get('com').strip()
        forbid_com_list = ['BLPOP', 'BRPOP', 'BRPOPLPUSH', 'SUBSCRIBE', 'BGSAVE', 'CLUSTER']

        # 判断发送过来的命令不能为空，如果为空则返回结果
        if cluster_com_str == '':
            return JsonResponse({'err_mess': '输入命令不能为空'})
        if cluster_com_str.__contains__('\n'):
            return JsonResponse({'err_mess': '每次只能执行一条命令'})
        # cluster_com 命令不为空时候，说明已经有命令发过来，需要执行了，这时候需要提前第一个以空格分隔命令
        # 定义一个临时list 用于存放命令数据
        cluster_com = [item.strip() for item in cluster_com_str.strip().split(';')]
        # 命令必须全部大写
        cluster_com[0] = cluster_com[0].upper()
        if cluster_com[0] in forbid_com_list:
            return JsonResponse({'err_mess':'%s 命令不允许执行' %cluster_com_str})
        # 初始化一个redis链接
        # 查询数据库获取redis信息
        try:
            redis_obj = models.Redis.objects.get(ipaddr=ipaddr)
        except Exception as e:
            logger.error("查询redis（%s）信息失败,错误信息：%s" % (ipaddr, e.message))
            return JsonResponse({'err_mess': e.message})
        else:
            if redis_obj.deploy_type == 'Cluster':
                rc = RedisCluster(startup_nodes=ipaddr_list)
            elif redis_obj.deploy_type == 'Standone':
                redis_ip,port = ipaddr.strip().split(':')
                rc = redis.Redis(host=redis_ip, port=port, db=redis_db,password=redis_obj.password)
            else:
                redis_ip_list = ipaddr.strip().split(',')
                for redis_ip_port in redis_ip_list:
                    redis_ip, port = redis_ip_port.strip().split(':')
                    rc = redis.Redis(host=redis_ip, port=port, db=redis_db, password=redis_obj.password)
                    if rc.info()['role'] == 'master':
                        break

        return_result = ''
        try:
            redis_com_res = rc.execute_command(*cluster_com)
        except Exception as e:
            logger.error('执行命令%s失败，错误信息：%s' % (cluster_com_str, e.message))
            return JsonResponse({'err_mess': e.message})
        else:
            if isinstance(redis_com_res, list):
                return_result = redis_com_res[:20]
            elif isinstance(redis_com_res, tuple):
                return_result = redis_com_res[:20]
            elif isinstance(redis_com_res, set):
                return_result = list(redis_com_res)[:20]
            elif redis_com_res is None:
                return_result = ''
            else:
                return_result = redis_com_res
            return HttpResponse(json.dumps(return_result, ensure_ascii=False))
        finally:
            try:
                models.RedisExecLog.objects.create(
                    username=request.user.get_full_name(),
                    exec_time=datetime.datetime.now(),
                    exec_com=cluster_com_str,
                    exec_result=return_result,
                    cluster=models.Redis.objects.get(ipaddr=ipaddr)
                )
            except Exception as e:
                pass








