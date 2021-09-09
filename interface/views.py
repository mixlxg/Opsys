# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function,division
import json
import logging
from django.shortcuts import HttpResponse
from django.views import View
from devopsApp import models
from django.db import Error
from django.http import JsonResponse
from rediscluster import RedisCluster
import os

interface_logger = logging.getLogger('interface')
# Create your views here.


class ZabbixServiceDiscovery(View):

    def dispatch(self, request, *args, **kwargs):
        return super(ZabbixServiceDiscovery, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        host_ip = request.POST.get('ip')
        if host_ip is None:
            interface_logger.error("调用参数ip不能为空")
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': 'ip 不能为空'}))
        try:
            service_obj = models.Host.objects.filter(ip=host_ip, service__status='online')
        except Error, e:
            interface_logger.error('查询数据库失败失败报错如下：%s' %e.mesage)
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': '查询数据库失败' }))
        else:
            if service_obj.exists():
                result = {'data': []}
                for item in service_obj.values('ip', 'service__service_name', 'service__service_port'):
                    if item['service__service_port'] != 0:
                        result['data'].append({'{#MYIP}': item['ip'], '{#SERVICE_NAME}': item['service__service_name'],
                                               '{#SERVICE_PORT}': item['service__service_port']})
                    else:
                        result['data'].append({'{#MYIP}': item['ip'], '{#SERVICE_NAME_PRO}': item['service__service_name'],
                                               '{#SERVICE_PRE}': item['service__service_name']})
                else:
                    return HttpResponse(json.dumps({'result': json.dumps(result)}))
            else:
                return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': '查询ip没有部署应用'}))


class ServiceQueryApi(View):
    def dispatch(self, request, *args, **kwargs):
        return super(ServiceQueryApi, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        """
        功能：返回应用的所有数据信息
        请求传参格式：不传参：表示返回所有应用的信息，serviceName：应用名称，返回要查询serviceName的所有信息
        """
        service_name = self.request.POST.get('serviceName')
        # 定义一个临时list 用于存放格式化好的服务信息数据，返回给调用端
        tmp_list = []
        # 判断是否传serviceName 参数，如果传参数则根据传递的服务名去获取数据，如果没有传参数则返回现网所有的服务信息
        if service_name is None:
            try:
                # 查询数据库获取Service所有服务信息
                service_obj = models.Service.objects.all()
            except Error as e:
                interface_logger.error("获取服务信息失败，错误信息：%s" %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            try:
                # 根据穿过的serviceName 查询服务信息数据
                service_obj = models.Service.objects.filter(service_name=service_name)
            except Error as e:
                interface_logger.error("获取%s服务信息失败，错误信息：%s" % (service_name, json.dumps(e.args)))
                return JsonResponse({'result': False, 'error_mess': e.args})

        # 循环遍历service_obj数据对象，并格式化服务信息数据
        for one_obj in service_obj:
            # 格式化服务信息 添加到临时list中，方便统一返回给调用端
            tmp_list.append({
                'project_name': one_obj.project_name.project_name,
                'service_name': one_obj.service_name,
                'type': one_obj.type,
                'service_port': one_obj.service_port,
                'jmx_port': one_obj.jmx_port,
                'base_path': one_obj.base_path,
                'package_name': one_obj.package_name,
                'status': one_obj.status,
                'package_deploy_path': one_obj.package_name,
                'start_script': one_obj.start_script,
                'stop_script': one_obj.stop_script,
                'log_path': one_obj.log_path,
                'service_conf_name': one_obj.service_conf_name,
                'jenkin_service_conf_name': one_obj.jenkin_service_conf_name,
                'ip': [one_ip[0] for one_ip in one_obj.host.all().values_list('ip')]
            })
        else:
            # 循环完成返回处理结果给调用端
            return JsonResponse({'result': True, 'data': tmp_list})


class MysqlSlowLogApi(View):
    def dispatch(self, request, *args, **kwargs):
        return super(MysqlSlowLogApi,self).dispatch(request, *args, **kwargs)

    def post(self, request):
        data = request.body.decode()
        # 判断传递过来的json数据是否为null ，如果null表示客户端没有传值过来
        if len(data) == 0:
            return JsonResponse({'result': False, 'error_mess': '请以json格式序列化数据传递到body中'})

        # 捕获异常，看传递的数据是否可反序列化
        try:
            slow_log_data = json.loads(data)
        except Exception as e:
            interface_logger.error("MysqlSlowLogApi接口body传递数据%s反序列化失败，错误信息：%s" % (data, e.message))
            return JsonResponse({'result': False, 'error_mess': '传递数据无法反序列化'})
        # 批量生成MysqlSlowLog对象然后批量入库
        try:
            tmp_mysql_slow_obj_list = []
            for mysql_slow_item in slow_log_data:
                tmp_mysql_slow_obj_list.append(models.MysqlSlowLog(
                    host=mysql_slow_item.get('host'),
                    remote_host=mysql_slow_item.get('remote_host'),
                    query_time=mysql_slow_item.get('query_time'),
                    sql_exc_time=mysql_slow_item.get('sql_exc_time'),
                    sql_lock_time=mysql_slow_item.get('sql_lock_time'),
                    sql_rows_examined=mysql_slow_item.get('sql_rows_examined'),
                    sql_text='''%s''' % mysql_slow_item.get('sql_text')
                ))
            else:
                models.MysqlSlowLog.objects.bulk_create(tmp_mysql_slow_obj_list, batch_size=2000)
        except Exception as e:

            interface_logger.error("慢查询数据入库失败：%s,错误信息：%s" %(data, json.dumps(e.args)))
            return JsonResponse({'result': False, 'error_mess': '入库失败'})
        else:
            return JsonResponse({'result': True})


class redisconfigfileDiscovery(View):

    def dispatch(self, request, *args, **kwargs):
        return super(redisconfigfileDiscovery, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        host_ip = request.POST.get('ip')
        print(type(host_ip))

        if host_ip is None:
            interface_logger.error("调用参数ip不能为空")
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': u'ip 不能为空'}))

        try:
            redis_ip_list = list(models.Redis.objects.all().values_list('ipaddr'))
            hosts = []
            if redis_ip_list:
                ip_list=(','.join([ip for ip_list in redis_ip_list for ip in ip_list])).split(',')
                for host_port_str in ip_list:
                    if host_ip in host_port_str:
                        hosts.append(host_port_str)
            else:
                interface_logger.error(u'没有查询到Redis ipaddr相关数据')
                return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': u'没有查询到Redis ipaddr相关数据'}))
        except Error, e:
            interface_logger.error(u'查询数据库失败失败报错如下：%s' %e.mesage)
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': u'查询数据库失败' }))
        else:
            result={'data':[]}
            if hosts:
                startup_nodes = []
                host_ip, port = hosts[0].split(':')
                startup_nodes.append(dict(host=host_ip, port=port))
                redis_client = RedisCluster(startup_nodes=startup_nodes, socket_timeout=2)
                redis_info = redis_client.info()

                if len(hosts) == 1:
                    config_file1 = redis_info[hosts[0]]['config_file']
                    result['data'].append({'{#REDIS_CONFIG_FILE1}': config_file1})

                elif len(hosts) == 2:

                    config_file1 = redis_info[hosts[0]]['config_file']
                    result['data'].append({'{#REDIS_CONFIG_FILE1}': config_file1})

                    config_file2 = redis_info[hosts[1]]['config_file']
                    result['data'].append({'{#REDIS_CONFIG_FILE2}': config_file2})
                else:
                    pass

                return HttpResponse(json.dumps({'result': json.dumps(result)}))
            else:
                return HttpResponse(json.dumps({'result': json.dumps(result), 'error': u'查询ip没有部署redis'}))


class kafkaconfigfileDiscovery(View):

    def dispatch(self, request, *args, **kwargs):
        return super(kafkaconfigfileDiscovery, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        host_ip = request.POST.get('ip')

        if host_ip is None:
            interface_logger.error("调用参数ip不能为空")
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': 'ip 不能为空'}))
        try:
            kafka_obj = models.KafkaList.objects.filter(ip__icontains=host_ip).get()
        except models.KafkaList.DoesNotExist,e:
            interface_logger.error(u'查询数据库失败,报错如下：%s' % e.message)
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': '查询ip没有部署应用'}))
        except Error,e:
            interface_logger.error(u'查询数据库失败,报错如下：%s' % e.mesage)
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': u'查询数据库失败'}))
        else:
            result = {'data':[]}
            base_path = kafka_obj.base_path
            if base_path:
                config_file_path = os.path.join(base_path,'config/server.properties')
                result['data'].append({'{#KAFKA2_CONFIG_FILE}':config_file_path })
                return HttpResponse(json.dumps({'result': json.dumps(result)}))
            else:
                return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': u'没有查询到kafka配置文件'}))


class zookeeperconfigfileDiscovery(View):

    def dispatch(self, request, *args, **kwargs):
        return super(zookeeperconfigfileDiscovery, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        host_ip = request.POST.get('ip')

        if host_ip is None:
            interface_logger.error("调用参数ip不能为空")
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': 'ip 不能为空'}))
        try:
            zk_obj = models.ZookeeperList.objects.filter(ip__icontains=host_ip).get()

        except models.ZookeeperList.DoesNotExist,e:
            interface_logger.error(u'查询数据库失败,报错如下：%s' % e.message)
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': '查询ip没有部署应用'}))
        except Error,e:
            interface_logger.error(u'查询数据库失败,报错如下：%s' % e.mesage)
            return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': u'查询数据库失败'}))

        else:
            result = {'data':[]}
            base_path = zk_obj.base_path
            if base_path:
                config_file_path = os.path.join(base_path,'conf/zoo.cfg')
                result['data'].append({'{#ZK_CONFIG_FILE}':config_file_path })
                return HttpResponse(json.dumps({'result': json.dumps(result)}))
            else:
                return HttpResponse(json.dumps({'result': json.dumps({'data': []}), 'error': u'没有查询到zk配置文件'}))
