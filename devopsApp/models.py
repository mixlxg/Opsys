# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import AbstractUser,UserManager
import datetime
# Create your models here.


class MyUserManger(UserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role_id', 1)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role_id',2)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


class MyUser(AbstractUser):
    role = models.ForeignKey('Role')
    objects = MyUserManger()

    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'


class Role(models.Model):
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField('Permissions')


class Permissions(models.Model):
    url = models.CharField(max_length=255, unique=True)


class Host(models.Model):
    """
    ip:主机地址
    ov_version: 操作系统
    hostname:主机名
    net_card_mes:网卡信息
    cpu_num: cpu 核数
    cpu_model: cpu 类型
    mem_total: 内存总大小单位 字节
    dis_num: 磁盘块数
    disk_mes 每块盘的信息
    disk_total_valume: 主机磁盘总大小，单位字节
    """
    ip = models.CharField(max_length=255, unique=True)
    os_version = models.CharField(max_length=255, blank=True)
    hostname = models.CharField(max_length=255, blank=True)
    net_card_mes = models.CharField(max_length=255, blank=True)
    cpu_num = models.IntegerField(default=0)
    cpu_model = models.CharField(max_length=255, blank=True)
    mem_total = models.BigIntegerField(default=0)
    disk_num = models.IntegerField(default=0)
    disk_mes = models.CharField(max_length=255, blank=True)
    disk_total_volume = models.BigIntegerField(default=0)
    root_password = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.ip


class Project(models.Model):
    project_name = models.CharField(max_length=255)
    project_description = models.CharField(max_length=255, blank=True)


class Service(models.Model):
    """
    service_name:服务名
    type 服务类型
    service_port 服务器端口
    jmx_port jmx端口
    online_date 上线时间
    offline_date 下线时间
    base_path 工程目录
    package_name 打包名称
    status 应用状态 choices=('online', 'offline', 'wait_online')
    start_script 启动脚本
    stop_scrip 关闭脚本
    log_path 日志目录
    service_conf_name：jenkins打包 应用需要使用的配置文件目录
    jenkin_service_conf_name：jenkin 打包中用到的配置文件
    host 多对多对象
    package_deploy_path 程序解压包的目录，或者jar的存放目录
    """
    service_name = models.CharField(max_length=255)
    service_alias_name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=128)
    service_port = models.IntegerField()
    jmx_port = models.IntegerField(default=0)
    online_date = models.DateTimeField(default=datetime.datetime.now())
    offline_date = models.DateTimeField(blank=True, null=True)
    base_path = models.CharField(max_length=255, blank=True)
    package_deploy_path = models.CharField(max_length=255, default=None)
    package_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20)
    start_script = models.CharField(max_length=255, blank=True)
    stop_script = models.CharField(max_length=255, blank=True)
    log_path = models.CharField(max_length=255, blank=True)
    service_conf_name = models.CharField(max_length=255, blank=True)
    jenkin_service_conf_name = models.CharField(max_length=255, blank=True)
    host = models.ManyToManyField("Host")
    project_name = models.ForeignKey("Project", default=1)

    def __str__(self):
        return self.service_name


class BizlogAuth(models.Model):
    username = models.CharField(max_length=50)
    ip = models.CharField(max_length=100, null=True)
    login_time = models.DateTimeField()
    logout_time = models.DateTimeField()


class ZookeeperList(models.Model):
    clustername = models.CharField(max_length=100)
    ip = models.CharField(max_length=255)
    base_path = models.CharField(max_length=100,null=True)
    version = models.CharField(max_length=100, null=True)


class KafkaList(models.Model):
    clustername = models.CharField(max_length=100)
    ip = models.CharField(max_length=255)
    base_path = models.CharField(max_length=100,null=True)
    version = models.CharField(max_length=100, null=True)
    zk = models.ForeignKey(ZookeeperList)


class Jobs(models.Model):
    username = models.CharField(max_length=100)
    job_type = models.CharField(max_length=100)
    job_id = models.CharField(max_length=100)
    post_data = models.TextField()


class Redis(models.Model):
    clustername = models.CharField(max_length=100)
    deploy_type = models.CharField(max_length=100)
    ipaddr = models.TextField(max_length=500)
    base_path = models.CharField(max_length=50)
    version = models.CharField(max_length=20)
    password = models.CharField(max_length=128)


class RedisExecLog(models.Model):
    username = models.CharField(max_length=50)
    exec_time = models.DateTimeField()
    exec_com = models.TextField(max_length=4000)
    exec_result = models.TextField(max_length=4000)
    cluster = models.ForeignKey("Redis", default=1)


