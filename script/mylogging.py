#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/3/7 14:40
    @FileName: mylogging.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
import logging
from logging.handlers import RotatingFileHandler


def logger(logger_name, Log_path, level='INFO'):
    try:
        handler = RotatingFileHandler(Log_path, maxBytes=1024*1024*100, backupCount=100, encoding='utf-8')
        fmt = '[%(levelname)s -%(name)s - %(lineno)d - %(asctime)s ]- %(message)s'
        fmtobj = logging.Formatter(fmt)
        handler.setFormatter(fmtobj)
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        if not logger.handlers:
            logger.addHandler(handler)
    except Exception, e:
        return False
    else:
        return logger