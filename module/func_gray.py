#!/usr/bin/env python3
# -*- coding:utf-8 -*-


# import
import os
import sys
import re
import time
import json
import module.database as db
import module.func_transform as tr

# global var
global group
global app
global db
global gray_system_root
global saltstack_root
global openresty_root
global openresty_host
# configure
gray_system_root = '/usr/local/unsops'
saltstack_root = '/srv/salt'
openresty_root = '/usr/local/openresty'
openresty_host = ['172.22.27.103', '172.22.27.104']


class application_group(object):

    def __init__(self, name):
        self.name = name

    def info(self):
        group_data = gray_cmd_sql("group_info", self.name)[1][0]
        print("{group_name}: {domain_name}".format(group_name=group_data[1], domain_name=group_data[2]))

    def group_add(self, domain):
        gray_cmd_sql("groupadd", self.name, domain)
        create_nginx_vhost(self, domain)

    def group_del(self):
        gray_cmd_sql("groupdel", self.name)
        remove_nginx_vhost(self)

    def app_add(self, app, ip_hash):
        gray_cmd_sql("appadd", self.name, app.name, ip_hash)
        db.execute("redis", "set", (self.name + "#" + app.name, 0))
        create_nginx_local(self, app)

    def app_del(self, app):
        gray_cmd_sql("appdel", self.name, app.name)
        db.execute("redis", "del", self.name + "#" + app.name)
        remove_nginx_local(self, app)

    def app_mod(self, app):
        gray_cmd_sql("appmod", self.name, app.name, app.ip_hash)
        sql = '''SELECT hosts FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=self.name, app_name=app.name)
        app.hosts = json.loads(db.execute("mysql", "search", sql)[0][0])


class application(object):

    def __init__(self, name):
        self.name = name
        self.hosts = {}

    def info(self, group):
        app_data = gray_cmd_sql("app_info", group.name, self.name)[1][0]
        group.info()
        print(" --- {app_name}: hash:{ip_hash}".format(app_name=app_data[1], ip_hash=app_data[3]))
        app_dict = json.loads(app_data[4])
        for app_info in sorted(app_dict):
            print("   - {ip_addr}:{port} backup:{backup} gray:{gray}".format(ip_addr=app_info, port=app_dict[app_info]['port'],backup=app_dict[app_info]['backup'], gray=app_dict[app_info]['gray']))

    def get_ip_hash(self, group):
        sql = '''SELECT ip_hash FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=group.name, app_name=self.name)
        if db.execute("mysql", "search", sql)[0][0] == "True":
            self.ip_hash = True
        else:
            self.ip_hash = False
        return self.ip_hash

    def get_hosts(self, group):
        sql = '''SELECT hosts FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=group.name, app_name=self.name)
        self.hosts = json.loads(db.execute("mysql", "search", sql)[0][0])

    def host_add(self, group):
        gray_cmd_sql("hostadd", group.name, self.name, json.dumps(self.hosts))
        manage_nginx_upstream(group, self)

    def host_del(self, group):
        gray_cmd_sql("hostdel", group.name, self.name, json.dumps(self.hosts))
        manage_nginx_upstream(group, self)

    def host_mod(self, group):
        gray_cmd_sql("hostmod", group.name, self.name, json.dumps(self.hosts))
        manage_nginx_upstream(group, self)

    def gray_add(self, group):
        gray_cmd_sql("grayadd", group.name, self.name, json.dumps(self.hosts))
        manage_nginx_upstream(group, self)

    def gray_del(self, group):
        gray_cmd_sql("graydel", group.name, self.name, json.dumps(self.hosts))
        manage_nginx_upstream(group, self)


def gray_cmd(parm):
    cmd = parm[0]
    # connect database
    db.connect("mysql")
    db.connect("redis")
    # command select
    if cmd == "info":
        group_data = gray_cmd_sql("group_data")
        app_data = gray_cmd_sql("app_data")
        if len(parm) == 3:
            group = application_group(parm[1])
            app = application(parm[2])
            if app_check(group, app, 2):
                app.info(group)
        else:
            for gkey in group_data:
                print("{group_name}: {domain_name}".format(group_name=gkey[1],domain_name=gkey[2]))
                for akey in app_data:
                    if gkey[1] == akey[2]:
                        print(" --- {app_name}: hash:{ip_hash}".format(app_name=akey[1], ip_hash=akey[3]))
                        app_dict = json.loads(akey[4])
                        for app_info in sorted(app_dict):
                            print("   - {ip_addr}:{port} backup:{backup} gray:{gray}".format(ip_addr=app_info, port=app_dict[app_info]['port'], backup=app_dict[app_info]['backup'], gray=app_dict[app_info]['gray']))
    # 添加应用组
    elif cmd == "groupadd" and len(parm) == 3:  # parm: group_name domain_name
        group = application_group(parm[1])
        if not group_check(group, 0):
            if re.search(r'Y|y', input("Please confirm the group [%s] information:[Y/N] " % group.name)):
                group.group_add(parm[2])
                print("the group [%s] create successful." % group.name)
    # 删除应用组
    elif cmd == "groupdel" and len(parm) == 2:  # parm: group_name
        group = application_group(parm[1])
        if group_check(group, 1):
            if not group_use_check(group, 1):
                if re.search(r'Y|y', input("Please confirm the group [%s] information:[Y/N] " % group.name)):
                    group.group_del()
                    print("the group [%s] delete successful." % group.name)
    # 添加应用
    elif cmd == "appadd" and len(parm) == 4 and re.search(r"^[Tt]rue$|^[Ff]alse$", parm[3]):  # parm: group_name app_name ip_hash
        group = application_group(parm[1])
        app = application(parm[2])
        if re.search(r"^[Tt]rue$", parm[3]):
            app.ip_hash = True
        else:
            app.ip_hash = False
        if not app_check(group, app, 1):
            if re.search(r'Y|y', input("Please confirm the application [%s] information:[Y/N] " % app.name)):
                group.app_add(app, app.ip_hash)
                print("the application [%s] create successful." % group.name)
    # 删除应用
    elif cmd == "appdel" and len(parm) == 3:  # parm: group_name app_name
        group = application_group(parm[1])
        app = application(parm[2])
        if app_check(group, app, 0):
            app.get_hosts(group)
            if len(app.hosts) == 0:
                if re.search(r'Y|y', input("Please confirm the application [%s] information:[Y/N] " % app.name)):
                    group.app_del(app)
                    print("the application [%s] delete successful." % app.name)
            else:
                print("the application [%s] still used." % app.name)
    # 修改应用
    elif cmd == "appmod" and len(parm) == 4 and re.search(r"^[Tt]rue$|^[Ff]alse$",parm[3]):  # parm: group_name app_name ip_hash
        group = application_group(parm[1])
        app = application(parm[2])
        if re.search(r"^[Tt]rue$", parm[3]):
            app.ip_hash = True
        else:
            app.ip_hash = False
        if app_check(group, app, 0):
            if tr.str2bool(gray_cmd_sql("app_info", group.name, app.name)[1][0][3]) != app.ip_hash:
                if re.search(r'Y|y', input("Please confirm the application [%s] information:[Y/N] " % app.name)):
                    group.app_mod(app)
                    manage_nginx_upstream(group, app)
                    print("the application [%s] modify successful." % app.name)
            else:
                print("the application [%s] ip_hash is already [%s]." % (app.name, app.ip_hash))
    # 添加主机
    elif cmd == "hostadd" and len(parm) == 6 and re.search(r"^([0-9]{1,3}\.){3}([0-9]{1,3})$", parm[3]) and re.search(r"^[0-9]{1,5}$", parm[4]) and int(parm[4]) <= 65535 and re.search(r"^[Tt]rue$|^[Ff]alse$", parm[5]):  # parm: group_name app_name ip port backup
        group = application_group(parm[1])
        app = application(parm[2])
        if not host_ip_check(group, app, parm[3], 1):
            if not host_gray_check(app, 0):
                host = {}
                host['port'] = parm[4]
                if re.search(r"^[Tt]rue$", parm[5]):
                    if len(app.hosts) > 0:
                        host['backup'] = True
                    else:
                        print("the first must be an active host.")
                        exit(1)
                else:
                    host['backup'] = False
                host['gray'] = False
                app.hosts[parm[3]] = host
                app.host_add(group)
                manage_nginx_upstream(group, app)
                print("the host [%s] add successful." % parm[3])
                app.info(group)
    # 删除主机
    elif cmd == "hostdel" and len(parm) == 4:
        group = application_group(parm[1])
        app = application(parm[2])
        if host_ip_check(group, app, parm[3], 2):
            if not host_gray_check(app, 0):
                if host_backup_check(app, parm[3], 1):
                    app.host_del(group)
                    manage_nginx_upstream(group, app)
                    print("the host [%s] del successful." % parm[3])
                    app.info(group)
    # 修改主机(待定)
    elif cmd == "hostmod" and len(parm) == 5 and re.search(r"^([0-9]{1,3}\.){3}([0-9]{1,3})$", parm[3]) and re.search(r"^[Tt]rue$|^[Ff]alse$", parm[4]):
        group = application_group(parm[1])
        app = application(parm[2])
        if host_ip_check(group, app, parm[3], 2):
            if not host_gray_check(app, 0):
                if app.hosts[parm[3]]['backup'] != tr.str2bool(parm[4]):
                    app.hosts[parm[3]]['backup'] = tr.str2bool(parm[4])
                    app.host_mod(group)
                    print("modify")
                else:
                    print("exit")
    # 添加灰度
    elif cmd == "grayadd" and len(parm) == 4 and re.search(r"^([0-9]{1,3}\.){3}([0-9]{1,3})$", parm[3]):
        group = application_group(parm[1])
        app = application(parm[2])
        gray_num = 0
        if host_ip_check(group, app, parm[3], 2):
            for ip in app.hosts:
                if app.hosts[ip]['gray'] == False and app.hosts[ip]['backup'] == False:
                    gray_num += 1
            if gray_num >= 2:
                if app.hosts[parm[3]]['gray'] == False:
                    app.hosts[parm[3]]['gray'] = True
                    app.gray_add(group)
                    print("the host [%s] switch in gray successful." % parm[3])
                    app.info(group)
                else:
                    print("the host [%s] is already switch in gray." % parm[3])
            else:
                print("must be have an active host in produce.")
    # 删除灰度
    elif cmd == "graydel" and len(parm) == 4 and re.search(r"^([0-9]{1,3}\.){3}([0-9]{1,3})$", parm[3]):
        group = application_group(parm[1])
        app = application(parm[2])
        if host_ip_check(group, app, parm[3], 2):
            if app.hosts[parm[3]]['gray'] == True:
                app.hosts[parm[3]]['gray'] = False
                app.gray_del(group)
                print("the host [%s] switch out gray successful." % parm[3])
                app.info(group)
            else:
                print("the host is switch out gray.")
    # 测试配置
    elif cmd == "test":
        for ip in openresty_host:
            print(ip+":")
            if os.path.exists("/var/cache/salt/master/file_lists/roots/base.p"):
                os.remove("/var/cache/salt/master/file_lists/roots/base.p")  # 删除salt-master文件缓存
            print("    file sync failed: " + os.popen("salt '{openresty_host}' state.highstate | awk '/^Failed/{{print $2}}'".format(openresty_host=ip)).read())
            print(os.popen("salt '{openresty_host}' cmd.run 'service openresty configtest' | grep -v '^{openresty_host}'".format(openresty_host=ip)).read())




    # 更新配置
    elif cmd == "update":
        pass
        # for ip in openresty_host:
        #     print(ip+":")
        #     print(os.popen(
        #         "salt '{openresty_host}' cmd.run 'service openresty reload' | grep -v '^{openresty_host}'".format(openresty_host=ip)).read())





    # 查看测试灰度主机
    elif cmd == "grayhost":
        grayhost_data = tr.str2list(gray_cmd_sql("grayhost")[2], ",")
        if len(grayhost_data) != 0:
            print(grayhost_data)
        else:
            print("empty")
    # 添加测试灰度主机
    elif cmd == "grayhostadd" and len(parm) == 2 and re.search(r"^([0-9*]{1,3}\.){3}([0-9*]{1,3})$", parm[1]):
        grayhost_data = tr.str2list(gray_cmd_sql("grayhost")[2], ",")
        if not parm[1] in grayhost_data:
            grayhost_data.append(parm[1])
            gray_cmd_sql("grayhostadd", tr.list2str(sorted(grayhost_data),","))
            gray_ip_sync()
            print(sorted(grayhost_data))
        else:
            print("already in.")
    # 删除测试灰度主机
    elif cmd == "grayhostdel" and len(parm) == 2 and re.search(r"^([0-9*]{1,3}\.){3}([0-9*]{1,3})$", parm[1]):
        grayhost_data = tr.str2list(gray_cmd_sql("grayhost")[2], ",")
        if parm[1] in grayhost_data:
            grayhost_data.remove(parm[1])
            gray_cmd_sql("grayhostadd", tr.list2str(sorted(grayhost_data), ","))
            gray_ip_sync()
            print(sorted(grayhost_data))
        else:
            print("not exited.")










    # 灰度锁
    elif cmd == "graylock" and len(parm) == 2 and re.search(r"^[Tt]rue$|^[Ff]alse$", parm[1]):
        for ip in openresty_host:
            if tr.str2bool(parm[1]) == True:
                os.popen("salt '{openresty_host}' cmd.run 'touch /tmp/gray.lock'".format(openresty_host=ip)).read()
            else:
                os.popen("salt '{openresty_host}' cmd.run 'rm -f /tmp/gray.lock'".format(openresty_host=ip)).read()


    # 测试函数
    elif cmd == "tttt":
        gray_ip_sync()

    else:
        command_help()


    # disconnect database
    db.disconnect("mysql")


def gray_ip_sync():
    # gray host ip list
    grayhost_data = tr.str2list(gray_cmd_sql("grayhost")[2], ",")
    # app host ip list
    for host in gray_cmd_sql("app_data"):
        app_data = json.loads(host[4])
        for ip in app_data:
            if app_data[ip]['gray'] == True:
                grayhost_data.append(ip)

    # last
    db.execute("redis", "set", ("grayhost", tr.list2ngxlua(sorted(grayhost_data))))




    # graydata = []
    # # dev gray ip list
    # sql = '''SELECT host FROM grayhost'''
    # graydata = tr.str2list(gray_data_process("mysql", execute("mysql", "search", sql))[0], ",")
    # # app gray ip list
    # sql = '''SELECT gray_host FROM application'''
    # appdata = gray_data_process("mysql", execute("mysql", "search", sql))
    # if appdata:
    #     graydata.extend(appdata)
    # # sync to redis
    # execute("redis", "set", "gray_ip_list", tr.list2ngxlua(graydata))
    print(grayhost_data)


def host_ip_check(group, app, ip, tip):
    if app_check(group, app, 2):
        sql = '''SELECT hosts FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=group.name, app_name=app.name)
        app.hosts = json.loads(db.execute("mysql", "search", sql)[0][0])
        if app.hosts.get(ip):
            if tip == 1:
                print("the host [%s] has already existed." % ip)
            return 1
        else:
            if not tip or tip == 2:
                print("the host [%s] not existed." % ip)
            return 0


