# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os,django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Opsys.settings")
django.setup()
from devopsApp import models
obj = models.DeployProjectApply.objects.filter(project_name__contains="-test").values()
print list(obj)
from django.test import TestCase
import xlwt
import os
from devopsApp import models
from django.conf import settings
from django.db.models import Max, Min, F
from common.Mjenkins import Mjenkins
from rediscluster import RedisCluster
import requests
from kubernetes import client,config
from kubernetes.client.rest import ApiException
import yaml
# config.load_kube_config()
#
# client.VersionApi()

# s=models.Service.objects.exclude(status='offline').values('host__ip')
# import MySQLdb as mysql
# import requests, datetime
#
# con = mysql.Connect(host='192.168.43.9',user='Opsys',passwd='Opsysadmin')
# cur = con.cursor()
# cur.execute('show slave status')
# print cur.fetchall()
# master_host_obj = models.DbClusterInfo.objects.filter(cluster_name='localdb', dbnodeinfo__role='master').values(
#     'dbnodeinfo__host_ip',
#     'dbnodeinfo__service_port',
#     'password',
#     'username'
# )
# print master_host_obj.exists()


# s=models.DbSqlApplyResult.objects.filter(group_leader_agree='同意',dba_agree='',is_dba_exec='')
# print s
# s=models.DbSqlApplyResult.objects.filter(apply_time__gte=datetime.datetime.now().strftime('%Y-%m-%d'))
# print s
# ndate ='2020-05-25'
# s=models.DbSqlApplyResult.objects.filter(apply_time__gte='%s 00:00:00' %ndate,apply_time__lt='%s 23:59:59' %ndate)
# print s[0].apply_time
# s=models.DbSqlApplyResult.objects.filter(apply_time__gte=(datetime.datetime.now()-datetime.timedelta(days=7))).values("apply_time").distinct().order_by('-apply_time')
# print s
# s=models.DbSqlApplyResult.objects.get(id=3)
# print s.sql
from urlparse import urlparse,urlunparse
#s=urlparse('http://127.0.0.1/user?name=lvxiugang&age=10')

# header = {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'}
# res = requests.post('http://127.0.0.1:8080/MPost', data='names[lv]=10&names[li]=20', headers=header)
# print res.json()

# s = models.DbClusterInfo.objects.get(cluster_name='locatdb')
# s1 = s.dbnodeinfo_set.all()
# print s1.exists()
# models.Service.objects.filter(status="offline").filter().values('host__ip')
# mysql.Connect()
# mysql.cursors.DictCursor

# s=models.DbClusterInfo.objects.all()[0]
# print s.dbnodeinfo_set.exists()
# requests.post()
# class base(object):
#     def __int__(self):
#         print '我是爷爷'
#     def get_gb(self):
#         self.gb()
#         self.isfase()
#
# class fbase(base):
#     def __int__(self):
#         super(fbase, self).__int__()
#     def isfase(self):
#         print '爸爸'
# class gbase(object):
#     def gb(self):
#         print '干爸'
# class son(gbase,fbase):
#     def __int__(self):
#         super(son,self).__int__()
#
# s=son()
# s.get_gb()
# s = models.Service.objects.get(service_name='member-report')
# iplist = [item[0] for item in s.host.values_list('ip')]
# print iplist

# from django_redis import get_redis_connection
# conn = get_redis_connection()
# s=models.Service.objects.exclude(status='offline')
# for item in s:
#     iplist = [item[0] for item in item.host.values_list('ip')]
#     item.service_name

# a=[1]
# def func():
#     a.append(10)
#
# func()
# print a

# Mjenkins.disable_job('xhjt-server')

#models.AppOffline.objects.filter(service_name='test').update(service_name='test1')


# obj = models.Service.objects.filter(service_name=service_name, service_port=service_port, host__ip=ip).annotate(ip=F('host__ip'), password=F('host__root_password')).values(
#                 'service_port',
#                 'service_name',
#                 'ip',
#                 'password',
#                 'start_script',
#                 'stop_script',
#                 'package_deploy_path'
#             )
# print obj

# service_obj = models.Service.objects.filter(service_name='woService-listen').annotate(ip=F('host__ip'), password=F('host__root_password')).values(
#     'service_name',
#     'service_port',
#     'start_script',
#     'stop_script',
#     'ip',
#     'password',
# )
# print service_obj


