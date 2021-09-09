#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2020/8/10 20:02 
# @Author : 吕秀刚
# @File : cleanEs_AddKibana.py
"""
 脚本往kibana中添加当日的索引模式servicelog
 删除servicelog 15天前的索引模式
 删除es中servicelog 15天前索引
 删除es中systemlog 180天的索引
"""
import requests
import datetime
import sys
import json
import elasticsearch
if __name__ == '__main__':
    # 目前es中的索引全部是以日志类型-yyyy.mm.dd 格式生成的名字
    # 获取当日日期
    current_date = datetime.datetime.now().strftime("%Y.%m.%d")
    # 获取半年前时间
    half_year_date = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y.%m.%d")
    # 获取15天前的日期
    half_mon_date = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y.%m.%d")
    # 拼接索引名称
    current_servicelog = 'servicelog-%s' % current_date
    current_nginxlog =  'nginxlog-%s' %current_date
    current_sctest= 'sctest-%s' %current_date
    half_mon_sctest = 'sctest-%s' % half_year_date
    current_scprod= 'scprod-%s' %current_date
    half_mon_scprod = 'scprod-%s' % half_year_date
    half_year_systemlog = 'systemlog-%s' % half_year_date
    half_mon_servicelog = 'servicelog-%s' % half_mon_date
    half_mon_nginxlog = 'nginxlog-%s' %half_mon_date
    # 添加scprod 当日索引模式
    try:
        res = requests.post(
            url='http://192.200.239.216:5601/api/saved_objects/index-pattern/%s' % current_scprod,
            headers={'kbn-xsrf': json.dumps(True)},
            json={
                'attributes': {
                    'title': current_scprod,
                    'timeFieldName': '@timestamp'
                }
            }
        )
    except Exception as e:
        print "添加kibana所以模式%s失败，错误信息:%s" % (current_scprod, e.message)
        sys.exit(1)
    else:
        if res.status_code != 200:
            if  res.status_code != 409:
                print "添加kibana所以模式%s失败，状态码:%s" % (current_scprod, res.status_code)
                sys.exit(1)
    # 添加sctest 当日索引模式
    try:
        res = requests.post(
            url='http://192.200.239.216:5601/api/saved_objects/index-pattern/%s' % current_sctest,
            headers={'kbn-xsrf': json.dumps(True)},
            json={
                'attributes': {
                    'title': current_sctest,
                    'timeFieldName': '@timestamp'
                }
            }
        )
    except Exception as e:
        print "添加kibana所以模式%s失败，错误信息:%s" % (current_sctest, e.message)
        sys.exit(1)
    else:
        if res.status_code != 200:
            if  res.status_code != 409:
                print "添加kibana所以模式%s失败，状态码:%s" % (current_sctest, res.status_code)
                sys.exit(1)

    # 添加nginx 当日索引模式
    try:
        res = requests.post(
            url='http://192.200.239.216:5601/api/saved_objects/index-pattern/%s' % current_nginxlog,
            headers={'kbn-xsrf': json.dumps(True)},
            json={
                'attributes': {
                    'title': current_nginxlog,
                    'timeFieldName': '@timestamp'
                }
            }
        )
    except Exception as e:
        print "添加kibana所以模式%s失败，错误信息:%s" % (current_nginxlog, e.message)
        sys.exit(1)
    else:
        if res.status_code != 200:
            if res.status_code != 409:
                print "添加kibana所以模式%s失败，状态码:%s" % (current_nginxlog, res.status_code)
                sys.exit(1)

    # 添加servicelog 当日的索引模式
    try:
       res = requests.post(url='http://192.200.239.216:5601/api/saved_objects/index-pattern/%s' %current_servicelog,
                      headers={'kbn-xsrf': json.dumps(True)},
                      json={
                          'attributes':{
                              'title': current_servicelog,
                              'timeFieldName': '@timestamp'
                          }
                      })
    except Exception as e:
        print "添加kibana所以模式%s失败，错误信息:%s" % (current_servicelog, e.message)
        sys.exit(1)
    else:
        if res.status_code != 200:
            if res.status_code != 409:
                print "添加kibana所以模式%s失败，状态码:%s" % (current_servicelog, res.status_code)
                sys.exit(1)
    # kibana 添加索引模式成功，设置当天的所以模式玮默认所以模式
    try:
        res = requests.post(
            url='http://192.200.239.216:5601/api/kibana/settings/defaultIndex',
            headers={'kbn-xsrf': json.dumps(True)},
            json={
                'value': current_servicelog
            }
        )
    except Exception as e:
        print "设置%s 为kibana默认模式失败，错误信息：%s" % (current_servicelog, e.message)
    else:
        if res.status_code != 200:
            if res.status_code != 409:
                print "设置%s 为kibana默认模式失败，状态码：%s" % (current_servicelog, res.status_code)
    # 设置成功或者失败默认模式都往下执行
    # 删除scprod中十五天前的索引模式
    try:
        res = requests.delete(
            url='http://192.200.239.216:5601/api/saved_objects/index-pattern/%s' % half_mon_scprod,
            headers={'kbn-xsrf': json.dumps(True)}
        )
    except Exception as e:
        print '删除%s索引模式失败，错误信息：%s' % (half_mon_scprod, e.message)
    else:
        if res.status_code != 200:
            if res.status_code != 409:
                print '删除%s索引模式失败，错误码：%s' % (half_mon_scprod, res.status_code)
    # 删除testsc中十五天前的索引模式
    try:
        res = requests.delete(
            url='http://192.200.239.216:5601/api/saved_objects/index-pattern/%s' %half_mon_sctest,
            headers={'kbn-xsrf': json.dumps(True)}
        )
    except Exception as e:
        print '删除%s索引模式失败，错误信息：%s' % (half_mon_sctest, e.message)
    else:
        if res.status_code != 200:
            if res.status_code != 409:
                print '删除%s索引模式失败，错误码：%s' % (half_mon_sctest, res.status_code)
    # 删除kibana中十五天前的索引模式
    try:
        res = requests.delete(
            url='http://192.200.239.216:5601/api/saved_objects/index-pattern/%s' %half_mon_servicelog,
            headers={'kbn-xsrf': json.dumps(True)}
        )
    except Exception as e:
        print '删除%s索引模式失败，错误信息：%s' % (half_mon_servicelog, e.message)
    else:
        if res.status_code != 200:
            if res.status_code != 409:
                print '删除%s索引模式失败，错误码：%s' % (half_mon_servicelog, res.status_code)
    # 删除kibana 十五天前的nginxlog 索引模式
    try:
        res = requests.delete(
            url='http://192.200.239.216:5601/api/saved_objects/index-pattern/%s' %half_mon_nginxlog,
            headers={'kbn-xsrf': json.dumps(True)}
        )
    except Exception as e:
        print '删除%s索引模式失败，错误信息：%s' % (half_mon_nginxlog, e.message)
    else:
        if res.status_code != 200:
            if res.status_code != 409:
                print '删除%s索引模式失败，错误码：%s' % (half_mon_nginxlog, res.status_code)
    # 删除kibana 十五天的servicelog 索引模式成功
    # 删除es中systemlog 中180天的index
    try:
        client = elasticsearch.Elasticsearch(hosts=['192.200.239.223:9200', '192.200.239.239:9200', '192.200.239.245:9200'])
        sys_index = client.indices.delete(half_year_systemlog)
        service_index = client.indices.delete(half_mon_servicelog)
        nginx_index = client.indices.delete(half_mon_nginxlog)
        client.close()
    except Exception as e:
        print "删除%s 索引或者%s索引失败，错误我信息：%s" % (half_mon_servicelog, half_year_systemlog, e.message)
    else:
        if sys_index['acknowledged'] is not True:
            print '删除%s 索引失败' % half_year_systemlog
        if service_index['acknowledged'] is not True:
            print '删除%s 索引失败' % half_mon_servicelog
        if nginx_index['acknowledged'] is not True:
            print '删除%s 索引失败' % half_mon_nginxlog
