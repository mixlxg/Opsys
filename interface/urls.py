# -*- coding:utf-8 -*-
from django.conf.urls import url
from interface import views
urlpatterns = [
    url(r'^zabbix_service_discovery$', views.ZabbixServiceDiscovery.as_view(), name='zabbix_service_discovery'),
    url(r'^ServiceQueryApi/$', views.ServiceQueryApi.as_view(), name='ServiceQueryApi'),
    url(r'^MysqlSlowLogApi/$', views.MysqlSlowLogApi.as_view(), name='MysqlSlowLogApi'),
    url(r'^redis_configfile_discovery/$', views.redisconfigfileDiscovery.as_view(), name='redis_configfile_discovery'),
    url(r'^kafka_configfile_discovery/$', views.kafkaconfigfileDiscovery.as_view(), name='kafka_configfile_discovery'),
    url(r'^zookeeper_configfile_discovery/$',views.zookeeperconfigfileDiscovery.as_view(), name='zookeeper_configfile_discovery'),

]
