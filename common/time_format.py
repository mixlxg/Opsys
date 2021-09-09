#!/usr/bin/env python
# -*- coding: utf-8 -*- 
# @Time : 2020/3/20 14:37 
# @Author : 吕秀刚
# @File : time_format.py


def s_to_dhms(s):
    if s < 0:
        return "不限时"
    # 将给的秒转换为多少天多少小时多少分钟多少秒，例如2天3小时6分钟23秒
    # 返回字符串
    # 计算出分钟数和秒数
    t_m, s = divmod(s, 60)
    t_h, m = divmod(t_m, 60)
    d, h = divmod(t_h,24)
    return '%s天%s时%s分%s秒' %(d, h, m, s)
