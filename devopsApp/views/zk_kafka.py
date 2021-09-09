#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/4/29 9:09
    @FileName: zk_kafka.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
import json
import logging
from devopsApp import models
from django.db import Error
from django.views.generic import View
from django.utils.decorators import method_decorator
from common.PermissonDecorator import permission_controller
from django.contrib.auth.decorators import login_required
from common.Page_split import Page
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse,JsonResponse
from kafka.errors import KafkaError
from kafka.client import KafkaClient
from kafka.admin import KafkaAdminClient,NewTopic
logger = logging.getLogger('django.request')


@method_decorator(login_required,'dispatch')
@method_decorator(permission_controller, 'dispatch')
class ZkKafka(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role_name = request.user.role.name
        except Error, e:
            logger.error('获取角色信息失败：%s' %e.args[1])
            self.role_name = 'guest'
        return super(ZkKafka, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                kafka_obj = models.KafkaList.objects.all().values('clustername','ip','base_path','version','zk__clustername')
                zk_obj = models.ZookeeperList.objects.all().values('clustername','ip','base_path','version')
            except Error, e:
                logger.error('查询kafka，zk信息失败：%s' %e.args[1])
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            else:
                return HttpResponse(json.dumps({
                    'result': True,
                    'kafka': list(kafka_obj),
                    'zk': list(zk_obj)
                }))
        else:
            return render(request, 'ZK-KAFKA.html', {'role_name':self.role_name})

    def post(self, request):
        post_type = request.POST.get('post_type', None)
        clustername = request.POST.get('clustername', None)
        ip = request.POST.get('ip', None)
        port = request.POST.get('port', None)
        base_path = request.POST.get('base_path', None)
        version = request.POST.get('version', None)
        if post_type and ip and port and base_path and clustername:
            ip_port = ','.join([item + ':' + port for item in ip.strip().split(',')])
            if post_type == 'zk':
                try:
                    models.ZookeeperList.objects.create(clustername=clustername.strip(), ip=ip_port,
                                                        base_path=base_path,
                                                        version=version)
                except Error, e:
                    logger.error('插入zk集群信息失败：%s' % e.args[1])
                    return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                else:
                    return HttpResponse(json.dumps({'result': True}))
            elif post_type == 'kafka':
                zkname = request.POST.get('zkname', None)
                if zkname:
                    try:
                        models.KafkaList.objects.create(
                            clustername=clustername,
                            ip=ip_port,
                            base_path=base_path,
                            version=version,
                            zk=models.ZookeeperList.objects.get(clustername=zkname)
                        )
                    except Error, e:
                        logger.error('kafka信息入库失败：%s' %e.args[1])
                        return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
                    else:
                        return HttpResponse(json.dumps({'result': True}))
                else:
                    return HttpResponse(json.dumps({'result': False, 'error_mess': 'post 参数不正确'}))

        else:
            return HttpResponse(json.dumps({'result': False, 'error_mess': 'post 请求参数有问题'}))


@method_decorator(login_required, 'dispatch')
class ZkKafkaUpdate(View):
    def dispatch(self, request, *args, **kwargs):
        return super(ZkKafkaUpdate, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        old_clustername = request.POST.get('old_clustername')
        clustername = request.POST.get('clustername')
        ip = request.POST.get('ip')
        base_path = request.POST.get('base_path')
        version = request.POST.get('version')
        post_type = request.POST.get('type')
        if post_type == 'zk':
            try:
                models.ZookeeperList.objects.filter(clustername=old_clustername).update(clustername=clustername, ip=ip, base_path=base_path, version=version)
            except Error, e:
                logger.error('update zk 信息失败：%s' %e.args[1])
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            else:
                return HttpResponse(json.dumps({'result': True}))
        else:
            zk__clustername = request.POST.get('zk__clustername')
            try:
                print zk__clustername
                models.KafkaList.objects.filter(clustername=old_clustername).update(
                    clustername=clustername,
                    ip=ip,
                    base_path=base_path,
                    version=version,
                    zk=models.ZookeeperList.objects.get(clustername=zk__clustername)
                )
            except Error, e:
                logger.error('update kafka 信息失败：%s' %e.args[1])
                return HttpResponse(json.dumps({'result': True}))
            else:
                return HttpResponse(json.dumps({'result': True}))


@method_decorator(login_required, 'dispatch')
class ZkKafkaDelete(View):
    def dispatch(self, request, *args, **kwargs):
        return super(ZkKafkaDelete,self).dispatch(request, *args, **kwargs)

    def post(self, request):
        post_type = request.POST.get('type')
        clustername = request.POST.get('clustername')
        if post_type == 'kafka':
            try:
                models.KafkaList.objects.filter(clustername=clustername).delete()
            except Error, e:
                logger.error('删除kafka %s 失败，错误信息：%s' %(clustername,e.args[1]))
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args[1]}))
            else:
                return HttpResponse(json.dumps({'result': True}))
        else:
            try:
                kafka_obj = models.KafkaList.objects.filter(zk__clustername=clustername)
                if kafka_obj.exists():
                    cluster_q = kafka_obj.values('clustername')
                    return HttpResponse(json.dumps({'result': True, 'mess': True, 'res': list(cluster_q)}))
                else:
                    models.ZookeeperList.objects.filter(clustername=clustername).delete()
                    return HttpResponse(json.dumps({'result': True}))
            except Error, e:
                logger.error('删除zk %s 失败，错误信息：%s' %(clustername, e.args[1]))
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))