def host_backup_check(app, ip, tip):
    if app.hosts[ip]['backup'] == False:
        app.hosts.pop(ip)
        if len(app.hosts) != 0:
            for akey in app.hosts:
                if app.hosts[akey]['backup'] == False:
                    return 1
        else:
            if re.search(r'Y|y', input("Please confirm delete the last host in the application:[Y/N] ")):
                return 1
            else:
                exit(1)
        if tip == 1:
            print("must be have an active host.")
        return 0
    else:
        app.hosts.pop(ip)
        return 1


def host_gray_check(app, tip):
    for ip in sorted(app.hosts):
        if app.hosts[ip]['gray'] == True:
            if not tip:
                print("gray status cannot add/mod/del host.")
            app.gray = True
            return 1
    else:
        app.gray = False
        return 0


def group_check(group, tip):
    sql = '''SELECT * FROM application_group WHERE `name` = \'{group_name}\''''.format(group_name=group.name)
    if db.execute("mysql", "search", sql):
        if not tip:
            print("the group [%s] has already existed." % group.name)
        return 1
    else:
        if tip:
            print("the group [%s] not existed." % group.name)
        return 0


def app_check(group, app, tip):
    if group_check(group, 1):
        sql = '''SELECT * FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=group.name,app_name=app.name)
        if db.execute("mysql", "search", sql):
            if tip == 1:
                print("this application [%s] is already in group [%s]." % (app.name, group.name))
            return 1
        else:
            if not tip or tip == 2:
                print("the application [%s] not existed." % app.name)
            return 0


def group_use_check(group, tip):
    sql = '''SELECT * FROM application WHERE `group` = \'{group_name}\''''.format(group_name=group.name)
    if db.execute("mysql", "search", sql):
        if tip:
            print("the group [%s] still used." % group.name)
        return 1
    else:
        return 0


