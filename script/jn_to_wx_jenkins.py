#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2020/12/4 10:12 
# @Author : mixlxg
# @File : jn_to_wx_jenkins.py
from __future__ import unicode_literals, absolute_import,print_function
import os
import sys
import django
import datetime
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Opsys.settings")
django.setup()
from devopsApp import models
from jenkins import Jenkins
from jenkins import JenkinsException
# 无锡Jenkins 信息
wx_jenkins_user_dict = {
    'url': 'http://192.200.251.45:30081/wxci_new/',
    'username': 'admin',
    'password': '8HqzQRJUDqvWwyGDYXFYPVrW7xGEFvNE'
}
if __name__ == '__main__':
    # 查询江宁数据库看当前时间到前一天有没有发布的项目
    now_datetime = datetime.datetime.now()
    last_day_datetime = now_datetime - datetime.timedelta(days=1)
    jobs = models.DeployProjectApply.objects.exclude(really_deploy_time__isnull=True).filter(really_deploy_time__range=[last_day_datetime, now_datetime]).values(
        'project_name',
        'deploy_result',
        'really_deploy_time'
    )
    # 循环打印扫描出来的jobs
    # 定义零时list用于存放需要在无锡发布的任务
    tmp_jobs = []
    for job in jobs:
        if job['deploy_result'] == '成功':
            if job['project_name'] not in tmp_jobs:
                tmp_jobs.append(job['project_name'])
    else:
        if tmp_jobs:
            try:
                jenkin = Jenkins(**wx_jenkins_user_dict)
            except JenkinsException as e:
                print(e.message)
            else:
                for job_name in tmp_jobs:
                    jenkin.build_job(job_name)
                else:
                    print("同步结束，同步了如下任务：%s" %json.dumps(tmp_jobs))




