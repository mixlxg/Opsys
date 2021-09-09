#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/3/7 16:25
    @FileName: send_mail.py
    @Software: PyCharm
"""
from __future__ import unicode_literals
from config import conf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import os


class SendMail(object):
    def __init__(self, to_user, cs_user=None):
        """
        :param to_user: type list 发送邮件给那些用户
        :param cs_user: type list 抄送邮件给那些用户，默认值为None
        """
        self.__mail_host = conf['host']
        self.__mail_port = conf['port']
        self.__user = conf['user']
        self.__mail_pass = conf['password']
        self.__to_user = to_user
        self.__cs_user = cs_user
        self.__timeout = conf['timeout']
        self.__stmpobj = None
    @property
    def connection(self):
        try:
            stmpobj = smtplib.SMTP(host=self.__mail_host, port=self.__mail_port, timeout=self.__timeout)
            stmpobj.starttls()
            stmpobj.login(user=self.__user, password=self.__mail_pass)
        except Exception, e:
            return False, e.message
        else:
            self.__stmpobj = stmpobj
            return True, '成功'

    def send(self, subject, contents, fj_name=None,  subtype='mixed'):
        """
        :param subject: type str 邮件主题
        :param contents: type str 邮件内容
        :param fj_name: type list 附件名字全路径加文件名字
        :return:返回发送结果
        """
        message = MIMEMultipart()
        message['From'] = Header(self.__user, 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')
        message['To'] = ','.join(self.__to_user)
        if self.__cs_user is not None:
            message['Cc'] = ','.join(self.__cs_user)
            self.__to_user.extend(self.__cs_user)

        if fj_name is not None:
            for fjname in fj_name:
                att = MIMEText(open(fjname, 'rb').read(), 'base64', 'utf-8')
                att["Content-Type"] = 'application/octet-stream'
                att["Content-Disposition"] = '''attachment; filename="%s"''' % os.path.basename(fjname)
                message.attach(att)
        message.attach(MIMEText(contents, subtype, 'utf-8'))

        try:
            self.__stmpobj.sendmail(self.__user, self.__to_user, message.as_string())
        except Exception, e:
            return False, e.message
        else:
            return True


if __name__ == '__main__':
    mail = SendMail(['1183566623@qq.com', 'lvxg9@chinaunicom.cn'])
    conn = mail.connection
    print conn
    if conn:
       result= mail.send('mytest', '<h1>test</h1>', subtype='html')
    else:
        print conn[1]

    print result