# generate nginx configure
def create_nginx_vhost(group, domain):
    with open(gray_system_root + '/gray_system/module/template/vhost.template', 'r', encoding='UTF-8') as f:
        template = f.read().format(group=group.name, domain=domain, openresty_path=openresty_root)
    with open(saltstack_root + '/nginx/conf/vhost/' + group.name + '.conf', 'w') as f:
        f.write(template)
    if not os.path.exists(saltstack_root + '/nginx/conf/vhost/' + group.name):
        os.mkdir(saltstack_root + '/nginx/conf/vhost/' + group.name)
    if not os.path.exists(saltstack_root + '/nginx/conf/upstream/' + group.name):
        os.mkdir(saltstack_root + '/nginx/conf/upstream/' + group.name)

def remove_nginx_vhost(group):
    if os.path.exists(saltstack_root + '/nginx/conf/vhost/' + group.name + '.conf'):
        os.remove(saltstack_root + '/nginx/conf/vhost/' + group.name + '.conf')
    if os.path.exists(saltstack_root + '/nginx/conf/vhost/' + group.name):
        os.rmdir(saltstack_root + '/nginx/conf/vhost/' + group.name)
    if os.path.exists(saltstack_root + '/nginx/conf/upstream/' + group.name):
        os.rmdir(saltstack_root + '/nginx/conf/upstream/' + group.name)

