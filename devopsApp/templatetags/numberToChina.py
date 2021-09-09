#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/3/18 9:44
    @FileName: numberToChina.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
from  django import template
register = template.Library()


@register.simple_tag
def numberToChina(value, user_define, china_value):
    if value == user_define:
        return china_value
    else:
        if china_value == '对':
            return '错'
        if china_value == '错':
            return '对'
        if china_value == '是':
            return '否'
        if china_value == '否':
            return '是'