# filename = os.path.join(settings.BASE_DIR, 'execl', 'deploy_apply', 'test.xlsx')
# logo = os.path.join(settings.BASE_DIR, 'execl', 'deploy_apply', 'logo.bmp')
# objs = models.WorkOrderNeeds.objects.filter(deploy_time='2019-09-30')
# wb = xlwt.Workbook(encoding='gbk')
# ws = wb.add_sheet("需求表单")
# ws1 = wb.add_sheet('版本信息')
# ws2 = wb.add_sheet('审批')
# # 生成需求表单sheet
# stye = xlwt.easyxf('font: name 宋体, height 200; Borders: left THIN,right THIN,top THIN,bottom THIN; align: wrap on, vert centre, horiz center')
# ws.write_merge(0, 2, 0, 8, "项目版本发布信息",xlwt.easyxf('font: name 宋体, bold on, height 351; Borders: left THIN,right THIN,top THIN,bottom THIN; align: wrap on, vert centre, horiz center'))
# ws.insert_bitmap(logo, 0, 0)
# ws.write_merge(3, 3, 0, 0, '部署环境', stye)
# ws.write_merge(3, 3, 2, 4, '□测试环境   □生产环境', stye)
# ws.write_merge(3, 3, 5, 6, '计划部署时间', stye)
# ws.write_merge(3, 3, 7, 8, '', stye)
# need_high = len(objs) * 3
# ws.write_merge(4, 3+need_high, 0, 1, '版本发布摘要', stye)
# row = 3
# for item in objs:
#     row = row +1
#     mrow = row + 2
#     ws.write_merge(row, mrow, 2, 8, '%s \n\n 代码审核：         产品经理：         研发：                      测试：         ' %item.need_content, stye)
#     row = mrow
# # 生成版本信息sheet
# ws1.write_merge(0, 0, 0, 10, '版本信息',xlwt.easyxf('font: name 宋体, bold on, height 351; Borders: left THIN,right THIN,top THIN,bottom THIN; align: wrap on, vert centre, horiz center') )
# ws_row = 1
# flag = 1
# one_flag =1
# for obj_item in objs:
#     ws_row_m = ws_row + len(obj_item.need_deploy_project.all())
#     ws1.write_merge(ws_row, ws_row_m, 0, 0, flag, stye)
#     ws1.write_merge(one_flag,one_flag,1,10, '需求： %s' %obj_item.need_content, xlwt.easyxf('font: name 宋体, bold on, height 200; Borders: left THIN,right THIN,top THIN,bottom THIN') )
#     one_flag +=1
#     for one_project_obj in obj_item.need_deploy_project.all():
#         ws1.write_merge(one_flag, one_flag, 1, 10, '%s 发布人:%s  研发:%s ' %(one_project_obj.project_name,one_project_obj.deploy_username,one_project_obj.developers_name) ,stye)
#         one_flag += 1
#     ws_row = ws_row_m + 1
#     flag += 1
# else:
#     ws1.col(0).width=256*3
#
# # 生成审批sheet
# #objs.all().values('need_deploy_project__tamper_resistant_start_time')
# #查找防篡改时间
# start_time = objs.all().aggregate(Min('need_deploy_project__tamper_resistant_start_time'))['need_deploy_project__tamper_resistant_start_time__min']
# end_time = objs.all().aggregate(Max('need_deploy_project__tamper_resistant_end_time'))['need_deploy_project__tamper_resistant_end_time__max']
# tamper_flag = '否'
# if start_time is None or end_time is None:
#     tamper = "关闭时间段:"
# else:
#     tamper_flag = '是'
#     tamper = '关闭时间段：%s ~ %s' %(start_time.strftime('%Y-%m-%d %H:%M:%S'),end_time.strftime('%Y-%m-%d %H:%M:%S'))
# ws2.write_merge(0, 0, 0, 1,"网页防篡改",stye)
# ws2.write_merge(0, 0, 2, 2,"是否关闭",stye)
# ws2.write_merge(0,0,3,3,tamper_flag,stye)
# ws2.write_merge(0,0,4,9,tamper,stye)
# ws2.write_merge(1,3,0,1,'领导签字',stye)
# ws2.write_merge(1,3,2,9,'',stye)
# ws2.write_merge(4,6,0,1,'测试结果',stye)
# ws2.write_merge(4,6,2,9,'',stye)
# wb.save(filename)