@method_decorator(login_required, 'dispatch')
class KafkaMess(View):
    def dispatch(self, request, *args, **kwargs):
        return super(KafkaMess, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        bootstrap_servers = request.GET.get('bootstrap_servers')
        try:
            kafkaclient = KafkaClient(bootstrap_servers=bootstrap_servers)
        except KafkaError, e:
            logger.error('查询kafka失败错误信息：%s' %e.message)
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.message}))
        else:
            meta = kafkaclient.poll()
            if not meta:
                return HttpResponse(json.dumps({'result': False, 'error_mess': '获取结果为空列表'}))
            else:
                topic_tuple = meta[0].topics
                data = []
                for item in topic_tuple:
                    if item[1] != '__consumer_offsets':
                        topic_name = item[1]
                        partions = len(item[3])
                        replicas = len(item[3][0][3])
                        data.append({'topic_name': topic_name, 'partions': partions, 'replicas': replicas})
                else:
                    kafkaclient.close()
                    return HttpResponse(json.dumps({'result': True, 'data': data}))


@method_decorator(login_required, 'dispatch')
class CreateTopic(View):
    def dispatch(self, request, *args, **kwargs):
        return super(CreateTopic, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        kafka_name = request.POST.get("kafka_name")
        topic_name = request.POST.get("topic_name")
        partions_num = request.POST.get("partions_num")
        replica_num = request.POST.get("replica_num")
        # 判断 topic 名字，分区数，和副本数量
        # 如果 topic 名字为空或者为None 返回错误信息,
        if len(topic_name) == 0 or topic_name is None:
            return JsonResponse({'result': False, 'error_mess': 'topic 不能为空'})
        else:
            # 判断topic 名字是否含有_ 分割字符串
            if topic_name.__contains__('_'):
                return JsonResponse({'result': False, 'error_mess': 'topic 名字不能用_分割字符'})
            else:
                try:
                    bootstrap = models.KafkaList.objects.get(clustername=kafka_name.strip()).ip
                except Error, e:
                    error_mess = '查询kafka 集群ip地址失败错误信息：%s' % e.args[1]
                    return JsonResponse({'result': False, 'error_mess': error_mess})

        # 如果partions 为空 设置默认值为3
        partions_num = 3 if partions_num is None or len(partions_num) == 0 else int(partions_num)
        # 如果 副本数为空或者None 返回2
        replica_num = 2 if replica_num is None or len(replica_num) == 0 else int(replica_num)

        # 判断topic 是否已经存在
        try:
            kafka_client = KafkaClient(bootstrap_servers=bootstrap)
            topic_obj = kafka_client.poll()
            kafka_client.close()
            if topic_obj:
                topics_list = [item[1] for item in topic_obj[0].topics]
                if topic_name in topics_list:
                    return JsonResponse({'result': False, 'error_mess': '%s topic已经存在，不能重复创建' % topic_name})
        except KafkaError, e:
            logger.error('查询kafka %s 失败：%s' % (bootstrap, e.message))
            return JsonResponse({'result': False, 'error_mess': '查询%s topic是否存在发生异常：%s' % (topic_name, e.message)})

        # 开始创建topic
        try:
            kafka_admin = KafkaAdminClient(bootstrap_servers=bootstrap)
            newtopic = NewTopic(name=topic_name,num_partitions=partions_num,replication_factor=replica_num)
            kafka_admin.create_topics([newtopic])
            kafka_admin.close()
        except KafkaError, e:
            logger.info("创建topic %s失败，错误信息：%s" % (topic_name, e.message))
            return JsonResponse({'result': False, 'error_mess': '创建topic %s失败错误信息:%s' % (topic_name, e.message)})
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class DeleteTopic(View):
    def dispatch(self, request, *args, **kwargs):
        return super(DeleteTopic, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        bootstrap_servers = request.POST.get('bootstrap_servers')
        topic_name = request.POST.get('topic_name')
        try:
            kafkaclient = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
            kafkaclient.delete_topics(topics=[topic_name])
        except KafkaError, e:
            logger.error('删除%s kafka集群，topic %s失败，错误信息：%s' % (bootstrap_servers, topic_name, e.message))
            return JsonResponse({'result': False, 'error_mess': e.message})
        else:
            return JsonResponse({'result': True})
        finally:
            kafkaclient.close()

