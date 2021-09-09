#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2021/7/5 14:06 
# @Author : mixlxg
# @File : k8sApply.py
import os
from common.k8s_yaml_parse import K8sYamlParse
from common.exec_shell_command.exec_comm import command


def k8s_apply(image, deploy_yaml):
    # 解析一下deploy_yaml 逻辑和文件名
    yaml_path = os.path.dirname(deploy_yaml)
    yaml_name = os.path.basename(deploy_yaml)
    hostNetwork = False
    # 创建一个yaml对象
    yaml_obj = K8sYamlParse(deploy_yaml)
    flag, data = yaml_obj.parse()
    # 解析yaml文件
    if flag is not True:
        return flag, data
    else:
        hostNetwork = data[0]['spec']['template']['spec'].has_key('hostNetwork')
        data[0]['spec']['template']['spec']['containers'][0]['image'] = image
    # dump yaml文件
    flag, mess = yaml_obj.dump(data)
    if flag is not True:
        return flag, mess
    # yaml 文件修改完成，开始apply yaml文件
    # 拼接执行命令
    if hostNetwork:
        comm = 'cd %s && kubectl delete -f %s && kubectl apply -f %s' %(yaml_path, yaml_name, yaml_name)
    else:
        comm = 'cd %s && kubectl apply -f %s' %(yaml_path, yaml_name)

    return command(comm)