class JenkinsDeployLog(models.Model):
    """
    username: 用户名
    deploy_project: 发布项目名称
    deploy_status: 发布状态（deploy,rollback)
    deploy_start_time: 发布开始时间
    deploy_end_time: 发布结束时间
    deploy_result: 发布结果（成功，失败，回滚）
    deploy_error_mess:发布错误信息
    """
    username = models.CharField(max_length=100)
    deploy_project = models.CharField(max_length=255)
    deploy_package_md5 = models.CharField(max_length=100)
    deploy_status = models.CharField(max_length=20)
    deploy_start_time = models.DateTimeField(default=datetime.datetime.now())
    deploy_end_time = models.DateTimeField(blank=True, null=True)
    deploy_result = models.CharField(max_length=20)
    deploy_error_mess = models.CharField(max_length=255, blank=True)


class DeployTimeControl(models.Model):
    type = models.CharField(max_length=20)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()


class JenkinsDeploy(models.Model):
    """
    username: 用户名
    deploy_project: 发布项目名称：
    """
    username = models.CharField(max_length=100)
    deploy_project = models.CharField(max_length=100)


class DeployVersion(models.Model):
    """
    username: 用户名
    deploy_project:项目名
    deploy_time: 项目发布时间
    delpoy_md5sum: 项目md5值
    package_name: 打包名
    """
    username = models.CharField(max_length=100)
    deploy_project = models.CharField(max_length=100)
    deploy_time = models.DateTimeField(default=datetime.datetime.now())
    deploy_m5sum = models.CharField(max_length=100)
    package_name = models.CharField(max_length=255)


class StaticService(models.Model):
    """
    project_name: jenkins 发布项目名称
    tamper_resistant:防篡改（是，否）
    is_need_npm_package: 是否需要npm打包(是，否）
    npm_package_commd: npm打包命令
    source_code_path: 打包好的源代码目录
    target_code_path: 目标目录
    """
    project_name = models.CharField(max_length=50)
    tamper_resistant = models.CharField(max_length=10)
    is_need_npm_package = models.CharField(max_length=10)
    npm_package_commd = models.CharField(max_length=255, blank=True)
    source_code_path = models.CharField(max_length=100)
    target_code_path = models.CharField(max_length=100)
    status = models.CharField(max_length=20, blank=True, default='online')
    host = models.ManyToManyField("Host")


class TwolevelLeader(models.Model):
    leadername = models.CharField(max_length=50)


class OnelevelLeader(models.Model):
    groupname = models.CharField(max_length=50)
    leadername = models.CharField(max_length=50)
    leader = models.ManyToManyField(TwolevelLeader)


class DeployProjectApply(models.Model):
    """
    project_class: 项目分类（如本地商城，微信项目，华盛项目）
    project_name:发布项目名称
    deploy_username:发布用户名
    tamper_resistant_start_time:防篡改开始时间
    tamper_resistant_end_time:防篡改结束时间
    code_verify_name:代码审核人
    developers_name:研发人员
    db_op:是否需要运维操作人员留守（是，否）
    operation_need_reasons:需要运维人员留守原因
    deploy_start_time:发布开始时间
    deploy_end_time:发布结束时间
    groupleader_name:组长名称
    groupleader_agree:组长是否同意
    TwolevelLeader_name:领导名称
    TwolevelLeader_agree:领导是否同意
    tester_name: 测试人员
    """
    project_class = models.CharField(max_length=100)
    project_name = models.CharField(max_length=255)
    deploy_username = models.CharField(max_length=100)
    tamper_resistant_start_time = models.DateTimeField(blank=True, null=True)
    tamper_resistant_end_time = models.DateTimeField(blank=True, null=True)
    code_verify_name = models.CharField(max_length=100)
    developers_name = models.CharField(max_length=255)
    tester_name = models.CharField(max_length=100, blank=True)
    db_op = models.CharField(max_length=10, default='否')
    operation_need_reasons = models.CharField(max_length=255, blank=True)
    deploy_start_time = models.DateTimeField()
    deploy_end_time = models.DateTimeField()
    groupleader_name = models.CharField(max_length=100)
    groupleader_agree = models.CharField(max_length=10, blank=True)
    twolevelLeader_name = models.CharField(max_length=100, blank=True)
    twolevelLeader_agree = models.CharField(max_length=10, blank=True)
    deploy_result = models.CharField(max_length=10, blank=True)
    result = models.TextField(max_length=10000, blank=True)
    build_id = models.IntegerField(max_length=11, default=0)
    really_deploy_time = models.DateTimeField(blank=True, null=True)


class WorkOrderNeeds(models.Model):
    need_content = models.CharField(max_length=255)
    product_manager_name = models.CharField(max_length=100)
    deploy_time = models.DateField()
    need_deploy_project = models.ManyToManyField(DeployProjectApply)


class AppRestart(models.Model):
    """
    username: str,用户名全称
    service_name: str, 应用名称
    group_task_id: str,celery group id
    task_id: str, celery deploy id
    op_type: str, restart, stop, start
    """
    username = models.CharField(max_length=50)
    service_name = models.CharField(max_length=100)
    group_task_id = models.TextField(max_length=4000, default='')
    task_id = models.TextField(max_length=2000, default='')
    op_type = models.CharField(max_length=10, default='restart')


