#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/8/28 16:44
    @FileName: delploy.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
import json
import logging
import datetime
import time
import xlwt
import os
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
from devopsApp import models
from django.db import Error
from django.views.generic import View
from django.utils.decorators import method_decorator
from common.PermissonDecorator import permission_controller
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from jenkins import JenkinsException
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.db.models import Max, Min
from django.http import FileResponse
from common.k8sApply import k8s_apply
logger = logging.getLogger('django.request')


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class ModifyDeployTime(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(ModifyDeployTime, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            start_time = request.GET.get('start_time')
            end_time = request.GET.get('end_time')
            mtype = request.GET.get('mtype')
            try:
                models.DeployTimeControl.objects.filter(type=mtype).update(start_time=start_time, end_time=end_time)
            except Error, e:
                logging.error('更新项目发布时间失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True})
        else:
            try:
                d_obj = models.DeployTimeControl.objects.get(type='deploy')
            except Error, e:
                logger.error('查询发布时间失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                return render(request, 'base_error.html', {'error_mess': e.args})
            else:
                return render(request, 'deploy-modify-time.html', {'role': self.role, 'start_time': d_obj.start_time,
                                                                   'end_time': d_obj.end_time})


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class DeployManage(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(DeployManage, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            delpoy_date = request.GET.get('delpoy_date')
            try:
                obj = models.WorkOrderNeeds.objects.filter(deploy_time=delpoy_date).values('need_content')
            except Error, e:
                logger.error('查询%s当天发布的需求单失败,错误信息：%s' % (delpoy_date, json.dumps(e.args, ensure_ascii=False)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True, 'data': list(obj)})
        else:
            # 获取组长列表
            try:
                group_leader_obj = models.OnelevelLeader.objects.all().values('leadername')
                leader_obj = models.TwolevelLeader.objects.all().values('leadername')
            except Error, e:
                logger.error('查询领导数据表失败错误信息%s' % json.dumps(e.args, ensure_ascii=False))
                return render(request, 'base_error.html', {'error_mess': e.args})
            else:
                group_leader = [item['leadername'] for item in group_leader_obj]
                leader = [item['leadername'] for item in leader_obj]
                return render(request, 'deploy-apply.html', {'group_leader': group_leader, 'leader': leader, 'role': self.role})


@method_decorator(login_required, 'dispatch')
class OneleaderAgree(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(OneleaderAgree, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            need_date = request.GET.get('need_date')
            two_last_date = (datetime.datetime.now() + datetime.timedelta(days=-2)).date()
            if need_date:
                try:
                    ndate = models.WorkOrderNeeds.objects.filter(deploy_time__gte=two_last_date).values('deploy_time').distinct().order_by('-deploy_time').values_list('deploy_time')
                except Error, e:
                    logger.error('获取发布日期失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    ndate_list = [item[0].strftime('%Y-%m-%d') for item in ndate]
                    return JsonResponse({'result': True, 'data': ndate_list})
        else:
            try:
                group_leader_obj = models.OnelevelLeader.objects.all().values('leadername')
                leader_obj = models.TwolevelLeader.objects.all().values('leadername')
            except Error, e:
                logger.error('查询领导数据表失败错误信息%s' % json.dumps(e.args, ensure_ascii=False))
                return render(request, 'base_error.html', {'error_mess': e.args})
            else:
                group_leader = [item['leadername'] for item in group_leader_obj]
                leader = [item['leadername'] for item in leader_obj]
                return render(request, 'deploy-apply-groupleader-agree.html',
                              {'group_leader': group_leader, 'leader': leader, 'role': self.role})

    def post(self, request):
        ndate = request.POST.get('ndate')
        sp_status = request.POST.get('sp_status')
        username = request.user.get_full_name()
        if self.role == 'admin':
            if sp_status == '待审批':
                try:
                    order_obj = models.DeployProjectApply.objects.filter(groupleader_agree='',
                                                                         workorderneeds__deploy_time=ndate
                                                                         ).values(
                        'workorderneeds__deploy_time',
                        'workorderneeds__need_content',
                        'workorderneeds__product_manager_name',
                        'id',
                        'project_class',
                        'project_name',
                        'deploy_username',
                        'tamper_resistant_start_time',
                        'tamper_resistant_end_time',
                        'code_verify_name',
                        'developers_name',
                        'tester_name',
                        'db_op',
                        'operation_need_reasons',
                        'deploy_start_time',
                        'deploy_end_time',
                        'groupleader_agree'
                    )
                    leader = models.TwolevelLeader.objects.all().values('leadername')
                except Error, e:
                    logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    leader_list = list(leader)
                    tmp_list = []
                    for order_item in order_obj:
                        order_item['leader'] = leader_list
                        tmp_list.append(order_item)
                    return JsonResponse({'result': True, 'data': tmp_list})
            else:
                try:
                    order_obj = models.DeployProjectApply.objects.filter(
                                                                         workorderneeds__deploy_time=ndate
                                                                         ).exclude(groupleader_agree='').values(
                        'workorderneeds__deploy_time',
                        'workorderneeds__need_content',
                        'workorderneeds__product_manager_name',
                        'id',
                        'project_class',
                        'project_name',
                        'deploy_username',
                        'tamper_resistant_start_time',
                        'tamper_resistant_end_time',
                        'code_verify_name',
                        'developers_name',
                        'tester_name',
                        'db_op',
                        'operation_need_reasons',
                        'deploy_start_time',
                        'deploy_end_time',
                        'groupleader_agree',
                        'twolevelLeader_name'
                    )
                except Error, e:
                    logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True, 'data': list(order_obj)})
        else:
            if sp_status == '待审批':
                try:
                    order_obj = models.DeployProjectApply.objects.filter(groupleader_agree='',
                                                                         workorderneeds__deploy_time=ndate,
                                                                         groupleader_name=username
                                                                         ).values(
                        'workorderneeds__deploy_time',
                        'workorderneeds__need_content',
                        'workorderneeds__product_manager_name',
                        'id',
                        'project_class',
                        'project_name',
                        'deploy_username',
                        'tamper_resistant_start_time',
                        'tamper_resistant_end_time',
                        'code_verify_name',
                        'developers_name',
                        'tester_name',
                        'db_op',
                        'operation_need_reasons',
                        'deploy_start_time',
                        'deploy_end_time',
                        'groupleader_agree'
                    )
                    leader = models.TwolevelLeader.objects.filter(onelevelleader__leadername=username).values('leadername')
                except Error, e:
                    logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    leader_list = list(leader)
                    tmp_list = []
                    for order_item in order_obj:
                        order_item['leader'] = leader_list
                        tmp_list.append(order_item)
                    return JsonResponse({'result': True, 'data': tmp_list})
            else:
                try:
                    order_obj = models.DeployProjectApply.objects.filter(
                                                                         workorderneeds__deploy_time=ndate,
                                                                         groupleader_name=username
                                                                         ).exclude(groupleader_agree='').values(
                        'workorderneeds__deploy_time',
                        'workorderneeds__need_content',
                        'workorderneeds__product_manager_name',
                        'id',
                        'project_class',
                        'project_name',
                        'deploy_username',
                        'tamper_resistant_start_time',
                        'tamper_resistant_end_time',
                        'code_verify_name',
                        'developers_name',
                        'tester_name',
                        'db_op',
                        'operation_need_reasons',
                        'deploy_start_time',
                        'deploy_end_time',
                        'groupleader_agree',
                        'twolevelLeader_name'
                    )
                except Error, e:
                    logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True, 'data': list(order_obj)})


@method_decorator(login_required, 'dispatch')
class OneleaderIfAgreePost(View):
    def dispatch(self, request, *args, **kwargs):
        return super(OneleaderIfAgreePost, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        order_id = request.POST.get('id')
        two_leader = request.POST.get('two_leader')
        groupleader_agree = request.POST.get('groupleader_agree')
        try:
            models.DeployProjectApply.objects.filter(id=order_id).update(twolevelLeader_name=two_leader, groupleader_agree=groupleader_agree)
        except Error, e:
            logger.error('更新DeployProjectApply表失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class GetDeployMess(View):
    def dispatch(self, request, *args, **kwargs):
        return super(GetDeployMess, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        try:
            # 组长信息
            one_leader_obj = models.OnelevelLeader.objects.all().values('leadername')
            # 获取项目归属
            project_class_obj = models.Project.objects.all().values('project_name')
        except Error, e:
            logger.error('查询组长信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            one_leader_list = [item['leadername'] for item in one_leader_obj]
            project_class_list = [item['project_name'] for item in project_class_obj]
            try:
                from common.Mjenkins import Mjenkins
            except Exception, e:
                logger.error('导入jenkin 链接失败错误信息：%s' % e.message)
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 获取微信项目信息
            data = {}
            weixin_static = [item['name'] for item in Mjenkins.get_jobs(view_name='静态资源发布')]
            weixin_java = [item['name'] for item in Mjenkins.get_jobs(view_name='java项目发布')]
            for pitem in project_class_list:
                if pitem == '微信项目':
                  data[pitem] = {
                      'java项目': weixin_java,
                      '静态项目': weixin_static
                  }
                else:
                    try:
                        tmp_list = [item['name'] for item in Mjenkins.get_jobs(view_name=pitem)]
                    except JenkinsException, e:
                        logger.error('查询%s 视图失败，错误信息:%s' % (pitem, e.message))
                        tmp_list = []
                    java_tmp_list = filter(lambda p: not p.endswith('-static'), tmp_list)
                    static_tmp_list = filter(lambda p: p.endswith('-static'), tmp_list)
                    data[pitem] = {
                        'java项目': java_tmp_list,
                        '静态项目': static_tmp_list
                    }
            else:
                return JsonResponse({'result': True, 'data': data, 'oneleader': one_leader_list})


@method_decorator(login_required, 'dispatch')
class InsertDeployOrder(View):
    def dispatch(self, request, *args, **kwargs):
        return super(InsertDeployOrder, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.POST.get('data'))
            username = request.user.get_full_name()
        except Exception, e:
            logger.error('提交发布上线单接口参数失败，错误信息：%s' %e.message)
            return JsonResponse({'result': False, 'error_mess': e.message})
        try:
                need_obj = models.WorkOrderNeeds.objects.get(deploy_time=data['need']['deploy_time'], need_content=data['need']['need_content'])
        except ObjectDoesNotExist, e:
                if data['need']['product_manager_name'] == '':
                    data['need']['product_manager_name'] = username
                need_obj = models.WorkOrderNeeds.objects.create(**data['need'])
        except Error, e:
            logger.error('插入需求表单失败，错误信息：%s' %json.dumps(e.args, ensure_ascii=False))
            return JsonResponse({'result': False, 'error_mess': e.args})

        for item in data['order']:
            try:
                order_obj = models.DeployProjectApply.objects.create(
                    deploy_username=username,
                    **item
                )
                # 加判断，如果检查到项目为测试环境的项目，在这里自动给审批掉，不需要在页面审批
                if item['project_name'].__contains__('-test'):
                    order_obj.groupleader_agree = '同意'
                    order_obj.twolevelLeader_agree = '同意'
                    order_obj.save()
            except Error, e:
                logger.error('插入需求表单失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                need_obj.need_deploy_project.add(order_obj)
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class TwoleaderAgree(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(TwoleaderAgree, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            need_date = request.GET.get('need_date')
            two_last_date = (datetime.datetime.now() + datetime.timedelta(days=-2)).date()
            if need_date:
                try:
                    ndate = models.WorkOrderNeeds.objects.filter(deploy_time__gte=two_last_date).values('deploy_time').distinct().order_by('-deploy_time').values_list('deploy_time')
                except Error, e:
                    logger.error('获取发布日期失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    ndate_list = [item[0].strftime('%Y-%m-%d') for item in ndate]
                    return JsonResponse({'result': True, 'data': ndate_list})
        else:
            try:
                group_leader_obj = models.OnelevelLeader.objects.all().values('leadername')
                leader_obj = models.TwolevelLeader.objects.all().values('leadername')
            except Error, e:
                logger.error('查询领导数据表失败错误信息%s' % json.dumps(e.args, ensure_ascii=False))
                return render(request, 'base_error.html', {'error_mess': e.args})
            else:
                group_leader = [item['leadername'] for item in group_leader_obj]
                leader = [item['leadername'] for item in leader_obj]
                return render(request, 'deploy-apply-leader-agree.html',
                              {'group_leader': group_leader, 'leader': leader, 'role': self.role})

    def post(self, request):
        ndate = request.POST.get('ndate')
        sp_status = request.POST.get('sp_status')
        username = request.user.get_full_name()
        if self.role == 'admin':
            if sp_status == '待审批':
                try:
                    order_obj = models.DeployProjectApply.objects.filter(twolevelLeader_agree='',
                                                                         workorderneeds__deploy_time=ndate,
                                                                         groupleader_agree='同意'
                                                                         ).values(
                        'workorderneeds__deploy_time',
                        'workorderneeds__need_content',
                        'workorderneeds__product_manager_name',
                        'id',
                        'project_class',
                        'project_name',
                        'deploy_username',
                        'tamper_resistant_start_time',
                        'tamper_resistant_end_time',
                        'code_verify_name',
                        'developers_name',
                        'tester_name',
                        'db_op',
                        'operation_need_reasons',
                        'deploy_start_time',
                        'deploy_end_time',
                        'groupleader_agree',
                        'twolevelLeader_agree'
                    )
                except Error, e:
                    logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True, 'data': list(order_obj)})
            else:
                try:
                    order_obj = models.DeployProjectApply.objects.filter(
                                                                         workorderneeds__deploy_time=ndate,
                                                                         groupleader_agree='同意',
                                                                         ).exclude(twolevelLeader_agree='').values(
                        'workorderneeds__deploy_time',
                        'workorderneeds__need_content',
                        'workorderneeds__product_manager_name',
                        'id',
                        'project_class',
                        'project_name',
                        'deploy_username',
                        'tamper_resistant_start_time',
                        'tamper_resistant_end_time',
                        'code_verify_name',
                        'developers_name',
                        'tester_name',
                        'db_op',
                        'operation_need_reasons',
                        'deploy_start_time',
                        'deploy_end_time',
                        'groupleader_agree',
                        'twolevelLeader_name',
                        'twolevelLeader_agree'
                    )
                except Error, e:
                    logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True, 'data': list(order_obj)})
        else:
            if sp_status == '待审批':
                try:
                    order_obj = models.DeployProjectApply.objects.filter(twolevelLeader_agree='',
                                                                         workorderneeds__deploy_time=ndate,
                                                                         twolevelLeader_name=username,
                                                                         groupleader_agree='同意'
                                                                         ).values(
                        'workorderneeds__deploy_time',
                        'workorderneeds__need_content',
                        'workorderneeds__product_manager_name',
                        'id',
                        'project_class',
                        'project_name',
                        'deploy_username',
                        'tamper_resistant_start_time',
                        'tamper_resistant_end_time',
                        'code_verify_name',
                        'developers_name',
                        'tester_name',
                        'db_op',
                        'operation_need_reasons',
                        'deploy_start_time',
                        'deploy_end_time',
                        'groupleader_agree',
                        'twolevelLeader_agree'
                    )
                except Error, e:
                    logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True, 'data': list(order_obj)})
            else:
                try:
                    order_obj = models.DeployProjectApply.objects.filter(groupleader_agree='同意',
                                                                         workorderneeds__deploy_time=ndate,
                                                                         twolevelLeader_name=username
                                                                         ).exclude(twolevelLeader_agree='').values(
                        'workorderneeds__deploy_time',
                        'workorderneeds__need_content',
                        'workorderneeds__product_manager_name',
                        'id',
                        'project_class',
                        'project_name',
                        'deploy_username',
                        'tamper_resistant_start_time',
                        'tamper_resistant_end_time',
                        'code_verify_name',
                        'developers_name',
                        'tester_name',
                        'db_op',
                        'operation_need_reasons',
                        'deploy_start_time',
                        'deploy_end_time',
                        'groupleader_agree',
                        'twolevelLeader_name',
                        'twolevelLeader_agree'
                    )
                except Error, e:
                    logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True, 'data': list(order_obj)})


@method_decorator(login_required, 'dispatch')
class TwoleaderIfAgreePost(View):
    def dispatch(self, request, *args, **kwargs):
        return super(TwoleaderIfAgreePost, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        order_id = request.POST.get('id')
        twoleader_agree = request.POST.get('twoleader_agree')
        try:
            models.DeployProjectApply.objects.filter(id=order_id).update(twolevelLeader_agree=twoleader_agree)
        except Error, e:
            logger.error('更新DeployProjectApply表失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class DeployProject(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(DeployProject, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            need_date = request.GET.get('need_date')
            two_last_date = (datetime.datetime.now() + datetime.timedelta(days=-7)).date()
            if need_date:
                try:
                    ndate = models.WorkOrderNeeds.objects.filter(deploy_time__gte=two_last_date).values('deploy_time').distinct().order_by('-deploy_time').values_list('deploy_time')
                except Error, e:
                    logger.error('获取发布日期失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    ndate_list = [item[0].strftime('%Y-%m-%d') for item in ndate]
                    return JsonResponse({'result': True, 'data': ndate_list})
        else:
            try:
                group_leader_obj = models.OnelevelLeader.objects.all().values('leadername')
                leader_obj = models.TwolevelLeader.objects.all().values('leadername')
            except Error, e:
                logger.error('查询领导数据表失败错误信息%s' % json.dumps(e.args, ensure_ascii=False))
                return render(request, 'base_error.html', {'error_mess': e.args})
            else:
                group_leader = [item['leadername'] for item in group_leader_obj]
                leader = [item['leadername'] for item in leader_obj]
                return render(request, 'deploy.html',
                              {'group_leader': group_leader, 'leader': leader, 'role': self.role})

    def post(self, request):
        ndate = request.POST.get('need_date')
        username = request.user.get_full_name()
        # 用于判断发布的环境，当env = test时，时测试环境，当env 为None表示生产环境这样就不用动生产环境发布的前端代码了
        env = request.POST.get('env')
        if ndate is None:
            return JsonResponse({'result': True, 'data': []})
        else:
            if env == 'test':
                if self.role == 'admin':
                    try:
                        order_obj = models.DeployProjectApply.objects.filter(
                            workorderneeds__deploy_time=ndate,
                            project_name__contains="-test"
                        ).values(
                            'workorderneeds__deploy_time',
                            'workorderneeds__need_content',
                            'workorderneeds__product_manager_name',
                            'id',
                            'project_class',
                            'project_name',
                            'deploy_username',
                            'tamper_resistant_start_time',
                            'tamper_resistant_end_time',
                            'code_verify_name',
                            'developers_name',
                            'tester_name',
                            'db_op',
                            'operation_need_reasons',
                            'deploy_start_time',
                            'deploy_end_time',
                            'groupleader_name',
                            'groupleader_agree',
                            'twolevelLeader_name',
                            'twolevelLeader_agree',
                            'really_deploy_time',
                            'deploy_result',
                            'build_id'
                        )
                    except Error, e:
                        logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                        return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    try:
                        order_obj = models.DeployProjectApply.objects.filter(
                            workorderneeds__deploy_time=ndate,
                            deploy_username=username,
                            project_name__contains="-test"
                        ).values(
                            'workorderneeds__deploy_time',
                            'workorderneeds__need_content',
                            'workorderneeds__product_manager_name',
                            'id',
                            'project_class',
                            'project_name',
                            'deploy_username',
                            'tamper_resistant_start_time',
                            'tamper_resistant_end_time',
                            'code_verify_name',
                            'developers_name',
                            'tester_name',
                            'db_op',
                            'operation_need_reasons',
                            'deploy_start_time',
                            'deploy_end_time',
                            'groupleader_name',
                            'groupleader_agree',
                            'twolevelLeader_name',
                            'twolevelLeader_agree',
                            'really_deploy_time',
                            'deploy_result',
                            'build_id'
                        )
                    except Error, e:
                        logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                        return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                if self.role == 'admin':
                    try:
                        order_obj = models.DeployProjectApply.objects.exclude(
                            project_name__contains='-test'
                        ).filter(
                            workorderneeds__deploy_time=ndate,
                        ).values(
                            'workorderneeds__deploy_time',
                            'workorderneeds__need_content',
                            'workorderneeds__product_manager_name',
                            'id',
                            'project_class',
                            'project_name',
                            'deploy_username',
                            'tamper_resistant_start_time',
                            'tamper_resistant_end_time',
                            'code_verify_name',
                            'developers_name',
                            'tester_name',
                            'db_op',
                            'operation_need_reasons',
                            'deploy_start_time',
                            'deploy_end_time',
                            'groupleader_name',
                            'groupleader_agree',
                            'twolevelLeader_name',
                            'twolevelLeader_agree',
                            'really_deploy_time',
                            'deploy_result',
                            'build_id'
                        )
                    except Error, e:
                        logger.error('查询发布工单信息失败错误信息：%s' %json.dumps(e.args, ensure_ascii=False))
                        return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    try:
                        order_obj = models.DeployProjectApply.objects.exclude(
                            project_name__contains='-test'
                        ).filter(
                            workorderneeds__deploy_time=ndate,
                            deploy_username=username
                        ).values(
                            'workorderneeds__deploy_time',
                            'workorderneeds__need_content',
                            'workorderneeds__product_manager_name',
                            'id',
                            'project_class',
                            'project_name',
                            'deploy_username',
                            'tamper_resistant_start_time',
                            'tamper_resistant_end_time',
                            'code_verify_name',
                            'developers_name',
                            'tester_name',
                            'db_op',
                            'operation_need_reasons',
                            'deploy_start_time',
                            'deploy_end_time',
                            'groupleader_name',
                            'groupleader_agree',
                            'twolevelLeader_name',
                            'twolevelLeader_agree',
                            'really_deploy_time',
                            'deploy_result',
                            'build_id'
                        )
                    except Error, e:
                        logger.error('查询发布工单信息失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                        return JsonResponse({'result': False, 'error_mess': e.args})
            # 检查 jenkins结果
            tmp_list = []
            try:
                from common.Mjenkins import Mjenkins
            except Exception, e:
                logger.error('导入jenkins初始化模块失败，错误信息：%s' % e.message)
                return JsonResponse({'result': False, 'error_mess': '链接jenkins api失败'})
            else:
                for item in order_obj:
                    if item['build_id'] > 0 and item['deploy_result'] == "":
                        deploy_result = ''
                        try:
                            console_res = Mjenkins.get_build_console_output(item['project_name'], item['build_id'])
                        except Exception, e:
                            logger.error('%s build_id:%s 错误：%s' % (item['project_name'], item['build_id'], e.message))
                            deploy_result='未知'
                            try:
                                models.DeployProjectApply.objects.filter(id=item['id']).update(
                                    deploy_result=deploy_result,
                                    result=e.message
                                )
                            except Error, e:
                                logger.error('修改deploy jobs信息失败：%s' % json.dumps(e.args,ensure_ascii=False))
                                return JsonResponse({'result': False, 'error_mess': e.args})
                        else:
                            if console_res.__contains__('Finished: FAILURE'):
                                deploy_result = '失败'
                            if console_res.__contains__('Finished: SUCCESS'):
                                deploy_result = '成功'
                            # 判断项目是否为docker项目
                            try:
                                k8s_obj = models.K8sApp.objects.filter(service_name=item['project_name'])
                            except Exception as e:
                                logger.error("发布项目时候，查询K8sApp表判断项目是否为k8s项目失败,发布信息:%s,错误信息:%s" %(item['project_name'], json.dump(e.args, ensure_ascii=False)))
                            else:
                                if k8s_obj.exists():
                                    # 删除Jenkins 发布时候插入数据库的标志数据
                                    try:
                                        models.JenkinsDeploy.objects.filter(deploy_project=item['project_name']).delete()
                                    except Exception as e:
                                        logger.error("k8s项目发布完成，删除JenkinsDeploy表%s项目信息失败，错误信息：%s" %(item['project_name'], json.dumps(e.args, ensure_ascii=False)))
                                    # k8s项目调用Jenkins发布只是build出来docker镜像，这里需要kubect apply 一下配置信息
                                    if deploy_result == '成功':
                                        k8s_deploy_mes = k8s_obj.values('latest_image', 'deploy_yaml')[0]
                                        image_tag = k8s_deploy_mes['latest_image']
                                        deploy_yaml = k8s_deploy_mes['deploy_yaml']
                                        result = k8s_apply(image_tag,deploy_yaml)
                                        logger.info("kubectl apply 结果：%s" %json.dumps(result))
                                        if result[0] is False:
                                            console_res = console_res + '</br>kubectl apply 失败信息：' + result[1]
                                            deploy_result = '失败'
                            if deploy_result != '':
                                try:
                                    models.DeployProjectApply.objects.filter(id=item['id']).update(
                                        deploy_result=deploy_result,
                                        result=console_res.replace('\n', '</br>')
                                    )
                                except Error, e:
                                    logger.error('修改deploy jobs信息失败：%s' % json.dumps(e.args, ensure_ascii=False))
                                    return JsonResponse({'result': False, 'error_mess': e.args})
                                else:
                                    item['deploy_result'] = deploy_result
                    tmp_list.append(item)
                else:
                    return JsonResponse({'result': True, 'data': tmp_list})


@method_decorator(login_required, 'dispatch')
class DeployProjectTest(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(DeployProjectTest, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            need_date = request.GET.get('need_date')
            two_last_date = (datetime.datetime.now() + datetime.timedelta(days=-7)).date()
            if need_date:
                try:
                    ndate = models.WorkOrderNeeds.objects.filter(deploy_time__gte=two_last_date).values('deploy_time').distinct().order_by('-deploy_time').values_list('deploy_time')
                except Error, e:
                    logger.error('获取发布日期失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    ndate_list = [item[0].strftime('%Y-%m-%d') for item in ndate]
                    return JsonResponse({'result': True, 'data': ndate_list})
        else:
            try:
                group_leader_obj = models.OnelevelLeader.objects.all().values('leadername')
                leader_obj = models.TwolevelLeader.objects.all().values('leadername')
            except Error, e:
                logger.error('查询领导数据表失败错误信息%s' % json.dumps(e.args, ensure_ascii=False))
                return render(request, 'base_error.html', {'error_mess': e.args})
            else:
                group_leader = [item['leadername'] for item in group_leader_obj]
                leader = [item['leadername'] for item in leader_obj]
                return render(request, 'deploy-test.html',
                              {'group_leader': group_leader, 'leader': leader, 'role': self.role})


@method_decorator(login_required, 'dispatch')
class SubmitDeployJob(View):
    def dispatch(self, request, *args, **kwargs):
        return super(SubmitDeployJob, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        total_jenkins_jobs = 10
        job_id = request.POST.get('id')
        jenkins_job_name = request.POST.get('job_name')
        env = request.POST.get('env')
        try:
            from common.Mjenkins import Mjenkins
        except Exception, e:
            logger.error('导入jenkins初始化模块失败，错误信息：%s' % e.message)
            return JsonResponse({'result': False, 'error_mess': 'jobs 提交失败'})
        else:
            current_runing_jobs = len(Mjenkins.get_running_builds())
            if current_runing_jobs > (total_jenkins_jobs/2):
                return JsonResponse({'result': False, 'error_mess': '当前jenkins发布任务比较多，请等待一会在发布'})
            else:
                # 判断项目是否在发布时间范围内,如果时测试环境不用判断发布时间，可以自由发布
                if env == 'test':
                    # 不做任何时间控制
                    pass
                else:
                    # 这里时生产环境发布时间管控判断
                    try:
                        global_control_time_obj = models.DeployTimeControl.objects.get(type='deploy')
                        one_project_control_time_obj = models.DeployProjectApply.objects.get(id=job_id)
                    except Error, e:
                        logger.error('查询全局控制发布时间表失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                        return JsonResponse({'result': False, 'error_mess': '校验是否在发布时间范围内失败'})
                    else:
                        golabl_control_start_time = global_control_time_obj.start_time
                        golabl_control_end_time = global_control_time_obj.end_time
                        one_project_control_start_time = one_project_control_time_obj.deploy_start_time
                        one_project_control_end_time = one_project_control_time_obj.deploy_end_time
                        current_time = datetime.datetime.now()
                        if (current_time - golabl_control_start_time).days >=0 and (current_time - one_project_control_start_time).days >=0 and (golabl_control_end_time - current_time).days >=0 and (one_project_control_end_time - current_time).days >=0:
                            pass
                        else:
                            return JsonResponse({'result': False, 'error_mess': '项目不再发布时间范围内'})
                queue_id = Mjenkins.build_job(jenkins_job_name)
                while True:
                    if 'executable' not in Mjenkins.get_queue_item(queue_id).keys():
                        time.sleep(1)
                    else:
                        build_id = Mjenkins.get_queue_item(queue_id)['executable']['number']
                        break
                try:
                    models.DeployProjectApply.objects.filter(id=job_id).update(build_id=build_id, really_deploy_time=datetime.datetime.now(), deploy_result="")
                except Error, e:
                    logger.error('更新%sjenkins发布的build_id %s失败，错误信息：%s' % (jenkins_job_name, build_id, json.dumps(e.args, ensure_ascii=False)))
                    return JsonResponse({'result': False, 'error_mess': '更新%s的jenkins build id失败'})
                else:
                    return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class QueryJobsResult(View):
    def dispatch(self, request, *args, **kwargs):
        return super(QueryJobsResult, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        query_id = request.GET.get('id')
        try:
            obj = models.DeployProjectApply.objects.get(id=query_id)
        except Error, e:
            logger.error('查询%s发布结果失败错误信息:%s' %(query_id, json.dumps(e.args, ensure_ascii=False)))
            return JsonResponse({'result': False, 'data': e.args})
        else:
            return JsonResponse({'result': True, 'data': obj.result})


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class DeployOrderDownload(View):
    def dispatch(self, request, *args, **kwargs):
        return super(DeployOrderDownload, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                ndate = models.WorkOrderNeeds.objects.filter(deploy_time__gte=(datetime.datetime.today()-datetime.timedelta(days=30)).date()).distinct().order_by('-deploy_time').values_list('deploy_time')
            except Error, e:
                logger.error('查询上线单日期信息失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True, 'data': [item[0].strftime('%Y-%m-%d') for item in ndate]})
        else:
            ndate = request.GET.get('ndate')
            if ndate is None:
                return render(request, 'deploy-applyorder-download.html')
            else:
                filename = os.path.join(settings.BASE_DIR, 'execl', 'deploy_apply', '%s.xls' % ndate)
                fp = open(filename, 'rb')
                response = FileResponse(fp)
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = 'attachment;filename="%s.xls"' % ndate
                return response

    def post(self, request):
        ndate = request.POST.get('ndate')
        order_op_type = request.POST.get('op_type')
        filename = os.path.join(settings.BASE_DIR, 'execl', 'deploy_apply', '%s.xls' % ndate)
        if order_op_type == 'product':
            try:
                logo = os.path.join(settings.BASE_DIR, 'execl', 'deploy_apply', 'logo.bmp')
                objs = models.WorkOrderNeeds.objects.exclude(need_deploy_project__project_class="智慧社区测试").filter(deploy_time=ndate)
                wb = xlwt.Workbook(encoding='gbk')
                ws = wb.add_sheet("需求表单")
                ws1 = wb.add_sheet('版本信息')
                # 生成需求表单sheet
                stye = xlwt.easyxf('font: name 宋体, height 200; Borders: left THIN,right THIN,top THIN,bottom THIN; align: wrap on, vert centre, horiz center')
                ws.write_merge(0, 2, 0, 8, "项目版本发布信息", xlwt.easyxf('font: name 宋体, bold on, height 351; Borders: left THIN,right THIN,top THIN,bottom THIN; align: wrap on, vert centre, horiz center'))
                ws.insert_bitmap(logo, 0, 0)
                ws.write_merge(3, 3, 0, 1, '部署环境', stye)
                ws.write_merge(3, 3, 2, 4, '生产环境', stye)
                ws.write_merge(3, 3, 5, 6, '计划部署时间', stye)
                ws.write_merge(3, 3, 7, 8, ndate, stye)
                need_high = len(objs) * 3
                ws.write_merge(4, 3 + need_high, 0, 1, '版本发布摘要', stye)
                row = 3
                for item in objs:
                    row = row + 1
                    mrow = row + 2
                    ws.write_merge(row, mrow, 2, 8, '%s \n\n 产品经理：%s    发布确认：' % (item.need_content.strip().replace('\n',''), item.product_manager_name), stye)
                    row = mrow
                # 生成版本信息sheet
                ws1.write_merge(0, 0, 0, 10, '版本信息', xlwt.easyxf('font: name 宋体, bold on, height 351; Borders: left THIN,right THIN,top THIN,bottom THIN; align: wrap on, vert centre, horiz center'))
                ws_row = 1
                flag = 1
                one_flag = 1
                for obj_item in objs:
                    ws_row_m = ws_row + len(obj_item.need_deploy_project.all().exclude(groupleader_agree='不同意'))
                    ws1.write_merge(ws_row, ws_row_m, 0, 0, flag, stye)
                    ws1.write_merge(one_flag, one_flag, 1, 10, '需求： %s' % obj_item.need_content, xlwt.easyxf('font: name 宋体, bold on, height 200; Borders: left THIN,right THIN,top THIN,bottom THIN'))
                    one_flag += 1
                    for one_project_obj in obj_item.need_deploy_project.all().exclude(groupleader_agree='不同意'):
                        ws1.write_merge(one_flag, one_flag, 1, 10, '%s 发布:%s 研发:%s 测试:%s 代码审核:%s' % (one_project_obj.project_name, one_project_obj.deploy_username, one_project_obj.developers_name,one_project_obj.tester_name,one_project_obj.code_verify_name), stye)
                        one_flag += 1
                    ws_row = ws_row_m + 1
                    flag += 1
                else:
                    ws1.col(0).width = 256 * 3

                # 生成审批sheet
                # objs.all().values('need_deploy_project__tamper_resistant_start_time')
                # 查找防篡改时间
                start_time = objs.all().aggregate(Min('need_deploy_project__tamper_resistant_start_time'))['need_deploy_project__tamper_resistant_start_time__min']
                end_time = objs.all().aggregate(Max('need_deploy_project__tamper_resistant_end_time'))['need_deploy_project__tamper_resistant_end_time__max']
                tamper_flag = '否'
                if start_time is None or end_time is None:
                    tamper = "关闭时间段:"
                else:
                    tamper_flag = '是'
                    tamper = '关闭时间段：%s ~ %s' % (start_time.strftime('%Y-%m-%d %H:%M:%S'), end_time.strftime('%Y-%m-%d %H:%M:%S'))
                ws1.write_merge(ws_row, ws_row, 0, 1, "网页防篡改", stye)
                ws1.write_merge(ws_row, ws_row, 2, 2, "是否关闭", stye)
                ws1.write_merge(ws_row, ws_row, 3, 3, tamper_flag, stye)
                ws1.write_merge(ws_row, ws_row, 4, 10, tamper, stye)
                ws1.write_merge(ws_row+1, ws_row+4, 0, 1, '领导签字', stye)
                ws1.write_merge(ws_row+1, ws_row+4, 2, 10, '', stye)
                ws1.write_merge(ws_row+5, ws_row+8, 0, 1, '测试结果', stye)
                ws1.write_merge(ws_row+5, ws_row+8, 2, 10, '', stye)
                wb.save(filename)
            except Exception, e:
                logger.error('生成上线申请单失败，错误信息：%s' %json.dumps(e.message, ensure_ascii=False))
                return JsonResponse({'result': False})
            else:
                return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class NeedOrderModify(View):
    def dispatch(self, request, *args, **kwargs):
        return super(NeedOrderModify, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        ndate = request.GET.get('ndate')
        try:
            obj = models.WorkOrderNeeds.objects.filter(deploy_time=ndate)
            obj_data = obj.values(
                'id',
                'need_content',
                'product_manager_name',
                'need_deploy_project__id',
                'need_deploy_project__tamper_resistant_start_time',
                'need_deploy_project__tamper_resistant_end_time',
                'need_deploy_project__deploy_start_time',
                'need_deploy_project__deploy_end_time',
                'need_deploy_project__project_class',
                'need_deploy_project__project_name',
                'need_deploy_project__deploy_username',
                'need_deploy_project__code_verify_name',
                'need_deploy_project__developers_name',
                'need_deploy_project__tester_name',
            )
            obj_ndata = obj.values(
                'id',
                'need_content'
            )
        except Error, e:
            logger.error('查询workorderneeds表报错，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True, 'data': list(obj_data), 'ndata': list(obj_ndata)})

    def post(self, request):
        nop = request.POST.get('nop')
        op_type = request.POST.get('op_type')
        if nop:
            nid = request.POST.get('nid')
            if op_type == 'delete':
                try:
                    obj = models.WorkOrderNeeds.objects.get(id=nid)
                except Error, e:
                    logger.error('获取workorderneeds表对象失败，错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    try:
                        obj.need_deploy_project.all().delete()
                        obj.delete()
                    except Error, e:
                        logger.error('执行删除order 和needs 失败错误信息：%s' % json.dumps(e.args, ensure_ascii=False))
                        return JsonResponse({'result': False, 'error_mess': e.args})
                    else:
                        return JsonResponse({'result': True})
        else:
            oid = request.POST.get('oid')
            if op_type == 'delete':
                try:
                    models.DeployProjectApply.objects.get(id=oid).delete()
                except Error, e:
                    logger.error('删除DeployProjectApply表id为%s得项目失败，错误信息：%s' % (oid, json.dumps(e.args, ensure_ascii=False)))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True})
            elif op_type == 'update':
                try:
                    models.DeployProjectApply.objects.filter(id=oid, project_name=request.POST.get('oname')).update(
                        tester_name=request.POST.get('tester'),
                        code_verify_name=request.POST.get('coder'),
                        developers_name=request.POST.get('developer'),
                        tamper_resistant_start_time=request.POST.get('tstart_time') if request.POST.get('tstart_time') else None,
                        tamper_resistant_end_time=request.POST.get('tend_time') if request.POST.get('tend_time') else None,
                        deploy_start_time=request.POST.get('dstart_time'),
                        deploy_end_time=request.POST.get('dend_time')
                    )
                except Error, e:
                    logger.error('修改id:%s %s项目失败，错误信息：%s' % (oid,request.POST.get('oname'), json.dumps(e.args, ensure_ascii=False)))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class DeployJenkinsLock(View):

    def dispatch(self, request, *args, **kwargs):
        return super(DeployJenkinsLock, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            try:
                obj = models.JenkinsDeploy.objects.filter().values(
                    'id',
                    'deploy_project'
                )
            except Error as e:
                logger.error('获取JenkinsDeploy数据失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True, 'data': list(obj)})

        else:
            return render(request, 'jenkinsLock.html')

    def post(self, request):
        nid = request.POST.get('nid')
        if nid is not None:
            try:
                models.JenkinsDeploy.objects.get(id=nid).delete()
            except Exception as e:
                logger.error("删除JenkinsDeploy id 为%s失败错误信息：%s" % (nid, json.dumps(e.args, ensure_ascii=False)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True})
        else:
            return JsonResponse({'result': False, "error_mess": "缺少参数"})