def create_nginx_local(group, app):
    with open(gray_system_root + '/gray_system/module/template/local.template', 'r', encoding='UTF-8') as f:
        template = f.read().format(upstream_name=app.name, app_name=group.name + "#" + app.name, openresty_path=openresty_root)
    with open(saltstack_root + '/nginx/conf/vhost/' + group.name + '/' + app.name + '.conf', 'w') as f:
         f.write(template)

def remove_nginx_local(group, app):
    if os.path.exists(saltstack_root + '/nginx/conf/vhost/' + group.name + '/' + app.name + '.conf'):
        os.remove(saltstack_root + '/nginx/conf/vhost/' + group.name + '/' + app.name + '.conf')


def manage_nginx_upstream(group, app):
    app.get_ip_hash(group)
    host_gray_check(app, 1)
    if len(app.hosts) != 0:
        # generate upstream
        with open(saltstack_root + '/nginx/conf/upstream/' + group.name + '/' + app.name + '.conf', 'w') as f:
            for ups_type in ['allserver', 'produce', 'develop']:
                ups_temp = "# {ups_type}\n".format(ups_type=ups_type)
                ups_temp += "upstream {ups_type}#{group_name}#{app_name} {{\n".format(ups_type=ups_type,group_name=group.name, app_name=app.name)
                if ups_type != "develop" and app.ip_hash == True:
                    ups_temp += "    ip_hash;\n"
                for ip in sorted(app.hosts):
                    server_temp = "    server {ip}:{port}".format(ip=ip, port=app.hosts[ip]['port'])
                    if ups_type != "develop":
                        if ups_type == "allserver" or ups_type == "produce" and app.hosts[ip]['gray'] == False:

                            if app.hosts[ip]['backup'] == True:
                                if app.ip_hash == False:
                                    ups_temp += server_temp + " backup;\n"
                            else:
                                ups_temp += server_temp + ";\n"
                    else:
                        if app.hosts[ip]['gray'] == True:
                            ups_temp += server_temp + ";\n"
                if ups_type != "develop" or ups_type == "develop" and app.gray == True:
                    # print(ups_temp + "}\n")
                    f.write(ups_temp + "}\n")
    else:
        if os.path.exists(saltstack_root + '/nginx/conf/upstream/' + group.name + '/' + app.name + '.conf'):
            os.remove(saltstack_root + '/nginx/conf/upstream/' + group.name + '/' + app.name + '.conf')



