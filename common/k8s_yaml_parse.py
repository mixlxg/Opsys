#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time : 2021/7/2 10:28 
# @Author : mixlxg
# @File : k8s_yaml_parse.py
import yaml


class K8sYamlParse(object):

    def __init__(self, file_name):
        self.__file_name = file_name

    def parse(self):
        with open(self.__file_name, 'r') as fp:
            try:
                cfg = yaml.load_all(fp, Loader=yaml.CLoader)
            except Exception as e:
                return False, e.message
            else:
                return True, list(cfg)

    def dump(self, data):
        with open(self.__file_name, 'w') as fp:
            try:
                yaml.safe_dump_all(data, stream=fp, allow_unicode=True, encoding='utf-8',default_flow_style=False, explicit_start=True)
            except Exception as e:
                return False, e.message
            else:
                return True, None


if __name__ == '__main__':
    obj = K8sYamlParse('traefix-rbac.yaml')
    flag, data = obj.parse()
    if flag:
      data[0]['metadata']['namespace']='harbor.sc.js/base/traefik:v1.7.31'
    obj.dump(data)