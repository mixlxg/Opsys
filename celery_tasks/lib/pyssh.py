#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    @author:吕秀刚
    @createdtime:2019/5/15 10:46
    @FileName: pyssh.py
    @Software: PyCharm
"""
from __future__ import unicode_literals, absolute_import, division
import paramiko
from paramiko import SSHException


class PySsh(object):

    def __init__(self, ip, username, paswword, port=22):
        self._ip = ip
        self._username = username
        self._password = paswword
        self._port = port
        self.connect_status = True
        self.error = None
        self._client = self.connect()

    def connect(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self._ip, self._port, self._username, self._password, timeout=10)
        except SSHException, e:
                self.connect_status = False
                self.error = e.message
        else:
            return client

    def comm(self, comm, timeout=30):

        if self.connect_status:
            try:
                exec_comm = 'source /etc/profile && ' + comm
                stdin, stdout, stderr = self._client.exec_command(exec_comm, timeout=timeout)
            except SSHException, e:
                 return False, None, e.message
            else:
                return True, stdout.readlines(), stderr.readlines()
        else:
            raise Exception('connect failed;%s' %self.error)

    def invoke_comm(self, comm_list):
        if self.connect_status:
            try:
                channel = self._client.invoke_shell()
                buff = ''
                for com in comm_list:
                    channel.send(com + '\n')
                    while not buff.endswith('$'):
                        buff = buff + channel.recv(1024)
                    else:
                        buff = buff+'\n'
            except SSHException, e:
                return False, e.message
            else:
                return True, buff
        else:
            raise Exception('connect failed;%s' % self.error)

    def close(self):
        self._client.close()