def gray_cmd_sql(cmd, *parm):
    if cmd == "app_info":
        sql = '''SELECT * FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1])
        return "mysql", db.execute("mysql", "search", sql)

    elif cmd == "group_info":
        sql = '''SELECT * FROM application_group WHERE `name` = \'{group_name}\''''.format(group_name=parm[0])
        return "mysql", db.execute("mysql", "search", sql)

    elif cmd == "app_data":
        sql = '''SELECT * FROM application'''
        return db.execute("mysql", "search", sql)

    elif cmd == "group_data":
        sql = '''SELECT * FROM application_group'''
        return db.execute("mysql", "search", sql)
    # 添加应用组
    elif cmd == "groupadd":
        sql = '''INSERT INTO application_group(name,domain) VALUES (\'{group_name}\',\'{group_domain}\')'''.format(group_name=parm[0],group_domain=parm[1])
        return db.execute("mysql", "insert", sql)
    # 删除应用组
    elif cmd == "groupdel":
        sql = '''DELETE FROM application_group WHERE name = \'{group_name}\''''.format(group_name=parm[0])
        return db.execute("mysql", "delete", sql)
    # 添加应用
    elif cmd == "appadd":
        sql = '''INSERT INTO application(name,`group`,ip_hash) VALUES (\'{app_name}\',\'{group_name}\',\'{ip_hash}\')'''.format(group_name=parm[0],app_name=parm[1],ip_hash=parm[2])
        return db.execute("mysql", "insert", sql)
    # 删除应用
    elif cmd == "appdel":
        sql = '''DELETE FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1])
        return db.execute("mysql", "delete", sql)
    # 修改应用
    elif cmd == "appmod":
        sql = '''UPDATE application SET ip_hash = \'{ip_hash}\' WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1],ip_hash=parm[2])
        return db.execute("mysql", "update", sql)
    # 添加主机, 删除主机, 修改主机, 添加灰度, 删除灰度
    elif re.search(r'^hostadd$|^hostdel$|^hostmod$|^grayadd$|^graydel$', cmd):
        sql = '''UPDATE application SET hosts = \'{hosts_data}\' WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1],hosts_data=parm[2])
        return db.execute("mysql", "update", sql)


    # 灰度主机
    elif cmd == "grayhost":
        sql = '''SELECT * FROM grayhost WHERE name = \'global\''''
        return db.execute("mysql", "search", sql)[0]

    elif cmd == "grayhostadd":
        sql = '''UPDATE grayhost SET `hosts` = \'{hosts_data}\' WHERE `name` = \'global\''''.format(hosts_data=parm[0])
        return db.execute("mysql", "update", sql)

    elif cmd == "devget":
        sql = '''SELECT * FROM grayhost WHERE type = \'{app_name}\''''.format(app_name=parm[0])
        return gray_data_process("mysql", db.execute("mysql", "search", sql))

    elif cmd == "devset":
        sql = '''UPDATE grayhost SET {host_type} = \'{host}\' WHERE type = \'{app_name}\''''.format(host=parm[2],app_name=parm[0],host_type=parm[1])
        return db.execute("mysql", "update", sql)





