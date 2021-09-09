#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/4/24 16:26
    @FileName: application.py
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
from django.shortcuts import render
from django.http import HttpResponse
from common.allocation_port import allocate_port
from celery_tasks.tasks.application_tasks import create_new_application
from celery_tasks.tasks import application_offline_tasks
from celery_tasks.tasks import application_restart_tasks
from common.create_job_id import create_job_id
from common.celery_task_query import query_task
from common.mySendMail.send_mail import SendMail
from django.http import JsonResponse
from django.db.models import F, Q
from celery_tasks.lib.pyssh import PySsh
from common.Mjenkins import Mjenkins
logger = logging.getLogger('django.request')


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class Application(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(Application, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                service_obj = models.Service.objects.all().values('service_name',
                                                                  'service_alias_name',
                                                                  'type',
                                                                  'service_port',
                                                                  'jmx_port',
                                                                  'online_date',
                                                                  'offline_date',
                                                                  'base_path',
                                                                  'package_name',
                                                                  'status',
                                                                  'start_script',
                                                                  'stop_script',
                                                                  'log_path',
                                                                  'service_conf_name',
                                                                  'jenkin_service_conf_name',
                                                                  'host__ip')

            except Error, e:
                logger.error('查询应用信息失败：%s' % e.args[1])
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            else:
                tmp_dict = {}
                for item in service_obj:
                    item['online_date'] = item['online_date'].strftime("%Y-%m-%d %H:%M:%S")
                    item['offline_date'] = item['offline_date'].strftime("%Y-%m-%d %H:%M:%S") if item[
                        'offline_date'] else None
                    if item['service_name'] in tmp_dict.keys():
                        tmp_dict[item['service_name']].append(item)
                    else:
                        tmp_dict[item['service_name']] = [item]
                else:
                    return HttpResponse(json.dumps({'result': True, 'service_mess': tmp_dict}))
        else:
            return render(request, 'application.html', {'role_name': self.role})


@method_decorator(login_required, 'dispatch')
class ApplicationRestart(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(ApplicationRestart, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            service_name = request.GET.get('service_name')
            if service_name is None:
                try:
                    obj = models.Service.objects.exclude(Q(start_script='', stop_script='') | Q(status='offline')).values(
                        'service_name',
                        'project_name__project_name'
                    )
                    pobj = models.Project.objects.all().values('project_name')
                except Error, e:
                    logger.error('查询Service表失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    res = [item for item in obj]
                    return JsonResponse({'result': True, 'data': res, 'pdata': list(pobj)})
            else:
                try:
                    obj = models.Service.objects.filter(service_name=service_name).annotate(ip=F('host__ip'), password=F('host__root_password')).values(
                        'service_name',
                        'project_name__project_name',
                        'ip',
                        'service_port',
                        'package_deploy_path',
                        'password'
                    )
                except Error, e:
                    logger.error('查询Service表失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    tmp_list = []
                    thread_list = []
                    for item in obj:
                        th = application_restart_tasks.CheckPortThtread(item)
                        th.start()
                        thread_list.append({'data': item, 'th': th})
                    else:
                        for thitem in thread_list:
                            if thitem['th'].is_alive():
                                thitem['th'].join()
                            check_res = thitem['th'].get_result()
                            logger.info('%s检测应用节点是运行状态结果：%s' % (json.dumps(thitem['data'], ensure_ascii=False), json.dumps(check_res,ensure_ascii=False)))
                            if check_res['result']:
                                status = 'runing'
                            else:
                                status = 'stoped'
                            tmp_list.append({'service_name': thitem['data']['service_name'], 'project_name__project_name': thitem['data']['project_name__project_name'], 'host__ip': thitem['data']['ip'], 'status': status, 'service_port': thitem['data']['service_port']})
                    return JsonResponse({'result': True, 'data': tmp_list})
        else:
            return render(request, 'application-restart.html', {'role_name': self.role})

    def post(self, request):
        service_name = request.POST.get('service_name')
        optype = request.POST.get('optype')
        username = request.user.get_full_name()
        # 检查是否有用户正在停止，启动，或者重启这个项目，如果有，则返回错误信息，如果没有则往下执行代码
        try:
            pobj = models.AppRestart.objects.filter(service_name=service_name)
        except Error, e:
            logger.error('查询AppRestart表失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            if pobj.exists():
                logger.error('用户%s正在操作%s应用，您不能同时操作' % (pobj[0].username, service_name))
                return JsonResponse({'result': False, 'error_mess': '用户%s正在操作%s应用，您不能同时操作' % (pobj[0].username, service_name)})
        try:
            service_obj = models.Service.objects.filter(service_name=service_name).annotate(ip=F('host__ip'), password=F('host__root_password')).values(
                'service_name',
                'service_port',
                'start_script',
                'stop_script',
                'ip',
                'password',
                'package_deploy_path'
            )
        except Error, e:
            logger.error('查询Service表失败，错误信息：%s' % (json.dumps(e.args, ensure_ascii=False)))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            try:
                task_list = []
                for item in service_obj:
                    if optype == 'restart':
                        task_obj = application_restart_tasks.app_restart.delay(**item)
                        task_list.append({'service_name': item['service_name'], 'service_port': item['service_port'], 'ip': item['ip'], 'task_id': task_obj.id, 'optype': 'restart'})
                    elif optype == 'stop':
                        task_obj = application_restart_tasks.app_stop_task.delay(**item)
                        task_list.append({'service_name': item['service_name'], 'service_port': item['service_port'], 'ip': item['ip'], 'task_id': task_obj.id, 'optype': 'stop' })
                    elif optype == 'start':
                        task_obj = application_restart_tasks.app_restart.delay(**item)
                        task_list.append({'service_name': item['service_name'], 'service_port': item['service_port'], 'ip': item['ip'], 'task_id': task_obj.id, 'optype': 'start' })
            except Exception, e:
                logger.error('提交tasks  %s任务失败错误信息：%s' % (json.dumps(list(service_obj), ensure_ascii=False), e.message))
                return JsonResponse({'result': False, 'error_mess': e.message})
            else:
                # 重启信息到临时表里面
                try:
                    models.AppRestart.objects.create(
                        username=username,
                        service_name=service_name,
                        group_task_id=json.dumps(task_list),
                        op_type=optype
                    )
                except Error, e:
                    logger.error('插入AppRestart表失败，celery group id为%s,错误信息：%s' % (json.dumps(task_list), json.dumps(e.args, ensure_ascii=False)))
                    return JsonResponse({'result': False, 'error_mess': 'celery 任务已经提交group id为：%s,但是信息入库失败' % json.dumps(task_list)})
                return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class ApplicationRestartOne(View):
    def dispatch(self, request, *args, **kwargs):
        return super(ApplicationRestartOne, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        username = request.user.get_full_name()
        service_name = request.POST.get('service_name')
        service_port = request.POST.get('service_port')
        ip = request.POST.get('ip')
        optype = request.POST.get('optype')
        # 判断这个节点是否正在操作
        try:
            gobj = models.AppRestart.objects.filter(service_name=service_name)
        except Error, e:
            logger.info('查询AppRestart获取信息失败，错误信息：%s' %json.dumps(e.args, ensure_ascii=False))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            for item in gobj:
                if item.group_task_id != '' and item.task_id == '':
                    return JsonResponse({'result': False, 'error_mess': '%s用户正在%s 这个应用' % (item.username, item.op_type)})
                else:
                    tmp_json = json.loads(item.task_id)
                    if service_name == tmp_json['service_name'] and service_port == tmp_json['service_port'] and ip == tmp_json['ip']:
                        return JsonResponse({'result': False, 'error_mess': '%s用户正在%s 这个应用' % (item.username, item.op_type)})
        # 提交任务
        try:
            obj = models.Service.objects.filter(service_name=service_name, service_port=service_port, host__ip=ip).annotate(ip=F('host__ip'), password=F('host__root_password')).values(
                'service_port',
                'service_name',
                'ip',
                'password',
                'start_script',
                'stop_script',
                'package_deploy_path'
            )[0]
        except Error, e:
            logger.error('查询Service表格失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            try:
                if optype == 'restart':
                    task_obj = application_restart_tasks.app_restart.delay(**obj)
                    task_dict = {'service_name': obj['service_name'], 'service_port': obj['service_port'], 'ip': obj['ip'], 'task_id': task_obj.id, 'optype': 'restart'}
                elif optype == 'stop':
                    task_obj = application_restart_tasks.app_stop_task.delay(**obj)
                    task_dict = {'service_name': obj['service_name'], 'service_port': obj['service_port'], 'ip': obj['ip'], 'task_id': task_obj.id, 'optype': 'stop'}
                elif optype == 'start':
                    task_obj = application_restart_tasks.app_restart.delay(**obj)
                    task_dict = {'service_name': obj['service_name'], 'service_port': obj['service_port'], 'ip': obj['ip'], 'task_id': task_obj.id, 'optype': 'start'}
            except Exception, e:
                logger.error('%s提交task任务失败，错误信息：%s' % (json.dumps(obj, ensure_ascii=False), json.dumps(e.args, ensure_ascii=False)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                try:
                    models.AppRestart.objects.create(
                        username=username,
                        service_name=service_name,
                        task_id=json.dumps(task_dict),
                        op_type=optype
                    )
                except Error, e:
                    logger.error('插入AppRestart表失败，celery task id为%s,错误信息：%s' % (json.dumps(task_dict), json.dumps(e.args, ensure_ascii=False)))
                    return JsonResponse({'result': False, 'error_mess': 'celery 任务已经提交task id为：%s,但是信息入库失败' % json.dumps(task_dict)})
                return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class ApplicationRestartQuery(View):
    def dispatch(self, request, *args, **kwargs):
        return super(ApplicationRestartQuery, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                obj = models.AppRestart.objects.all().order_by('group_task_id')
            except Error, e:
                logger.error('查询AppRestart 零时表获取结果失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                result_dict = {}
                for item in obj:
                    if item.group_task_id == '' and item.task_id != '':
                       mitem = json.loads(item.task_id)
                       one_tasks_res = query_task(task_id=mitem['task_id'])
                       result_dict[mitem['task_id']] = {
                           'service_name': mitem['service_name'],
                           'service_port': mitem['service_port'],
                           'ip': mitem['ip'],
                           'optype': mitem['optype'],
                           'status': one_tasks_res['result']
                       }
                       if one_tasks_res['result'] == 'SUCCESS' or one_tasks_res['result'] == 'FAILURE':
                           item.delete()
                    elif item.group_task_id != '':
                        delete_flag = True
                        mitem = json.loads(item.group_task_id)
                        for gitem in mitem:
                            g_task_res = query_task(task_id=gitem['task_id'])
                            result_dict[gitem['task_id']] = {
                                'service_name': gitem['service_name'],
                                'service_port': gitem['service_port'],
                                'ip': gitem['ip'],
                                'optype': gitem['optype'],
                                'status': g_task_res['result']
                            }
                            logger.info(g_task_res)
                            if g_task_res['result'] == 'SUCCESS':
                                pass
                            elif g_task_res['result'] == 'FAILURE':
                                pass
                            else:
                                delete_flag = False

                        else:
                            if delete_flag:
                                item.delete()
                else:

                    return JsonResponse({'result': True, 'data': result_dict})


@method_decorator(login_required, 'dispatch')
class ApplicationNewOnline(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(ApplicationNewOnline, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                service_type = models.Service.objects.values('type').distinct()
                username = models.MyUser.objects.filter().exclude(first_name='').values('first_name')
                project_class = models.Project.objects.all().values('project_name')
            except Error, e:
                return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
            else:
                data = {'service_type': [], 'username': [], 'project_class': [item['project_name'] for item in project_class]}
                for item in service_type:
                    data['service_type'].append(item['type'])
                for item in username:
                    data['username'].append(item['first_name'])
                return HttpResponse(json.dumps({'result': True, 'data': data}))
        else:
            return render(request, 'application-new-online.html', {'role_name': self.role})

    def post(self, request):
        ip = request.POST.get('ip')
        service_name = request.POST.get('service_name')
        service_type = request.POST.get('service_type')
        service_port = request.POST.get('service_port')
        jdk_version = request.POST.get('jdk_version')
        retrun_result_name = request.POST.get('retrun_result_name')
        project_class = request.POST.get('project_class')
        if ip is None and service_name is None:
            return HttpResponse(json.dumps({'result': False, 'error_mess': 'ip地址和应用名称不能为空'}))
        # 校验 应用名称是否已经存在
        try:
            service_name_obj = models.Service.objects.filter(service_name=service_name)
            if service_name_obj.exists():
                return HttpResponse(json.dumps({'result': False, 'error_mess': '%s已经存在' % service_name}))
        except Error, e:
            logger.error('查询数据库报错：%s' % e.args[1])
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))

        if service_port == '是':
            logger.info(ip)
            port_list = allocate_port(ip)
            logger.info(port_list)
            if port_list[0]:
                port = port_list[1]
            else:
                return HttpResponse(json.dumps({'result': False, 'error_mess': port_list[1]}))
        else:
            port = None
        # 获取对应ip的root账号密码
        try:
            rootpass = models.Host.objects.filter(ip__in=ip.strip().split(',')).values('ip', 'root_password')
        except Error, e:
            logger.error('查询数据库密码失败：%s' % e.args[1])
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
        tmp = []
        for item in ip.strip().split(','):
            tmp_dict = {}
            tmp_dict['ip'] = item
            tmp_dict['username'] = 'root'
            for rootpass_item in rootpass:
                if item == rootpass_item['ip']:
                    tmp_dict['password'] = rootpass_item['root_password']
                    break
            tmp_dict['port'] = 22
            tmp_dict['service_name'] = service_name
            tmp_dict['service_type'] = service_type
            tmp_dict['jdk_version'] = jdk_version
            tmp_dict['http_port'] = 0 if port is None else port
            tmp_dict['retrun_result_name'] = retrun_result_name
            tmp_dict['project_class'] = project_class
            try:
                task_obj = create_new_application.delay(tmp_dict)
            except Exception, e:
                tmp_dict['status'] = 'FAILURE'
                logger.error('执行任务时%s候抛出异常：%s' % (json.dumps(tmp_dict), e.message))
            else:
                tmp_dict['task_id'] = task_obj.id
                tmp.append(tmp_dict)
        else:
            try:
                job_id = create_job_id(request.user.username, service_name)
                models.Jobs.objects.create(username=request.user.username, job_id=job_id, job_type='create_new_app', post_data=json.dumps(tmp))
            except Error, e:
                logger.error("将create new app 任务信息入库失败：%s；任务信息：%s" % (e.args[1], json.dumps(tmp)))
                return HttpResponse(json.dumps({'result': False, 'error_mess': '任务已经生成，但是入库失败，需要查看日志查找task id信息'}))
            else:
                return HttpResponse(json.dumps({'result': True, 'job_id': job_id}))


@method_decorator(login_required, 'dispatch')
class ApplicationNewOnlineQuery(View):
    def dispatch(self, request, *args, **kwargs):
        return super(ApplicationNewOnlineQuery, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        job_id = request.GET.get('job_id', None)
        username = request.user.username
        try:
            if job_id is None:
                job_obj = models.Jobs.objects.filter(username=username, job_type='create_new_app')
            else:
                job_obj = models.Jobs.objects.filter(job_id=job_id, job_type='create_new_app')
        except Error, e:
            logger.error('查询job信息失败%s' % e.args[1])
            return HttpResponse(json.dumps({'result': False, 'error_mess': e.args}))
        else:
            result_mess = {}
            if job_obj.exists():
                job_mes = job_obj.values('job_id', 'post_data')
                for item in job_mes:
                    for task_item in json.loads(item['post_data']):
                        if item['job_id'] in result_mess.keys():
                            if 'status' in task_item.keys() and task_item['status'] == 'FAILURE':
                                result_mess[item['job_id']].append(task_item)
                            else:
                                task_result = query_task(task_item['task_id'])
                                logger.info('%s,result:%s' % (json.dumps(task_item), json.dumps(task_result)))
                                task_item['status'] = task_result['result']
                                result_mess[item['job_id']].append(task_item)
                        else:
                            if 'status' in task_item.keys() and task_item['status'] == 'FAILURE':
                                result_mess[item['job_id']] = [task_item]
                            else:
                                task_result = query_task(task_item['task_id'])
                                logger.info('%s,result:%s' % (json.dumps(task_item), json.dumps(task_result)))
                                task_item['status'] = task_result['result']
                                result_mess[item['job_id']] = [task_item]
                else:
                    for mid, check_item in result_mess.items():
                        for check_task_item in check_item:
                            if check_task_item['status'] == 'FAILURE' or check_task_item['status'] == 'SUCCESS':
                                continue
                            else:
                                break
                        else:
                            try:
                                models.Jobs.objects.filter(job_id=mid).delete()
                            except Error, e:
                                logger.error('删除已经执行完成的job（job id：%s)失败：%s' % (mid, e.args[1]))
                            else:
                                # 入库处理，添加项目到service表
                                for db_item in check_item:
                                    if db_item['status'] == 'SUCCESS':
                                        try:
                                            service_obj = models.Service.objects.get_or_create(
                                                service_name=db_item['service_name'],
                                                type=db_item['service_type'],
                                                service_port=int(db_item['http_port']),
                                                jmx_port=0,
                                                base_path='/webapp/%s' % db_item['service_name'],
                                                package_name='%s.jar' % db_item['service_name'],
                                                status='wait_online',
                                                start_script='/webapp/%s/bin/start.sh' % db_item['service_name'],
                                                stop_script='/webapp/%s/bin/stop.sh' % db_item['service_name'],
                                                log_path='/bizlog/%s' % db_item['service_name'],
                                                project_name=models.Project.objects.get(project_name=db_item['project_class'])
                                            )[0]
                                            host_obj = models.Host.objects.get(ip=db_item['ip'])
                                            service_obj.host.add(host_obj)
                                        except Error, e:
                                            logger.error("待上线应用%s 入库失败：%s" % (json.dumps(db_item), e.args[1]))
                                # 发送邮件
                                send_ccuser_list = ['tanghq5@chinaunicom.cn', 'lvxg9@chinaunicom.cn', 'xugl35@chinaunicom.cn']
                                try:
                                    user_mail = models.MyUser.objects.get(first_name=check_item[0]['retrun_result_name']).email
                                except Error, e:
                                    logger.error('获取email 地址失败：%s' % e.args[1])
                                    send_user_list = ['lvxg9@chinaunicom.cn']
                                else:
                                    send_user_list = [user_mail]
                                html_str = """
                                <div>你好，%s!!</div>
                                <div>以下表格是服务配置信息：</div>
                                <table  border="1" cellspacing="0" cellpadding="0">
                                <tr bgcolor="#AEEEEE">
                                    <td>服务名称</td>
                                    <td>部署ip地址</td>
                                    <td>服务端口</td>
                                    <td>服务类型</td>
                                    <td>jdk版本</td>
                                    <td>服务部署基目录</td>
                                    <td>日志目录</td>
                                    <td>初始化状态</td>
                                </tr>
                                """ % check_item[0]['retrun_result_name']
                                for send_mes_itm in check_item:
                                    html_str = html_str + """
                                    <tr>
                                        <td>%s</td>
                                        <td>%s</td>
                                        <td>%s</td>
                                        <td>%s</td>
                                        <td>%s</td>
                                        <td>/webapp/%s</td>
                                        <td>/bizlog/%s</td>
                                        <td>%s</td>
                                    </tr>
                                    """ % (send_mes_itm['service_name'],
                                           send_mes_itm['ip'],
                                           send_mes_itm['http_port'],
                                           send_mes_itm['service_type'],
                                           send_mes_itm['jdk_version'],
                                           send_mes_itm['service_name'],
                                           send_mes_itm['service_name'],
                                           send_mes_itm['status']
                                           )
                                else:
                                    html_str = html_str + "</table>"
                                    mail = SendMail(to_user=send_user_list, cs_user=send_ccuser_list)
                                    mail_conn = mail.connection
                                    if mail_conn[0]:
                                        mail.send('%s 配置信息' % send_mes_itm['service_name'], html_str, subtype='html')
                                    else:
                                        logger.error('发送%s邮件信息失败，错误信息：%s' % (html_str, mail_conn[1]))

                    logger.info(json.dumps({'result': True, 'data': result_mess}))
                    return HttpResponse(json.dumps({'result': True, 'data': result_mess}))
            else:
                logger.info(json.dumps({'result': True, 'data': {}}))
                return HttpResponse(json.dumps({'result': True, 'data': {}}))


@method_decorator(login_required, 'dispatch')
class ApplicationYJ(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(ApplicationYJ, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                obj = models.Host.objects.get(ip='192.200.239.188')
            except Error, e:
                logger.error('查询Host表失败错误信息：%s' %json.dumps(e.args, ensure_ascii=False))
                return JsonResponse({'result': False, 'error_mess': '查询Host表失败错误信息：%s'  %json.dumps(e.args, ensure_ascii=False)})
            try:
                ssh = PySsh(ip=obj.ip, username='root', paswword=obj.root_password)
            except Exception, e:
                logger.error('初始化ssh链接失败，错误信息：%s' %e.message)
                return JsonResponse({'result': False, 'error_mess': '初始化ssh链接失败，错误信息：%s' %e.message})
            try:
                recovery_res = ssh.comm('cd /home/bizlog/script;source /opt/usr/python3bin/bin/activate;fab -f uip_activemq_restart.py restart_all', timeout=120)
            except Exception, e:
                logger.error('紧急恢复uip-in 失败，错误信息：%s' %e.message)
                return JsonResponse({'result': False, 'error_mess': '执行恢复脚本失败，错误信息：%s' % e.message})
            else:
                logger.info(json.dumps(recovery_res))
                if recovery_res[0]:
                    if recovery_res[2]:
                        return JsonResponse({'result': False, 'error_mess': recovery_res[2]})
                    else:
                        tmp_str = '<br>'.join(recovery_res[1])
                        if tmp_str.__contains__('failed'):
                            return JsonResponse({'result': False, 'error_mess': tmp_str})
                        else:
                            return JsonResponse({'result': True})
                else:
                    return JsonResponse({'result': False, 'error_mess': recovery_res[2]})
        else:
            return render(request, 'application-yj.html', {'role_name': self.role})


@method_decorator(login_required, 'dispatch')
class ApplicationManage(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(ApplicationManage, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            service_name = request.GET.get('service_name')
            if service_name is None:
                try:
                    all_obj = models.Service.objects.all()
                    tmp_dict = {}
                    for item_obj in all_obj:
                        ip = [item[0] for item in item_obj.host.values_list('ip')]
                        if item_obj.project_name.project_name in tmp_dict.keys():
                            tmp_dict[item_obj.project_name.project_name].append(
                                {'service_name': item_obj.service_name,
                                 'type': item_obj.type,
                                 'service_port': item_obj.service_port,
                                 'jmx_port': item_obj.jmx_port,
                                 'base_path': item_obj.base_path,
                                 'package_deploy_path': item_obj.package_deploy_path,
                                 'package_name': item_obj.package_name,
                                 'status': item_obj.status,
                                 'start_script': item_obj.start_script,
                                 'stop_script': item_obj.stop_script,
                                 'log_path': item_obj.log_path,
                                 'service_conf_name': item_obj.service_conf_name,
                                 'jenkin_service_conf_name': item_obj.jenkin_service_conf_name,
                                 'ip': ip,
                                 'project_name': item_obj.project_name.project_name}
                            )
                        else:
                            tmp_dict[item_obj.project_name.project_name] = [
                                {'service_name': item_obj.service_name,
                                 'type': item_obj.type,
                                 'service_port': item_obj.service_port,
                                 'jmx_port': item_obj.jmx_port,
                                 'base_path': item_obj.base_path,
                                 'package_deploy_path': item_obj.package_deploy_path,
                                 'package_name': item_obj.package_name,
                                 'status': item_obj.status,
                                 'start_script': item_obj.start_script,
                                 'stop_script': item_obj.stop_script,
                                 'log_path': item_obj.log_path,
                                 'service_conf_name': item_obj.service_conf_name,
                                 'jenkin_service_conf_name': item_obj.jenkin_service_conf_name,
                                 'ip': ip,
                                 'project_name': item_obj.project_name.project_name}
                            ]
                    else:
                        return JsonResponse({'result': True, 'data': tmp_dict})
                except Exception as e:
                    logger.error('获取应用信息失败，错误信息：%s' %e.args[1])
                    return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return render(request, 'application-manage.html', {'role_name': self.role})

    def post(self, request):
        op_type = request.POST.get('op_type')
        if op_type == 'delete':
            service_name = request.POST.get('service_name')
            try:
                models.Service.objects.get(service_name=service_name).delete()
            except Error as e:
                logger.error('删除%s应用信息失败，错误信息：%s' % (service_name, json.dump(e.args)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True})
        elif op_type == 'update':
            service_name = request.POST.get('service_name')
            service_type = request.POST.get('service_type')
            service_port = request.POST.get('service_port')
            jmx_port = request.POST.get('jmx_port')
            base_path = request.POST.get('base_path')
            package_deploy_path = request.POST.get('package_deploy_path')
            package_name = request.POST.get('package_name')
            status = request.POST.get('status')
            start_script = request.POST.get('start_script')
            stop_script = request.POST.get('stop_script')
            log_path = request.POST.get('log_path')
            service_conf_name = request.POST.get('service_conf_name')
            jenkin_service_conf_name = request.POST.get('jenkin_service_conf_name')
            project_name = request.POST.get('project_name')
            # 根据前端传过来的project_name 获取project_name 对象
            try:
                project_name_obj = models.Project.objects.get(project_name=project_name)
            except Exception as e:
                logger.error('更新应用%s时获取project_name 信息失败错误信息：%s' % (service_name, json.dumps(e.args)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 更新service 信息
            try:
                models.Service.objects.filter(service_name=service_name).update(
                    type=service_type,
                    service_port=service_port,
                    jmx_port=jmx_port,
                    base_path=base_path,
                    package_deploy_path=package_deploy_path,
                    package_name=package_name,
                    status=status,
                    start_script=start_script,
                    stop_script=stop_script,
                    log_path=log_path,
                    service_conf_name=service_conf_name,
                    jenkin_service_conf_name=jenkin_service_conf_name,
                    project_name=project_name_obj)
            except Exception as e:
                logger.error('更新应用%s信息失败，错误信息：%s' % (service_name, json.dumps(e.args)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class ApplicationOffline(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(ApplicationOffline, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                jobj = models.Service.objects.exclude(status='offline')
                sobj = models.StaticService.objects.exclude(status='offline')
            except Exception as e:
                logger.error('查询动态应用和今天应用失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                tmp_dict = {}
                for jitem in jobj:
                    ip = [item[0] for item in jitem.host.values_list('ip')]
                    one_item_dict = {'service_name': jitem.service_name,
                         'type': jitem.type,
                         'service_port': jitem.service_port,
                         'status': jitem.status,
                         'ip': ip,
                         'project_name': jitem.project_name.project_name}
                    if jitem.project_name.project_name in tmp_dict.keys():
                        tmp_dict[jitem.project_name.project_name].append(one_item_dict)
                    else:
                         tmp_dict[jitem.project_name.project_name] = [one_item_dict]

                tmp_dict['静态资源项目'] = []
                for sitem in sobj:
                   sip = [item[0] for item in sitem.host.values_list('ip')]
                   tmp_dict['静态资源项目'].append({
                     'service_name': sitem.project_name,
                     'status': sitem.status,
                     'ip': sip
                   })

                return JsonResponse({'result': True, 'data': tmp_dict})
        else:
            return render(request, 'application-offline.html', {'role_name': self.role})

    def post(self, request):
        project_name = request.POST.get('project_name')
        service_name = request.POST.get('service_name')
        username = request.user.get_full_name()
        ip = request.POST.get('ip')
        # 验证是否有用户正在下线提交的项目，如果有则返回错误信息
        try:
            eobj = models.AppOffline.objects.filter(service_name=service_name)
        except Error as e:
            logger.error("验证是否有其他用户正在下线此项目发生异常，错误信息：%s" % json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            if eobj.exclude(username=username).exists():
                logger.error('其他用户正在下线%s项目不允许多用户操作同一个项目' %  service_name)
                return JsonResponse({'result': False, 'error_mess': '其他用户正在下线这个项目'})

        # 提交下线任务
        if project_name == '静态资源项目':
            if eobj.exists():
                logger.error('%s 项目不能重复执行下线操作' %service_name)
                return JsonResponse({'result': False, 'error_mess': '%s项目正在执行下线操作，不能重复提交任务' %service_name})
            else:
                try:
                    sobj = models.StaticService.objects.filter(project_name=service_name).values(
                        'target_code_path',
                        'host__ip',
                        'status',
                        'host__root_password',
                    )
                except Error as e:
                    logger.error('查询%s项目信息失败，错误信息：%s' % (service_name, json.dumps(e.args)))
                    return JsonResponse({'result': False, 'error_mess': '提交任务失败'})
                else:
                    tmp_list = []
                    for sone_item in sobj:
                        task_id = application_offline_tasks.application_offline.delay(
                            ip=sone_item['host__ip'],
                            target_path=sone_item['target_code_path'],
                            username='root',
                            password=sone_item['host__root_password'],
                            offline_type='static'
                        ).task_id
                        tmp_list.append({
                            'ip': sone_item['host__ip'],
                            'project_name': project_name,
                            'status': sone_item['status'],
                            'task_id': task_id
                        })
                    else:
                        try:
                            models.AppOffline.objects.create(
                                username=username,
                                service_name=service_name,
                                group_task_id=json.dumps(tmp_list)
                            )
                        except Error as e:
                            logger.error('提交%s task任务完成，插入信息记录到数据库失败错误信息：%s' % (json.dumps(tmp_list), json.dumps(e.args)))
                            return JsonResponse({'result': False, 'error_mess': 'task 任务已经提交完成，但是信息入库失败，错误信息：%s' % json.dumps(e.args)})
                        else:
                            return JsonResponse({'result': True})
        else:
            # 定义一个临时list 用户存在task id 信息
            tmp_list = []
            # 判断是否有批量下线同一个任务的，如果存在批量下线任务，批量下线不能和单独下线一个节点同时发生
            try:
                jobj = models.Service.objects.get(service_name=service_name)
            except Error as e:
                logger.error('查询%s 应用信息失败，错误信息：%s' % (service_name, json.dumps(e.args)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            if ip is None:
                if eobj.exists():
                    return JsonResponse({'result': False, 'error_mess': '有人正在操作该项目下线'})
                else:
                    ip_mess = jobj.host.all().values('ip', 'root_password')
                    for ip_obj in ip_mess:
                        task_id = application_offline_tasks.application_offline.delay(
                            offline_type='java',
                            ip=ip_obj['ip'],
                            username='root',
                            password=ip_obj['root_password'],
                            stop_script=jobj.stop_script,
                        ).task_id
                        tmp_list.append({
                            'ip': ip_obj['ip'],
                            'project_name': project_name,
                            'status': jobj.status,
                            'task_id': task_id,
                        })
                    else:
                        try:
                            models.AppOffline.objects.create(
                                username=username,
                                service_name=service_name,
                                group_task_id=json.dumps(tmp_list)
                            )
                        except Error as e:
                            logger.error('插入%s任务信息到AppOffline表失败,错误信息%s' % (json.dumps(tmp_list), json.dumps(e.args)))
                            return JsonResponse({'result': False, 'error_mess': '提交任务信息成功但是将信息插入数据库失败'})
                        else:
                            return JsonResponse({'result': True})
            else:
                for jone_item in eobj:
                    if jone_item.group_task_id != '':
                        return JsonResponse({'result': False, 'error_mess': '应用正在被其他用户下线'})
                    else:
                        tmp_json = json.loads(jone_item.task_id)
                        if tmp_json['ip'] == ip:
                            return JsonResponse({'result': False, 'error_mess': '当前节点正在被其他用户下线'})
                else:
                    task_id = application_offline_tasks.application_offline.delay(
                        offline_type='java',
                        ip=ip,
                        username='root',
                        password=jobj.host.get(ip=ip).root_password,
                        stop_script=jobj.stop_script
                    ).task_id
                    try:
                        models.AppOffline.objects.create(
                            username=username,
                            service_name=service_name,
                            task_id=json.dumps({
                                'ip': ip,
                                'project_name': project_name,
                                'status': jobj.status,
                                'task_id': task_id
                            })
                        )
                    except Error as e:
                        logger.error('任务提交完成，入库失败，错误信息：%s' % json.dumps(e.args))
                        return JsonResponse({'result': False, 'error_mess': '任务提交成功，入库失败'})
                    else:
                        return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class ApplicationOfflineQuery(View):
    def dispatch(self, request, *args, **kwargs):
        return super(ApplicationOfflineQuery, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        # 去查询所有的task 信息
        try:
            task_obj = models.AppOffline.objects.all()
        except Error as e:
            logger.error('查询下线任务task 信息失败，错误信息：%s' % json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': '获取task 任务信息失败'})
        # 遍历查询所有的task 条目，获取task信息任务是否完成，已经完成状态，封装返回给前端
        # 临时变量用于存放返回到前端的数据
        tmp_list = []
        for one_task in task_obj:
            if one_task.group_task_id == '' and one_task.task_id != '':
                # 判断是单节点下线
                task_mess = json.loads(one_task.task_id)
                task_result = query_task(task_mess['task_id'])
                # 判断task 任务执行成功且结果成功时，修改数据库里面记录
                if task_result['result'] == 'SUCCESS':
                    try:
                        sobj = models.Service.objects.get(service_name=one_task.service_name)
                        host_obj = models.Host.objects.get(ip=task_mess['ip'])
                        sobj.host.remove(host_obj)
                        if not sobj.host.all().exists():
                            sobj.status = 'offline'
                            sobj.save()
                            # 将Jenkins上项目状态改为禁用
                            try:
                                Mjenkins.disable_job(one_task.service_name)
                            except Exception as e:
                                logger.error('将Jenkins上的%s设置为disabled失败，错误无信息：%s' % (one_task.service_name, e.message))
                    except Error as e:
                        logger.error('%s节点下线成功，但是清理数据库信息失败错误信息%s' % (one_task.task_id, json.dumps(e.args)))
                # 判断task 成功或者失败时，删除task记录
                if task_result['result'] == 'SUCCESS' or task_result['result'] == 'FAILURE':
                    one_task.delete()
                # 追加此任务的结果到临时list
                tmp_list.append({
                    'project_name': task_mess['project_name'],
                    'service_name': one_task.service_name,
                    'status': task_mess['status'],
                    'ip': task_mess['ip'],
                    'username': one_task.username,
                    'result': task_result['result'],
                })
            else:
                # 批量节点下线
                group_task_mess = json.loads(one_task.group_task_id)
                offline_flag = True
                for item in group_task_mess:
                    task_result = query_task(item['task_id'])
                    if task_result['result'] != 'SUCCESS':
                        offline_flag = False
                    tmp_list.append({
                        'project_name': item['project_name'],
                        'service_name': one_task.service_name,
                        'status': item['status'],
                        'ip': item['ip'],
                        'username': one_task.username,
                        'result': task_result['result']
                    })
                else:
                    if offline_flag:
                        if item['project_name'] == '静态资源项目':
                            try:
                                models.StaticService.objects.filter(project_name=one_task.service_name).update(status='offline')
                                one_task.delete()
                            except Error as e:
                                logger.error('%s项目下线成功，但是修改数据库offline 状态失败，错误信息：%s' % (one_task.service_name, json.dumps(e.args)))
                        else:
                            try:
                                models.Service.objects.filter(service_name=one_task.service_name).update(status='offline')
                                one_task.delete()
                            except Error as e:
                                logger.error('任务已经下线成功，但是修改数据库的offline状态失败')
                        # 将Jenkins 应用状态设置问禁用状态
                        try:
                            Mjenkins.disable_job(one_task.service_name)
                        except Exception as e:
                            logger.error('将应用%s Jenkins状态设置为disabled失败，错误信息：%s' % (one_task.service_name, e.message))
        else:
            return JsonResponse({'result': True, 'data': tmp_list})







