#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2020/4/21 19:47 
# @Author : 吕秀刚
# @File : dbMange.py
from __future__ import unicode_literals
import json
import re
import logging
import datetime
import MySQLdb as mysql
import cx_Oracle
from devopsApp import models
from django.utils.decorators import method_decorator
from common.PermissonDecorator import permission_controller
from django.contrib.auth.decorators import login_required
from django.views.generic import View
from django.db import Error
from django.db.models import Q
from django.shortcuts import render
from django.http import JsonResponse
from common.oracle_schema import oracle_schema_dict
from Opsys.settings import dbmonitor
logger = logging.getLogger('django.request')


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class DBMange(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(DBMange, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        # 判断是否为ajax请求
        if request.is_ajax():
            # 如果是ajax 请求返回数据库的想象信息
            try:
                cluster_obj = models.DbClusterInfo.objects.all()
            except Error as e:
                logger.error("查询数据集群信息失败,错误信息:%s" %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 定义一个用于存放返回集群数据的list
            data = []
            # 获取集群对应的节点信息
            for cluster_item in cluster_obj:
                tmp_dict = {
                        "cluster_name": cluster_item.cluster_name,
                        "version": cluster_item.version,
                        "db_type": cluster_item.db_type,
                        "service_name": cluster_item.service_name,
                        "node":[]
                    }
                # 判断集群节点地址是否已经添加入库
                if cluster_item.dbnodeinfo_set.exists():
                    # 判断存在节点，获取到节点的信息
                    try:
                        node_obj = cluster_item.dbnodeinfo_set.all()
                    except Error as e:
                        logger.error("查询数据库节点信息失败，错误信息：%s" %json.dumps(e.args))
                        data.append(tmp_dict)
                    # 成功获取到节点信息对象
                    for node_item in node_obj:
                        tmp_dict['node'].append({
                            'host_ip': node_item.host_ip,
                            'conf_path': node_item.conf_path,
                            'base_path': node_item.base_path,
                            'service_port': node_item.service_port,
                            'role': node_item.role
                        })
                    else:
                        data.append(tmp_dict)
                else:
                    data.append(tmp_dict)
            else:
                # 返回最终结果
                return JsonResponse({'result': True, 'data': data})
        else:
            return render(request, 'MysqlMange.html', {'role_name': self.role})

    def post(self, request):
        method = request.POST.get('method')
        cluster_name = request.POST.get('cluster_name')
        if method == 'cluster':
            version = request.POST.get("version")
            db_type = request.POST.get("db_type")
            service_name = request.POST.get("service_name")
            username = request.POST.get("username")
            password = request.POST.get("password")
            if db_type == 'oracle' and not service_name:
                return JsonResponse({'result': False, 'error_mess': 'oracle 类型数据service_name 必填'})
            # 入库操作
            try:
                models.DbClusterInfo.objects.create(
                    cluster_name=cluster_name,
                    version=version,
                    db_type=db_type,
                    service_name=service_name,
                    username=username,
                    password=password
                )
            except Error as e:
                logger.error("插入集群信息数据到DbClusterInfo表失败，错误信息：%s" %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True})
        elif method == 'node':
            host_ip = request.POST.get('host_ip')
            conf_path = request.POST.get('conf_path')
            base_path = request.POST.get('base_path')
            service_port = request.POST.get('service_port')
            role = request.POST.get('role')
            try:
                node_obj = models.DbNodeInfo.objects.create(
                    host_ip=host_ip,
                    conf_path=conf_path,
                    base_path=base_path,
                    service_port=service_port,
                    role=role,
                    cluster_name=models.DbClusterInfo.objects.get(cluster_name=cluster_name)
                )
            except Error as e:
                logger.error("数据插入到DbNodeInfo表失败，错误信息：%s" %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True})
        elif method == 'del_node':
            host_ip = request.POST.get('host_ip')
            try:
                models.DbNodeInfo.objects.filter(cluster_name__cluster_name=cluster_name, host_ip=host_ip).delete()
            except Error as e:
                logger.error('删除集群%s中节点%s失败，错误信息：%s' %(cluster_name,host_ip,json.dumps(e.args)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                try:
                    cluster_obj = models.DbClusterInfo.objects.get(cluster_name=cluster_name)
                except Error as e:
                    logger.error('查询DbClusterInfo表失败，错误信息：%s' %json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    if cluster_obj.dbnodeinfo_set.all().exists() is False:
                        cluster_obj.delete()
                    return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class QueryDb(View):
    def dispatch(self, request, *args, **kwargs):
        return super(QueryDb, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        cluster_name = request.GET.get('cluster_name')
        # 去数据库查询主库地址和用户密码
        try:
           cluster_queryset = models.DbClusterInfo.objects.filter(cluster_name=cluster_name)
        except Error as e:
            logger.error("查询表DbClusterInfo失败，错误信息：%s" %json.dumps(e.args))
            return JsonResponse({'result': True, 'error_mess': e.args})
        # 判断前端传过来的cluster_name 是否存在
        if not cluster_queryset.exists():
            logger.error("查询表DbClusterInfo中的%s集群数据，不存在" %cluster_name)
            return JsonResponse({'result': False, 'error_mess': '%s 集群不存在' %cluster_name})
        # 因为表设计cluster_name 有且只能有一个不能重复
        cluster_obj = cluster_queryset[0]
        if cluster_obj.db_type == 'oracle':
            return JsonResponse({'result': True, 'data': oracle_schema_dict.keys()})
        else:
            # 查询节点信息
            try:
                node_obj = cluster_obj.dbnodeinfo_set.get(role='master')
            except Exception as e:
                logger.error('查询dbnodeinfo表节点数据失败，错误信息：%s' %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 获取mysql 节点信息
            host_ip = node_obj.host_ip
            username = cluster_obj.username
            password = cluster_obj.password
            port = node_obj.service_port
            db_list = []
            excpt_dbs = ['information_schema','mysql','percona','performance_schema','sys', 'test']
            try:
                conn = mysql.Connect(host=host_ip, user=username, passwd=password, port=port, cursorclass=mysql.cursors.DictCursor)
                cur = conn.cursor()
                cur.execute('show databases')
                dbs_tuple = cur.fetchall()
                cur.close()
                conn.close()
                for db_dict in dbs_tuple:
                    if db_dict['Database'] not in excpt_dbs:
                        db_list.append(db_dict['Database'])
            except mysql.MySQLError as e:
                logger.error('获取%s节点所有数据库失败，错误信息：%s' %(host_ip,json.dumps(e.args)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True, 'data': db_list})


@method_decorator(login_required, 'dispatch')
@method_decorator(permission_controller, 'dispatch')
class DbSqlApply(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(DbSqlApply, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            # 获取组长信息返回
            try:
                group_leader_obj = models.OnelevelLeader.objects.all().exclude(leadername='徐可').values('leadername')
            except Exception as e:
                logger.error("查询OnelevelLeader表获取组长信息失败，错误信息：%s" %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                group_leader = [item['leadername'] for item in group_leader_obj]
            # 获取数据集群中的所有schema信息
            try:
                cluster_mess = {}
                cluster_obj = models.DbClusterInfo.objects.all().values('cluster_name','db_type','username','password')
                excpt_dbs = ['information_schema', 'mysql', 'percona', 'performance_schema', 'sys', 'test']
                for cluster_item in cluster_obj:
                    if cluster_item['db_type'] == 'oracle':
                        try:
                            node_obj = models.DbNodeInfo.objects.filter(cluster_name__cluster_name=cluster_item['cluster_name'])
                        except Exception as e:
                            logger.error('查询DbNodeInfo表失败,错误信息：%s' %json.dumps(e.args))
                            continue
                        # 添加oracle类型数据到cluster_mess中
                        cluster_mess[cluster_item['cluster_name']]={'db_type': cluster_item['db_type'],'host_ip': node_obj[0].host_ip, 'schema':[sc for sc,pw in oracle_schema_dict.items() if pw['pow'] == 'w']}
                    elif cluster_item['db_type'] == 'mysql':
                        try:
                            node_obj = models.DbNodeInfo.objects.get(cluster_name__cluster_name=cluster_item['cluster_name'], role='master')
                        except Exception as e:
                            logger.error('查询DbNodeInfo表失败,错误信息：%s' %json.dumps(e.args))
                            continue
                        try:
                            conn = mysql.Connect(host=node_obj.host_ip, user=cluster_item['username'], passwd=cluster_item['password'], port=node_obj.service_port, cursorclass=mysql.cursors.DictCursor)
                            cur = conn.cursor()
                            cur.execute('show databases')
                            dbs_tuple = cur.fetchall()
                            cur.close()
                            conn.close()
                        except mysql.MySQLError as e:
                            logger.error("链接数据库%s获取信息失败，错误信息：%s" % (node_obj.host_ip, json.dumps(e.args)))
                            continue
                        db_list = []
                        for db_dict in dbs_tuple:
                            if db_dict['Database'] not in excpt_dbs:
                                db_list.append(db_dict['Database'])
                        else:
                            cluster_mess[cluster_item['cluster_name']]={'db_type': cluster_item['db_type'], 'host_ip': node_obj.host_ip, 'schema': db_list}
            except Exception as e:
                logger.error('获取schema信息失败，错误信息：%s' %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                return JsonResponse({'result': True, 'data': {'cluster': cluster_mess, 'group_leader': group_leader}})
        else:
            # 获取组长信息
            try:
                group_leader_obj = models.OnelevelLeader.objects.all().values('leadername')
            except Exception as e:
                logger.error("查询OnelevelLeader表获取组长信息失败，错误信息：%s" %json.dumps(e.args))
                return render(request, 'base_error.html', {'error_mess': e.args})
            else:
                group_leader = [item['leadername'] for item in group_leader_obj]
                return render(request, 'db-sql-apply.html', {'group_leader': group_leader, 'role': self.role})

    def post(self, request):
        username = request.user.get_full_name()
        cluster_name = request.POST.get('cluster_name')
        schema_name = request.POST.get('schema_name')
        group_leader = request.POST.get('group_leader')
        apply_reson = request.POST.get('apply_reson')
        sql = request.POST.get('sql')
        # 判断前端传过来的参数是否为空
        if cluster_name and schema_name and group_leader and apply_reson and sql:
            pass
        else:
            return JsonResponse({'result': False, 'error_mess': "表单有未填列"})
        # 判断sql里面是否有create table 的语句，如果包含子提取出来表名
        table_list = re.findall(r'CREATE TABLE (\S+) ', sql, re.IGNORECASE)

        # 创建数据库链接，链接dbmonitor
        try:
            conn = mysql.Connect(host=dbmonitor['HOST'],
                                 user=dbmonitor['USER'],
                                 passwd=dbmonitor['PASSWORD'],
                                 port=dbmonitor['PORT'],
                                 db=dbmonitor['DB'],
                                 cursorclass=mysql.cursors.DictCursor,
                                 charset='utf8',
                                 autocommit=True)
            cur = conn.cursor()
        except Exception as e:
            logger.error("初始化dbmonitor 库失败:%s" % json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        if table_list:
            # 匹配到有建表语句，并提取出来表名
            table_list = [table.strip('`') for table in table_list]
            logger.info('匹配到的建表，表名：%s' % json.dumps(table_list))
            if cluster_name.__contains__('oracle'):
                m_cluster_name = 'ORACLE'
                m_schema_name = schema_name.upper()
            else:
                m_cluster_name = cluster_name.strip('mysql')
                m_schema_name = schema_name
            return_res = ''
            for table_name in table_list:
                try:
                    tmp_res = cur.execute('''select * from t_table_info where CLUSTER='%s' and TABLE_SCHEMA='%s' and TABLE_NAME='%s' ''' %(m_cluster_name, m_schema_name, table_name))
                except Exception as e:
                    logger.error("查询dbmonitor 库失败:%s" % json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                if tmp_res == 0:
                    return_res = return_res + table_name + ','
            else:
                cur.close()
                conn.close()
                if return_res != '':
                    return JsonResponse({'result': False, 'error_mess': '表%s未在数据资产管理系统登记过，请先登记在创建表' %return_res.strip(',')})

        # sql工单申请入口处理
        try:
            models.DbSqlApplyResult.objects.create(
                username=username,
                cluster_name=cluster_name,
                schema_name=schema_name,
                group_leader=group_leader,
                apply_reson=apply_reson,
                sql=sql,
                apply_time=datetime.datetime.now()
            )
        except Exception as e:
            logger.error("数据插入DbSqlApplyResult失败，错误信息:%s" %json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class SqlOrderRelease(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(SqlOrderRelease, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            method = request.GET.get('method')
            if method == 'get_date':
                try:
                    ndate_obj = models.DbSqlApplyResult.objects.filter(apply_time__gte=(datetime.datetime.now()-datetime.timedelta(days=7))).values("apply_time")
                except Exception as e:
                    logger.error('查询DbSqlApplyResult获取日期数据失败，错误信息：%s' %json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    ndate_list = [date_item['apply_time'].strftime("%Y-%m-%d") for date_item in ndate_obj]
                    return JsonResponse({'result': True, 'data': sorted(list(set(ndate_list)), reverse=True)})
            elif method == 'get_ndate':
                ndate = request.GET.get('ndate')
                username = request.user.get_full_name()
                if self.role == 'admin':
                    if ndate is None:
                        try:
                            data = models.DbSqlApplyResult.objects.filter(apply_time__gte=datetime.datetime.now().strftime('%Y-%m-%d'))
                        except Exception as e:
                            logger.error('查询DbSqlApplyResult中最新日期数据失败，错误信息：%s' %json.dumps(e.args))
                            return JsonResponse({'result': False, 'error_mess': e.args})
                    else:
                        try:
                            data = models.DbSqlApplyResult.objects.filter(apply_time__gte='%s 00:00:00' %ndate, apply_time__lt='%s 23:59:59' %ndate)
                        except Exception as e:
                            logger.error('查询DbSqlApplyResult中最新日期数据失败，错误信息：%s' %json.dumps(e.args))
                            return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    if ndate is None:
                        try:
                            data = models.DbSqlApplyResult.objects.filter(apply_time__gte=datetime.datetime.now().strftime('%Y-%m-%d'), username=username)
                        except Exception as e:
                            logger.error('查询DbSqlApplyResult中最新日期数据失败，错误信息：%s' %json.dumps(e.args))
                            return JsonResponse({'result': False, 'error_mess': e.args})
                    else:
                        try:
                            data = models.DbSqlApplyResult.objects.filter(apply_time__gte='%s 00:00:00' % ndate, apply_time__lt='%s 23:59:59' % ndate, username=username)
                        except Exception as e:
                            logger.error('查询DbSqlApplyResult中最新日期数据失败，错误信息：%s' %json.dumps(e.args))
                            return JsonResponse({'result': False, 'error_mess': e.args})
                # 获取数据逻辑处理返回结果
                data_list = []
                for sql_apply_item in data:
                    data_list.append({
                        'id': sql_apply_item.id,
                        'username': sql_apply_item.username,
                        'cluster_name': sql_apply_item.cluster_name,
                        'schema_name': sql_apply_item.schema_name,
                        'apply_reson': sql_apply_item.apply_reson,
                        'apply_time': sql_apply_item.apply_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'group_leader': sql_apply_item.group_leader,
                        'group_leader_agree': sql_apply_item.group_leader_agree,
                        'dba_agree': sql_apply_item.dba_agree,
                        'dba_not_agree_reson': sql_apply_item.dba_not_agree_reson,
                        'is_dba_exec': sql_apply_item.is_dba_exec,
                        'sql': sql_apply_item.sql,
                        'is_success': sql_apply_item.is_success,
                        'start_exec_time': None if sql_apply_item.start_exec_time is None else sql_apply_item.start_exec_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'end_exec_time': None if sql_apply_item.end_exec_time is None else sql_apply_item.end_exec_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'result': sql_apply_item.result
                    })
                else:
                    return JsonResponse({'result': True, 'data': data_list})
        else:
            try:
                group_leader_obj = models.OnelevelLeader.objects.all().exclude(leadername='徐可').values('leadername')
            except Exception as e:
                logger.error("查询OnelevelLeader表获取组长信息失败，错误信息：%s" %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                group_leader = [item['leadername'] for item in group_leader_obj]
                return render(request, 'db-sql-deploy.html', {'role': self.role, 'group_leader': group_leader})


@method_decorator(login_required, 'dispatch')
class SqlGroupLeaderApprove(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        try:
            group_leader_obj = models.OnelevelLeader.objects.all().exclude(leadername='徐可').values('leadername')
        except Exception as e:
            logger.error("查询OnelevelLeader表获取组长信息失败，错误信息：%s" % json.dumps(e.args))
            self.group_leader = []
        else:
            self.group_leader = [item['leadername'] for item in group_leader_obj]
        return super(SqlGroupLeaderApprove, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            # 判断用户角色，如果是admin返回所有组长未审批额sql工单，如果为非admin用户获取当前用户所有未审批的sql 工单
            if self.role == 'admin':
                try:
                    sql_order_obj = models.DbSqlApplyResult.objects.filter(group_leader_agree="")
                except Exception as e:
                    logger.error("查询DbSqlApplyResult获取所有组长未审批的sql工单报错，错误信息：%s" %json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                try:
                    sql_order_obj = models.DbSqlApplyResult.objects.filter(group_leader=request.user.get_full_name(), group_leader_agree="")
                except Exception as e:
                    logger.error("查询DbSqlApplyResult获取组长未审批的sql工单执行失败，错误信息：%s" %json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
            # 定义一个列表用于零时存放数据
            data_list = []
            for sql_apply_item in sql_order_obj:
                data_list.append({
                    'id': sql_apply_item.id,
                    'username': sql_apply_item.username,
                    'cluster_name': sql_apply_item.cluster_name,
                    'schema_name': sql_apply_item.schema_name,
                    'apply_reson': sql_apply_item.apply_reson,
                    'apply_time': sql_apply_item.apply_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'sql': sql_apply_item.sql,
                })
            else:
                return JsonResponse({'result': True, 'data': data_list})
        else:
            return render(request, 'db-sql-groupleader-agree.html', {'role': self.role, 'group_leader': self.group_leader})

    def post(self, request):
        nid = request.POST.get('id')
        group_leader_agree_content = request.POST.get('content')
        try:
            models.DbSqlApplyResult.objects.filter(id=nid).update(group_leader_agree=group_leader_agree_content)
        except Exception as e:
            logger.error("更新DbSqlApplyResult id 为%s信息失败，错误信息：%s" %(nid, json.dumps(e.args)))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class SqlDbaApprove(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(SqlDbaApprove, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            # 获取所有dba未审批的sql 工单
            try:
                dba_sql_obj = models.DbSqlApplyResult.objects.filter(group_leader_agree='同意',dba_agree='',is_dba_exec='')
            except Exception as e:
                logger.error('查询DbSqlApplyResult 获取dba要审批的工单报错，错误信息：%s' %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            dba_sql_list = []
            for sql_item in dba_sql_obj:
                dba_sql_list.append({
                    'id': sql_item.id,
                    'username': sql_item.username,
                    'cluster_name': sql_item.cluster_name,
                    'schema_name': sql_item.schema_name,
                    'apply_reson': sql_item.apply_reson,
                    'apply_time': sql_item.apply_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'sql': sql_item.sql
                })
            else:
                return JsonResponse({'result': True, 'data': dba_sql_list})
        else:
            return render(request, 'db-sql-dba-agree.html', {'role': self.role})

    def post(self, request):
        nid = request.POST.get('id')
        method = request.POST.get('method')
        reason = request.POST.get('reason')
        if method == 'dba执行':
            try:
                models.DbSqlApplyResult.objects.filter(id=nid).update(is_dba_exec='是', dba_not_agree_reson=reason)
            except Exception as e:
                logger.error('修改DbSqlApplyResult信息失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            try:
                models.DbSqlApplyResult.objects.filter(id=nid).update(
                    dba_agree=method,
                    dba_not_agree_reson=reason
                )
            except Exception as e:
                logger.error('修改DbSqlApplyResult信息失败，错误信息：%s' % json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})

        return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class SqlDbaExc(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            self.role = models.Role.objects.get(myuser__username=request.user.username).name
        except Error, e:
            logger.error('查询角色信息报错：%s' % e.args[1])
            self.role = 'guest'
        return super(SqlDbaExc, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        if request.is_ajax():
            # 获取所有需要dba来执行sql语句
            try:
                db_sql_obj = models.DbSqlApplyResult.objects.filter(is_dba_exec='是',is_success='')
            except Exception as e:
                logger.error('查询DbSqlApplyResult获取需要dba执行的sql工单报错，错误信息：%s' %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            # 拼装数据返回给用户
            dba_sql_list = []
            for sql_item in db_sql_obj:
                dba_sql_list.append({
                    'id':sql_item.id,
                    'username':sql_item.username,
                    'cluster_name': sql_item.cluster_name,
                    'schema_name': sql_item.schema_name,
                    'apply_reson': sql_item.apply_reson,
                    'sql': sql_item.sql,
                    'apply_time': sql_item.apply_time.strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                return JsonResponse({'result': True, 'data': dba_sql_list})
        else:
            return render(request, 'db-sql-dba-exc.html', {'role': self.role})

    def post(self, request):
        nid = request.POST.get('id')
        result = request.POST.get('result')
        try:
            models.DbSqlApplyResult.objects.filter(id=nid).update(is_success=result, result=result)
        except Exception as e:
            logger.error('更新DbSqlApplyResult  dba执行结果失败，错误信息：%s' %json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        else:
            return JsonResponse({'result': True})


@method_decorator(login_required, 'dispatch')
class SqlExc(View):
    def dispatch(self, request, *args, **kwargs):
        return super(SqlExc, self).dispatch(request, *args, **kwargs)

    def post(self, request):
        nid = request.POST.get('id')
        # 获取到要执行sql语句
        try:
            order_obj = models.DbSqlApplyResult.objects.get(id=nid)
        except Exception as e:
            logger.error('查询DbSqlApplyResult获取要执行的sql语句失败，错误信息：%s' % json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        cluster_name = order_obj.cluster_name
        schema_name = order_obj.schema_name
        sql = order_obj.sql.replace("；", ';')
        start_time = datetime.datetime.now()
        # 查询主库信息:
        try:
            master_host_obj = models.DbClusterInfo.objects.filter(Q(dbnodeinfo__role='master') | Q(dbnodeinfo__role='rac'), cluster_name=cluster_name).values(
                'dbnodeinfo__host_ip',
                'dbnodeinfo__service_port',
                'password',
                'username',
                'db_type',
                'service_name',
            )
        except Exception as e:
            logger.error("查询DbClusterInfo获取集群信息失败，错误信息：%s" % json.dumps(e.args))
            return JsonResponse({'result': False, 'error_mess': e.args})
        # 判断master_host_obj 是否为空，如果为空返回错误信息
        if not master_host_obj.exists():
            return JsonResponse({'result': True, 'error_mess': '集群不存在'})
        # 取出唯一的一个主节点数据信息
        master_host = master_host_obj[0]
        # 判断 数据库类型
        if master_host['db_type'] == 'mysql':
            # 判断查询到的节点是否为主节点，如果为主节点则执行sql，如果不为主节点返回错误信息
            # 创建数据连接
            try:
                conn = mysql.Connect(host=master_host['dbnodeinfo__host_ip'],
                                     user=master_host['username'],
                                     passwd=master_host['password'],
                                     port=master_host['dbnodeinfo__service_port'],
                                     db=schema_name,
                                     cursorclass=mysql.cursors.DictCursor,
                                     charset='utf8',
                                     autocommit=True)
                cur = conn.cursor()
            except Exception as e:
                logger.error('链接%s数据库失败错误信息：%s' %(cluster_name, json.dumps(e.args)))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                # cur.execute('show slave status')
                # if len(cur.fetchall()) != 0:
                #     logger.error('%s 不是主节点' %master_host['dbnodeinfo__host_ip'])
                #     return JsonResponse({'result': False, 'error_mess': '读取数据库记录的主节点有问题'})
                # 开始执行sql语句
                # 解析sql语句
                sql_list = [item for item in sql.split(';') if len(item) != 0]
                index = 0
                result = ''
                is_success = ''
                for sql_item in sql_list:
                    try:
                        cur.execute('''%s''' %sql_item)
                    except Exception as e:
                        logger.error('执行%s失败错误信息：%s' %(sql_item, json.dumps(e.args)))
                        result = result+sql_item+'---执行失败，错误信息：%s' %json.dumps(e.args)+'<br>'
                        is_success = '失败'
                        break
                    else:
                        result = result + sql_item + '---执行成功<br>'
                    finally:
                        index += 1
                if index < len(sql_list):
                    for sql_item1 in sql_list[index:]:
                        result = result+sql_item1+'---未执行<br>'
                    else:
                        is_success = '失败'
                else:
                    if is_success == '':
                        is_success = '成功'
                # 获取结束时间
                end_time = datetime.datetime.now()
                # 插入结构到sql工单表单中
                try:
                    models.DbSqlApplyResult.objects.filter(id=nid).update(
                        is_success=is_success,
                        result=result,
                        start_exec_time=start_time,
                        end_exec_time=end_time
                    )
                except Exception as e:
                    logger.error('更新DbSqlApplyResult表失败，错误信息：%s' %json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True})
            finally:
                if 'cur' in locals().keys():
                    cur.close()
                if 'conn' in locals().keys():
                    conn.close()
        else:
            # 创建一个oracle 链接
            try:
                conn = cx_Oracle.connect(user=schema_name,
                                         password=oracle_schema_dict[schema_name]['password'],
                                         dsn='%s:%s/%s' %(master_host['dbnodeinfo__host_ip'], master_host['dbnodeinfo__service_port'], master_host['service_name']),
                                         encoding='utf-8',
                                         )
                cur = conn.cursor()
            except Exception as e:
                logger.error('创建链接失败错误信息：%s' %json.dumps(e.args))
                return JsonResponse({'result': False, 'error_mess': e.args})
            else:
                # 解析sql语句
                sql_list = [item for item in sql.split(';') if len(item) != 0]
                index = 0
                result = ''
                is_success = ''
                for sql_item in sql_list:
                    try:
                        cur.execute('''%s''' % sql_item)
                        conn.commit()
                    except Exception as e:
                        logger.error('执行%s失败错误信息：%s' % (sql_item, json.dumps(e.args)))
                        result = result + sql_item + '---执行失败，错误信息：%s' % json.dumps(e.args) + '<br>'
                        break
                    else:
                        result = result + sql_item + '---执行成功<br>'
                    finally:
                        index += 1
                if index < len(sql_list):
                    for sql_item1 in sql_list[index:]:
                        result = result + sql_item1 + '---未执行<br>'
                    else:
                        if is_success == '':
                            is_success = '成功'
                else:
                    is_success = '成功'
                # 获取结束时间
                end_time = datetime.datetime.now()
                # 插入结构到sql工单表单中
                try:
                    models.DbSqlApplyResult.objects.filter(id=nid).update(
                        is_success=is_success,
                        result=result,
                        start_exec_time=start_time,
                        end_exec_time=end_time
                    )
                except Exception as e:
                    logger.error('更新DbSqlApplyResult表失败，错误信息：%s' % json.dumps(e.args))
                    return JsonResponse({'result': False, 'error_mess': e.args})
                else:
                    return JsonResponse({'result': True})
            finally:
                if 'conn' in locals():
                    conn.close()