# command help
def command_help():
    print('''
    Usage: gray-cli COMMAND [OPTION]...

    List of Commands:
    
    info [GROUP_NAME] [APP_NAME]
    
    groupadd GROUP_NAME DOMAIN_NAME             -- e.g. groupadd test_unspay_com test.unspay.com
    groupdel GROUP_NAME                         -- e.g. groupdel test_unspay_com
    
    appadd GROUP_NAME APP_NAME IP_HASH          -- e.g. appadd test_unspay_com small_agent_web false
    appdel GROUP_NAME APP_NAME                  -- e.g. appdel test_unspay_com small_agent_web
    appmod GROUP_NAME APP_NAME IP_HASH          -- e.g. appmod test_unspay_com small_agent_web true
    
    hostadd GROUP_NAME APP_NAME IP PORT BACKUP  -- e.g. hostadd test_unspay_com small_agent_web 172.22.27.103 8081 false
    hostdel GROUP_NAME APP_NAME IP              -- e.g. hostadd test_unspay_com small_agent_web 172.22.27.103
    
    grayadd GROUP_NAME APP_NAME IP              -- e.g. hostadd test_unspay_com small_agent_web 172.22.27.104
    graydel GROUP_NAME APP_NAME IP              -- e.g. hostadd test_unspay_com small_agent_web 172.22.27.105
        
    test
    update
    
    graylock
    ''')