class AppOffline(models.Model):
    """
        username: str 正在下线应用的用户名
        service_name: str 项目名称
        group_task_id: str 批量下线应用的task_id 信息集合
        task_id 下线单个节点的task_id信息
    """
    username = models.CharField(max_length=50)
    service_name = models.CharField(max_length=100)
    group_task_id = models.TextField(max_length=4000, default='')
    task_id = models.TextField(max_length=2000, default='')


class MysqlSlowLog(models.Model):
    host = models.CharField(max_length=50)
    remote_host = models.CharField(max_length=50, blank=True)
    query_time = models.DateTimeField()
    sql_exc_time = models.FloatField()
    sql_lock_time = models.FloatField()
    sql_rows_examined = models.IntegerField(max_length=10)
    sql_text = models.CharField(max_length=2000)


class HostPowerApply(models.Model):
    """
    is_agree: null 表示待审批，0表示审批成功，1表示拒绝，2表示审批刷权限失败
    """
    username = models.CharField(max_length=50)
    service_name = models.CharField(max_length=2000)
    apply_time = models.DateTimeField(default=datetime.datetime.now())
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    apply_reason = models.CharField(max_length=1000)
    is_agree = models.IntegerField(max_length=2, null=True)
    apply_result = models.CharField(max_length=250, blank=True)


class mysqldeadlock_log(models.Model):
    deadlock_id = models.DateTimeField(verbose_name="死锁时间",null=True)
    deadlock_transaction_content = models.TextField(verbose_name='事务内容',null=True)
    create_date = models.DateTimeField(auto_now_add=True, verbose_name="创建时间",null=True)


class DbClusterInfo(models.Model):
    """
    cluster_name: 集群名称
    version: 数据库版本
    db_type: 数据库类型
    service_name: 当db_type 为oracle时候需要填写的服务名称
    username: 用于操作这个集群的相同的用户名
    password: 用户密码
    """
    cluster_name = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    db_type = models.CharField(max_length=10)
    service_name = models.CharField(max_length=50, blank=True)
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=100)


class DbNodeInfo(models.Model):
    """
    host_ip:主机地址
    conf_path: 数据库配置文件，当为oracle时候可以不填
    service_port: 数据库提供服务的端口
    role:数据的角色。mysql（master|slave） oracle（rac）
    """
    host_ip = models.CharField(max_length=50)
    conf_path = models.CharField(max_length=150)
    base_path = models.CharField(max_length=150)
    service_port = models.IntegerField(max_length=10)
    role = models.CharField(max_length=10)
    cluster_name = models.ForeignKey("DbClusterInfo")


class DbSqlApplyResult(models.Model):
    """
    username: 申请执行sql用户名
    cluster_name: 数据库集群名称
    schema_name: 数据库schema名称
    apply_time:生气sql工单时间，入库时自动创建
    group_leader: 组长名称
    group_leader_agree: 组长是否同意（同意|不同意）
    db_agree: dba 是否同意（同意|不同意）
    dba_not_agree_reson： dba不同意原因
    is_dba_exec: sql是否由dba来执行(是|否)
    sql: 用户写的sql
    is_success: sql是否执行成功（成功|失败）
    start_exec_time: 执行sql的开始时间
    end_exec_time: sql执行结束时间
    result: sql执行结果
    """
    username = models.CharField(max_length=50)
    cluster_name = models.CharField(max_length=50)
    schema_name = models.CharField(max_length=50)
    apply_reson = models.CharField(max_length=255,blank=True)
    apply_time = models.DateTimeField(default=datetime.datetime.now())
    group_leader = models.CharField(max_length=50)
    group_leader_agree = models.CharField(max_length=50, blank=True)
    dba_agree = models.CharField(max_length=50, blank=True)
    dba_not_agree_reson = models.CharField(max_length=1000)
    is_dba_exec = models.CharField(max_length=10, blank=True)
    sql = models.TextField()
    is_success = models.CharField(max_length=10)
    start_exec_time = models.DateTimeField(blank=True, null=True)
    end_exec_time = models.DateTimeField(blank=True, null=True)
    result = models.TextField()

class K8sApp(models.Model):
    """
    :param service_name 应用名称
    :param type 应用类型如java python等
    :param online_date 上线时间
    :param offline_date 下线时间
    :param package_name maven 打好的报名，绝对路径
    :param status 当前服务的状态
    :param dockerfile_path dockerfile目录
    :param deploy_yaml kubectl发布yaml文件
    """
    service_name = models.CharField(max_length=255)
    type = models.CharField(max_length=128)
    online_date = models.DateTimeField(default=datetime.datetime.now())
    offline_date = models.DateTimeField(blank=True, null=True)
    package_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20)
    dockerfile_path = models.CharField(max_length=100)
    latest_image = models.CharField(max_length=100)
    deploy_yaml = models.CharField(max_length=100)
    project_name = models.ForeignKey("Project", default=1)





