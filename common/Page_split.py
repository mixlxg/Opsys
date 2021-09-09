#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/3/15 10:47
    @FileName: Page_split.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, print_function


class Page(object):
    def __init__(self, url, total_count, current_page, per_page_num=20, max_page_num=7,):
        """
        :param total_count: type number 总数据条数
        :param current_page: type number 当前页码
        :param per_page_num: type number 每页多少条
        :param max_page_num :  type number 显示多少页
        """
        self._total_count = total_count
        try:
            self._current_page = int(current_page)
            if self._current_page <= 0:
                self._current_page = 1
        except Exception, e:
            self._current_page = 1
        self._per_page_num = per_page_num
        self._max_page_num = max_page_num
        self._url = url
    @property
    def start(self):
        return (self._current_page - 1) * self._per_page_num

    @property
    def end(self):
        return self._current_page * self._per_page_num

    @property
    def total_page_num(self):
        page_num_tuple = divmod(self._total_count, self._per_page_num)
        if page_num_tuple[0] == 0:
            return 0
        else:
            if page_num_tuple[1] == 0:
                return page_num_tuple[0]
            else:
                return page_num_tuple[0] + 1

    def page_show_range(self):
        if self.total_page_num <= self._max_page_num:
            return range(1, self.total_page_num + 1)
        else:
            half = int(self._max_page_num/2)
            if self._current_page <= half:
                return range(1, self._max_page_num+1)
            else:
                if (self._current_page + half) > self.total_page_num:
                    return range(self.total_page_num - self._max_page_num + 1, self.total_page_num + 1)
                else:
                    return range(self._current_page - half, self._current_page + half + 1)

    def page_html(self):
        if self.total_page_num <= 1:
            return ""
        else:
            tmp_list = ['<nav aria-label="Page navigation" class="text-center"><ul class="pagination">']
            show_page_list = self.page_show_range()
            if 1 not in show_page_list:
                tmp_list.append('<li><a href="%s?page=%s">首页</a></li>' %(self._url, 1))
            pre_page = self._current_page - 1
            if pre_page <= 0:
                pass
                # pre_page_str = '<li class="disabled"><a  href="jacascript:void(0)" aria-label="Previous"><span aria-hidden="true">' \
                #                '上一页</span></a></li>'
            else:
                pre_page_str = '<li><a href="%s?page=%s" aria-label="Previous"><span aria-hidden="true">' \
                               '上一页</span></a></li>' %(self._url, pre_page)
                tmp_list.append(pre_page_str)
            for item in show_page_list:
                if item == self._current_page:
                    tmp_str = '<li class="active"><a href="%s?page=%s">%s</a></li>' %(self._url, item, item)
                else:
                    tmp_str = '<li ><a href="%s?page=%s">%s</a></li>' % (self._url, item, item)
                tmp_list.append(tmp_str)
            next_page = self._current_page + 1
            if next_page > self.total_page_num:
                # next_page_str = '<li class="disabled"><a href="jacascript:void(0)" aria-label="Next"><span aria-hidden="true">' \
                #                 '下一页</span></a></li>'
                pass
            else:
                next_page_str = '<li><a href="%s?page=%s" aria-label="Next"><span aria-hidden="true">' \
                                '下一页</span></a></li>' %(self._url, next_page)
                tmp_list.append(next_page_str)
            if self.total_page_num not in show_page_list:
                tmp_list.append('<li><a href="%s?page=%s">尾页</a></li>' % (self._url, self.total_page_num))
            tmp_list.append('</ul></nav>')
            return ''.join(tmp_list)

