# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function

import sys,os,time
import django
import threading
import csv
from datetime import datetime
from threading import  Thread
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()
import random
from devopsApp.models import Host
from django.conf import settings
import string,logging
import paramiko
from socket import *
collect_logger = logging.getLogger("django.request")

class Modifiedhostpasswd_thread(Thread):
    def __init__(self,host,login_password,modified_user,sem,login_user='root',port=22,timeout=60):
        super(Modifiedhostpasswd_thread,self).__init__()
        self.host = host
        self.login_user = login_user
        self.login_password = login_password
        self.modified_user = modified_user
        self.port = port
        self.modified_passwd = self.generate_activation_code()
        self.timeout = timeout
        self.cmd = "echo '%s' | passwd --stdin %s" % (self.modified_passwd, self.modified_user)
        self.sem = sem
        self.result = None

    def conn_scan(self):
        conn = socket(AF_INET, SOCK_STREAM)
        conn.settimeout(2)
        try:
            conn.connect((self.host, self.port))
            return True
        except Exception, e:
            collect_logger.error('%s %s is not available' % (self.host, self.port))
            return False
        finally:
            conn.close()

    def run(self):
        try:
            host_available = self.conn_scan()
            if host_available:
                    result_tuple = self.remote_execute_cmd()
                    info = [self.host,self.modified_user,self.modified_passwd,result_tuple[1]]
                    self.result = info
            else:
                collect_logger.error('%s 网络不通' % self.host)
        except Exception as e:
            collect_logger.error("修改ip %s 的%s 用户发生未知异常" %(self.host, self.modified_user ))
        finally:
            self.sem.release()

    @property
    def get_result(self):
        return self.result

    @staticmethod
    def generate_activation_code(n=16):
        SpecialChar = "&!@#$%^-_=[]()^+:~"  #特殊字符
        upper = string.ascii_uppercase   #大写字母
        lower = string.ascii_lowercase   #小写字母
        digital = string.digits    #数字
        password = random.sample(SpecialChar, 4) + random.sample(upper, 4) + random.sample(lower, 4) + random.sample(digital, 4)
        random.shuffle(password)
        return ''.join(password)

    @staticmethod
    def get_host_info():
        info = []
        try:
            host_list = Host.objects.all().exclude(ip__in=['192.200.239.187', '192.200.175.18','192.200.251.21','192.200.251.22','192.200.251.23','192.200.251.24']).values('ip', 'hostname', 'root_password')
        except Exception, e:
            collect_logger.error('查询数据库失败：%s' % e.args[1])
        else:
            if host_list.exists():
                for host in host_list:
                    info.append(dict(ip=host['ip'], hostname=host['hostname'],
                                     root_password=host['root_password']))
        return info


    def remote_execute_cmd(self):
        try:
            with paramiko.SSHClient() as client:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(self.host,self.port,self.login_user, password=self.login_password,timeout=self.timeout)
                stdin,stdout,stderr = client.exec_command(self.cmd)
                stdout = stdout.readlines()
                if 'successfully' in ' '.join(stdout):
                    return True,  'success'
                else:
                    return False, 'failed'
        except Exception,e:
            collect_logger.error("执行命令失败,错误信息是:%s" % e.args[0])
            return False, 'failed'


    def save_newpassword_to_mysql(self):
        try:
            Host.objects.filter(ip=self.host).update(root_password=self.modified_passwd)
        except Exception, e:
            collect_logger.error('更新数据库失败：%s' % e.args[1])
            return False
        else:
            return True

    @staticmethod
    def write_to_csv(*args):
        header = ['主机ip'.encode('gbk'),'用户名'.encode('gbk'), '密码'.encode('gbk'), '修改状态'.encode('gbk')]
        filename = settings.BASE_DIR +'/execl/host_password_file/passwords' + datetime.now().strftime('%Y%m%d%H%M%S') + '.csv'
        with open(filename,'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)
            writer.writerows(args)
        return filename.split('/')[-1]


def main(modified_users=None):
    all_threads = []
    result_list = []
    sem = threading.Semaphore(10)
    all_hosts = Modifiedhostpasswd_thread.get_host_info()
    for m_u in modified_users:
        for host in all_hosts:
            ip = host['ip']
            login_password = host['root_password']
            collect_logger.info('开始修改ip：%s的%s用户密码' %(ip,m_u))
            sem.acquire()
            mp = Modifiedhostpasswd_thread(ip,login_password,m_u,sem)
            mp.start()
            all_threads.append(mp)

    for t in all_threads:
        if t.is_alive():
            t.join()
        res = t.get_result

        if res:
            if res[1] == 'root' and res[3] == 'success':
                t.save_newpassword_to_mysql()
            result_list.append(res)
    else:
        filename = Modifiedhostpasswd_thread.write_to_csv(*result_list)
        return filename, result_list


if __name__ == '__main__':
    print(main(modified_users=['root', 'webapp']))
