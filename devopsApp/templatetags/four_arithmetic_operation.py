#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/4/8 16:31
    @FileName: four_arithmetic_operation.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, division
from django import template

register = template.Library()
@register.filter
def mydivision(value, param):
    return round(int(value)/int(param), 2)

# register = template.Library()  # 固定变量名
#
#
# @register.filter
# def multi(num1, num2):
#     return num1 * num2
