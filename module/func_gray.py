#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#####################################################################################################################
#   Gray System                                                                                 Create 2018/07/26   #
#   Author Annda Ver 1.0.0                                                                      Update 2018/10/16   #
#####################################################################################################################

# import
import os
import sys
import re
import time
import json
import module.database as ModDB
import module.func_translate as ModTransl

# global var
global graySystemRoot, saltstackRoot, openrestyRoot, openrestyHost
# configure
graySystemRoot = '/usr/local/unsops'
saltstackRoot = '/srv/salt'
openrestyRoot = '/usr/local/openresty'
openrestyHost = ['172.22.27.103', '172.22.27.104']


# function gray command
def GrayCmd(cmdParm):
    # var grayCmd
    grayCmd = cmdParm[0]
    # remove grayCmd
    del cmdParm[0]
    # connect database
    ModDB.Connect("mysql")
    ModDB.Connect("redis")
    # command select
    # 打印应用信息
    if grayCmd == "info":
        groupData = GrayCmdSql("group_data")
        appData = GrayCmdSql("app_data")
        if len(cmdParm) == 1:
            groupName = cmdParm[0]
            if GroupCheck(groupName, 1):
                PrintGroupInfo(groupName)
                for aKey in appData:
                    if groupName == aKey[2]:
                        PrintAppInfo(groupName, aKey[1])
        elif len(cmdParm) == 2:
            groupName = cmdParm[0]
            appName = cmdParm[1]
            if AppCheck(groupName, appName, 2):
                PrintGroupInfo(groupName)
                PrintAppInfo(groupName, appName)
        else:
            for gkey in groupData:
                print("{group_name}: {domain_name}".format(group_name=gkey[1],domain_name=gkey[2]))
                for akey in appData:
                    if gkey[1] == akey[2]:
                        print(" --- {app_name}: hash:{ip_hash}".format(app_name=akey[1], ip_hash=akey[3]))
                        app_dict = json.loads(akey[4])
                        for app_info in sorted(app_dict):
                            print("   - {ip_addr}:{port} backup:{backup} gray:{gray}".format(ip_addr=app_info, port=app_dict[app_info]['port'], backup=app_dict[app_info]['backup'], gray=app_dict[app_info]['gray']))
    # 添加应用组
    elif grayCmd == "groupadd" and len(cmdParm) == 2:  # Parm: GROUP_NAME DOMAIN_NAME
        groupName = cmdParm[0]
        groupDomain = cmdParm[1]
        if not GroupCheck(groupName, 0):
            if re.search(r'Y|y', input("Please confirm the group [%s] information:[Y/N] " % groupName)):
                GrayCmdSql(grayCmd, groupName, groupDomain)
                CreateNginxVHost(groupName, groupDomain)
                print("the group [%s] create successful." % groupName)
    # 删除应用组
    elif grayCmd == "groupdel" and len(cmdParm) == 1:  # Parm: GROUP_NAME
        groupName = cmdParm[0]
        if GroupCheck(groupName, 1):
            if not GroupUseCheck(groupName, 1):
                if re.search(r'Y|y', input("Please confirm the group [%s] information:[Y/N] " % groupName)):
                    GrayCmdSql(grayCmd, groupName)
                    RemoveNginxVHost(groupName)
                    print("the group [%s] delete successful." % groupName)
    # 添加应用
    elif grayCmd == "appadd" and len(cmdParm) == 3 and re.search(r"^[Tt]rue$|^[Ff]alse$", cmdParm[2]):  # Parm: GROUP_NAME APP_NAME IP_HASH
        groupName = cmdParm[0]
        appName = cmdParm[1]
        appIpHash = ModTransl.Str2Bool(cmdParm[2])
        if not AppCheck(groupName, appName, 1):
            if re.search(r'Y|y', input("Please confirm the application [%s] information:[Y/N] " % appName)):
                GrayCmdSql(grayCmd, groupName, appName, appIpHash)
                ModDB.Execute("redis", "set", (groupName + "#" + appName, 0))
                CreateNginxLocal(groupName, appName)
                print("the application [%s] create successful." % groupName)
    # 删除应用
    elif grayCmd == "appdel" and len(cmdParm) == 2:  # Parm: group_name app_name
        groupName = cmdParm[0]
        appName = cmdParm[1]
        if AppCheck(groupName, appName, 0):
            appHosts = json.loads(GrayCmdSql("app_hosts", groupName, appName)[0][0])
            if len(appHosts) == 0:
                if re.search(r'Y|y', input("Please confirm the application [%s] information:[Y/N] " % appName)):
                    GrayCmdSql(grayCmd, groupName, appName)
                    ModDB.Execute("redis", "del", groupName + "#" + appName)
                    RemoveNginxLocal(groupName, appName)
                    print("the application [%s] delete successful." % appName)
            else:
                print("the application [%s] still used." % appName)
    # 修改应用
    elif grayCmd == "appmod" and len(cmdParm) == 3 and re.search(r"^[Tt]rue$|^[Ff]alse$",cmdParm[2]):  # Parm: GROUP_NAME APP_NAME IP_HASH
        groupName = cmdParm[0]
        appName = cmdParm[1]
        appIpHash = ModTransl.Str2Bool(cmdParm[2])
        if AppCheck(groupName, appName, 0):
            if ModTransl.Str2Bool(GrayCmdSql("app_info", groupName, appName)[1][0][3]) != appIpHash:
                if re.search(r'Y|y', input("Please confirm the application [%s] information:[Y/N] " % appName)):
                    GrayCmdSql(grayCmd, groupName, appName, appIpHash)
                    ManageNginxUpstream(groupName, appName)
                    print("the application [%s] modify successful." % appName)
            else:
                print("the application [%s] ip_hash is already [%s]." % (appName, appIpHash))
    # 添加主机
    elif grayCmd == "hostadd" and len(cmdParm) == 5 and re.search(r"^([0-9]{1,3}\.){3}([0-9]{1,3})$", cmdParm[2]) and re.search(r"^[0-9]{1,5}$", cmdParm[3]) and int(cmdParm[3]) <= 65535 and re.search(r"^[Tt]rue$|^[Ff]alse$", cmdParm[4]):  # Parm: GROUP_NAME APP_NAME IP PORT BACKUP
        groupName = cmdParm[0]
        appName = cmdParm[1]
        appIP = cmdParm[2]
        appPort = cmdParm[3]
        appBackup = ModTransl.Str2Bool(cmdParm[4])
        if not HostIpCheck(groupName, appName, appIP, 1):
            appHosts = json.loads(GrayCmdSql("app_hosts", groupName, appName)[0][0])
            if not HostGrayCheck(appName, appHosts, 0):
                host = {}
                host['port'] = appPort
                if appBackup:
                    if len(appHosts) > 0:
                        host['backup'] = True
                    else:
                        print("the first must be an active host.")
                        exit(1)
                else:
                    host['backup'] = False
                host['gray'] = False
                appHosts[appIP] = host
                GrayCmdSql(grayCmd, groupName, appName, json.dumps(appHosts))
                ManageNginxUpstream(groupName, appName)
                print("the host [%s] add successful." % appIP)
                PrintAppInfo(groupName, appName)
    # 删除主机
    elif grayCmd == "hostdel" and len(cmdParm) == 3:
        groupName = cmdParm[0]
        appName = cmdParm[1]
        appIP = cmdParm[2]
        if HostIpCheck(groupName, appName, appIP, 2):
            appHosts = json.loads(GrayCmdSql("app_hosts", groupName, appName)[0][0])
            if not HostGrayCheck(appName, appHosts, 0):
                if HostBackupCheck(appName, appHosts, appIP, 1):
                    GrayCmdSql(grayCmd, groupName, appName, json.dumps(appHosts))
                    ManageNginxUpstream(groupName, appName)
                    print("the host [%s] del successful." % appIP)
                    PrintAppInfo(groupName, appName)
    # 修改主机
    elif grayCmd == "hostmod" and len(cmdParm) == 4 and re.search(r"^([0-9]{1,3}\.){3}([0-9]{1,3})$", cmdParm[2]) and re.search(r"^[Tt]rue$|^[Ff]alse$", cmdParm[3]):
        groupName = cmdParm[0]
        appName = cmdParm[1]
        appIP = cmdParm[2]
        appBackup = ModTransl.Str2Bool(cmdParm[3])
        if HostIpCheck(groupName, appName, appIP, 2):
            appHosts = json.loads(GrayCmdSql("app_hosts", groupName, appName)[0][0])
            # if not HostGrayCheck(appName, appHosts, 0):
            if appHosts[appIP]['backup'] != appBackup:
                appHosts[appIP]['backup'] = appBackup
                GrayCmdSql(grayCmd, groupName, appName, json.dumps(appHosts))
                ManageNginxUpstream(groupName, appName)
                print("the host [%s] modify successful." % appIP)
            else:
                print("the host [%s] backup state is already [%s]." % (appIP, appBackup))
            PrintAppInfo(groupName, appName)
    # 添加灰度
    elif grayCmd == "grayadd" and len(cmdParm) == 3 and re.search(r"^([0-9]{1,3}\.){3}([0-9]{1,3})$", cmdParm[2]):
        groupName = cmdParm[0]
        appName = cmdParm[1]
        appIP = cmdParm[2]
        grayNum = 0
        if HostIpCheck(groupName, appName, appIP, 2):
            appHosts = json.loads(GrayCmdSql("app_hosts", groupName, appName)[0][0])
            for IP in appHosts:
                if appHosts[IP]['gray'] == False and appHosts[IP]['backup'] == False:
                    grayNum += 1
            if grayNum >= 2:
                if appHosts[appIP]['gray'] == False:
                    appHosts[appIP]['gray'] = True
                    GrayCmdSql(grayCmd, groupName, appName, json.dumps(appHosts))
                    ManageNginxUpstream(groupName, appName)
                    print("the host [%s] switch in gray successful." % appIP)
                    PrintAppInfo(groupName, appName)
                else:
                    print("the host [%s] is already switch in gray." % appIP)
            else:
                print("must be have an active host in produce.")
    # 删除灰度
    elif grayCmd == "graydel" and len(cmdParm) == 3 and re.search(r"^([0-9]{1,3}\.){3}([0-9]{1,3})$", cmdParm[2]):
        groupName = cmdParm[0]
        appName = cmdParm[1]
        appIP = cmdParm[2]
        if HostIpCheck(groupName, appName, appIP, 2):
            appHosts = json.loads(GrayCmdSql("app_hosts", groupName, appName)[0][0])
            if appHosts[appIP]['gray'] == True:
                appHosts[appIP]['gray'] = False
                GrayCmdSql(grayCmd, groupName, appName, json.dumps(appHosts))
                ManageNginxUpstream(groupName, appName)
                print("the host [%s] switch out gray successful." % appIP)
                PrintAppInfo(groupName, appName)
            else:
                print("the host is switch out gray.")
    # 查看测试灰度主机
    elif grayCmd == "testhost":
        testGrayHostData = ModTransl.Str2List(GrayCmdSql("testgrayhost")[2], ",")
        if len(testGrayHostData) != 0:
            print(testGrayHostData)
        else:
            print("empty")
    # 添加测试灰度主机
    elif grayCmd == "testhostadd" and len(cmdParm) == 1 and re.search(r"^([0-9*]{1,3}\.){3}([0-9*]{1,3})$", cmdParm[0]):
        testHostIP = cmdParm[0]
        testGrayHostData = ModTransl.Str2List(GrayCmdSql("testgrayhost")[2], ",")
        if not testHostIP in testGrayHostData:
            testGrayHostData.append(testHostIP)
            GrayCmdSql(grayCmd, ModTransl.List2Str(sorted(testGrayHostData),","))
            GrayIpSyncRedis()
            print(sorted(testGrayHostData))
        else:
            print("already in.")
    # 删除测试灰度主机
    elif grayCmd == "testhostdel" and len(cmdParm) == 1 and re.search(r"^([0-9*]{1,3}\.){3}([0-9*]{1,3})$", cmdParm[0]):
        testHostIP = cmdParm[0]
        testGrayHostData = ModTransl.Str2List(GrayCmdSql("testgrayhost")[2], ",")
        if testHostIP in testGrayHostData:
            testGrayHostData.remove(testHostIP)
            GrayCmdSql(grayCmd, ModTransl.List2Str(sorted(testGrayHostData), ","))
            GrayIpSyncRedis()
            print(sorted(testGrayHostData))
        else:
            print("not exited.")
    # 测试配置
    elif grayCmd == "test":
        for IP in openrestyHost:
            print(IP+":")
            if os.path.exists("/var/cache/salt/master/file_lists/roots/base.p"):
                os.remove("/var/cache/salt/master/file_lists/roots/base.p")  # 删除salt-master文件缓存
            print("    file sync failed: " + os.popen("salt '{openrestyHost}' state.highstate | awk '/^Failed/{{print $2}}'".format(openrestyHost=IP)).read())
            print(os.popen("salt '{openrestyHost}' cmd.run 'service openresty configtest' | grep -v '^{openrestyHost}'".format(openrestyHost=IP)).read())
        os.popen("rm -f /usr/local/unsops/gray_system/test.lock")
    # 更新配置
    elif grayCmd == "update":
        if os.path.exists('/usr/local/unsops/gray_system/test.lock'):
            print("==================== !!! Warning !!! ====================")
            print("              Please run command test first              ")
            print("==================== !!! Warning !!! ====================")
            exit(1)
        appData = GrayCmdSql("app_data")
        appGrayHostData = []
        # generate app gray host list
        # gray switch
        for appHosts in appData:
            graySwitch = False
            groupName = appHosts[2]
            appName = appHosts[1]
            appDict = json.loads(appHosts[4])
            for appIP in appDict:
                if appDict[appIP]['gray']:
                    graySwitch = True
                    appGrayHostData.append(appIP)
            if graySwitch:
                ModDB.Execute("redis", "set", (groupName + "#" + appName, 1))
            else:
                ModDB.Execute("redis", "set", (groupName + "#" + appName, 0))
        # gray host sync
        GrayCmdSql("appgrayhost_sync", ModTransl.List2Str(sorted(set(appGrayHostData)), ","))
        GrayIpSyncRedis()
        # service openresty reload
        for IP in openrestyHost:
            print(IP + ":")
            print(os.popen("salt '{openrestyHost}' cmd.run 'service openresty reload' | grep -v '^{openrestyHost}'".format(openrestyHost=IP)).read())
    # 灰度锁
    elif grayCmd == "graylock" and len(cmdParm) == 1 and re.search(r"^[Tt]rue$|^[Ff]alse$", cmdParm[0]):
        for IP in openrestyHost:
            if ModTransl.Str2Bool(cmdParm[0]) == True:
                os.popen("salt '{openrestyHost}' cmd.run 'touch /tmp/gray.lock'".format(openrestyHost=IP)).read()
            else:
                os.popen("salt '{openrestyHost}' cmd.run 'rm -f /tmp/gray.lock'".format(openrestyHost=IP)).read()
    else:
        CmdHelp()
    # 配置测试锁
    if grayCmd != "test":
        os.popen("touch /usr/local/unsops/gray_system/test.lock")
    # disconnect database
    ModDB.Disconnect("mysql")


# print info
def PrintGroupInfo(groupName):
    groupData = GrayCmdSql("group_info", groupName)[1][0]
    print("{group_name}: {domain_name}".format(group_name=groupData[1], domain_name=groupData[2]))


def PrintAppInfo(groupName, appName):
    appData = GrayCmdSql("app_info", groupName, appName)[1][0]
    # PrintGroupInfo(groupName)
    print(" --- {app_name}: hash:{ip_hash}".format(app_name=appData[1], ip_hash=appData[3]))
    appDict = json.loads(appData[4])
    for appInfo in sorted(appDict):
        print("   - {ip_addr}:{port} backup:{backup} gray:{gray}".format(ip_addr=appInfo,port=appDict[appInfo]['port'],backup=appDict[appInfo]['backup'],gray=appDict[appInfo]['gray']))


# group application data check
def GroupCheck(groupName, tipType):
    sql = '''SELECT * FROM application_group WHERE `name` = \'{group_name}\''''.format(group_name=groupName)
    if ModDB.Execute("mysql", "search", sql):
        if not tipType:
            print("the group [%s] has already existed." % groupName)
        return 1
    else:
        if tipType:
            print("the group [%s] not existed." % groupName)
        return 0


def GroupUseCheck(groupName, tipType):
    sql = '''SELECT * FROM application WHERE `group` = \'{group_name}\''''.format(group_name=groupName)
    if ModDB.Execute("mysql", "search", sql):
        if tipType:
            print("the group [%s] still used." % groupName)
        return 1
    else:
        return 0


def AppCheck(groupName, appName, tipType):
    if GroupCheck(groupName, 1):
        sql = '''SELECT * FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=groupName,app_name=appName)
        if ModDB.Execute("mysql", "search", sql):
            if tipType == 1:
                print("this application [%s] is already in group [%s]." % (appName, groupName))
            return 1
        else:
            if not tipType or tipType == 2:
                print("the application [%s] not existed." % appName)
            return 0
    else:
        exit(1)


def HostIpCheck(groupName, appName, appIP, tipType):
    if AppCheck(groupName, appName, 2):
        sql = '''SELECT hosts FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=groupName, app_name=appName)
        appHosts = json.loads(ModDB.Execute("mysql", "search", sql)[0][0])
        if appHosts.get(appIP):
            if tipType == 1:
                print("the host [%s] has already existed." % appIP)
            return 1
        else:
            if not tipType or tipType == 2:
                print("the host [%s] not existed." % appIP)
            return 0
    else:
        exit(1)


def HostBackupCheck(appName, appHosts, appIP, tipType):
    if appHosts[appIP]['backup'] == False:
        appHosts.pop(appIP)
        if len(appHosts) != 0:
            for IP in appHosts:
                if appHosts[IP]['backup'] == False:
                    return 1
        else:
            if re.search(r'Y|y', input("Please confirm delete the last host in the application:[Y/N] ")):
                return 1
            else:
                exit(1)
        if tipType == 1:
            print("must be have an active host.")
        return 0
    else:
        return 1


def HostGrayCheck(appName, appHosts, tipType):
    for IP in sorted(appHosts):
        if appHosts[IP]['gray'] == True:
            if not tipType:
                print("gray status cannot add/mod/del host.")
            return 1
    else:
        return 0


# generate nginx configure
def CreateNginxVHost(groupName, groupDomain):
    with open(graySystemRoot + '/gray_system/module/template/vhost.template', 'r', encoding='UTF-8') as f:
        template = f.read().format(group=groupName, domain=groupDomain, openresty_path=openrestyRoot)
    with open(saltstackRoot + '/nginx/conf/vhost/' + groupName + '.conf', 'w') as f:
        f.write(template)
    if not os.path.exists(saltstackRoot + '/nginx/conf/vhost/' + groupName):
        os.mkdir(saltstackRoot + '/nginx/conf/vhost/' + groupName)
    if not os.path.exists(saltstackRoot + '/nginx/conf/upstream/' + groupName):
        os.mkdir(saltstackRoot + '/nginx/conf/upstream/' + groupName)


def RemoveNginxVHost(groupName):
    if os.path.exists(saltstackRoot + '/nginx/conf/vhost/' + groupName + '.conf'):
        os.remove(saltstackRoot + '/nginx/conf/vhost/' + groupName + '.conf')
    if os.path.exists(saltstackRoot + '/nginx/conf/vhost/' + groupName):
        os.rmdir(saltstackRoot + '/nginx/conf/vhost/' + groupName)
    if os.path.exists(saltstackRoot + '/nginx/conf/upstream/' + groupName):
        os.rmdir(saltstackRoot + '/nginx/conf/upstream/' + groupName)


def CreateNginxLocal(groupName, appName):
    with open(graySystemRoot + '/gray_system/module/template/local.template', 'r', encoding='UTF-8') as f:
        template = f.read().format(upstream_name=appName, app_name=groupName + "#" + appName, openresty_path=openrestyRoot)
    with open(saltstackRoot + '/nginx/conf/vhost/' + groupName + '/' + appName + '.conf', 'w') as f:
         f.write(template)


def RemoveNginxLocal(groupName, appName):
    if os.path.exists(saltstackRoot + '/nginx/conf/vhost/' + groupName + '/' + appName + '.conf'):
        os.remove(saltstackRoot + '/nginx/conf/vhost/' + groupName + '/' + appName + '.conf')


def ManageNginxUpstream(groupName, appName):
    appHosts = json.loads(GrayCmdSql("app_hosts", groupName, appName)[0][0])
    appIpHash = ModTransl.Str2Bool(GrayCmdSql("app_ip_hash", groupName, appName)[0][0])
    appGray = bool(HostGrayCheck(appName, appHosts, 1))
    if len(appHosts) != 0:
        # generate upstream
        with open(saltstackRoot + '/nginx/conf/upstream/' + groupName + '/' + appName + '.conf', 'w') as f:
            for upsType in ['allserver', 'produce', 'develop']:
                upsTemp = "# {ups_type}\n".format(ups_type=upsType)
                upsTemp += "upstream {ups_type}#{group_name}#{app_name} {{\n".format(ups_type=upsType,group_name=groupName, app_name=appName)
                if upsType != "develop" and appIpHash == True:
                    upsTemp += "    ip_hash;\n"
                for IP in sorted(appHosts):
                    serverTemp = "    server {ip}:{port}".format(ip=IP, port=appHosts[IP]['port'])
                    if upsType != "develop":
                        if upsType == "allserver" or upsType == "produce" and appHosts[IP]['gray'] == False:
                            if appHosts[IP]['backup'] == True:
                                if appIpHash == False:
                                    upsTemp += serverTemp + " backup;\n"
                            else:
                                upsTemp += serverTemp + ";\n"
                    else:
                        if appHosts[IP]['gray'] == True:
                            upsTemp += serverTemp + ";\n"
                if upsType != "develop" or upsType == "develop" and appGray == True:
                    # print(upsTemp + "}\n")
                    f.write(upsTemp + "}\n")
    else:
        if os.path.exists(saltstackRoot + '/nginx/conf/upstream/' + groupName + '/' + appName + '.conf'):
            os.remove(saltstackRoot + '/nginx/conf/upstream/' + groupName + '/' + appName + '.conf')


# gray command sql execute
def GrayCmdSql(grayCmd, *parm):
    # 应用数据查询
    if grayCmd == "app_data":
        sql = '''SELECT * FROM application'''
        return ModDB.Execute("mysql", "search", sql)
    elif grayCmd == "app_info":
        sql = '''SELECT * FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1])
        return "mysql", ModDB.Execute("mysql", "search", sql)
    elif grayCmd == "app_hosts":
        sql = '''SELECT hosts FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1])
        return ModDB.Execute("mysql", "search", sql)
    elif grayCmd == "app_ip_hash":
        sql = '''SELECT ip_hash FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1])
        return ModDB.Execute("mysql", "search", sql)
    elif grayCmd == "group_info":
        sql = '''SELECT * FROM application_group WHERE `name` = \'{group_name}\''''.format(group_name=parm[0])
        return "mysql", ModDB.Execute("mysql", "search", sql)
    elif grayCmd == "group_data":
        sql = '''SELECT * FROM application_group'''
        return ModDB.Execute("mysql", "search", sql)
    # 添加应用组
    elif grayCmd == "groupadd":
        sql = '''INSERT INTO application_group(name,domain) VALUES (\'{group_name}\',\'{group_domain}\')'''.format(group_name=parm[0],group_domain=parm[1])
        return ModDB.Execute("mysql", "insert", sql)
    # 删除应用组
    elif grayCmd == "groupdel":
        sql = '''DELETE FROM application_group WHERE name = \'{group_name}\''''.format(group_name=parm[0])
        return ModDB.Execute("mysql", "delete", sql)
    # 添加应用
    elif grayCmd == "appadd":
        sql = '''INSERT INTO application(name,`group`,ip_hash) VALUES (\'{app_name}\',\'{group_name}\',\'{ip_hash}\')'''.format(group_name=parm[0],app_name=parm[1],ip_hash=parm[2])
        return ModDB.Execute("mysql", "insert", sql)
    # 删除应用
    elif grayCmd == "appdel":
        sql = '''DELETE FROM application WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1])
        return ModDB.Execute("mysql", "delete", sql)
    # 修改应用
    elif grayCmd == "appmod":
        sql = '''UPDATE application SET ip_hash = \'{ip_hash}\' WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1],ip_hash=parm[2])
        return ModDB.Execute("mysql", "update", sql)
    # 添加主机, 删除主机, 修改主机, 添加灰度, 删除灰度
    elif re.search(r'^hostadd$|^hostdel$|^hostmod$|^grayadd$|^graydel$', grayCmd):
        sql = '''UPDATE application SET hosts = \'{hosts_data}\' WHERE `group` = \'{group_name}\' AND `name` = \'{app_name}\''''.format(group_name=parm[0],app_name=parm[1],hosts_data=parm[2])
        return ModDB.Execute("mysql", "update", sql)
    # 应用灰度主机
    elif grayCmd == "appgrayhost":
        sql = '''SELECT * FROM grayhost WHERE name = \'application\''''
        return ModDB.Execute("mysql", "search", sql)[0]
    # 应用灰度主机同步
    elif grayCmd == "appgrayhost_sync":
        sql = '''UPDATE grayhost SET `hosts` = \'{hosts_data}\' WHERE `name` = \'application\''''.format(hosts_data=parm[0])
        return ModDB.Execute("mysql", "update", sql)
    # 测试主机
    elif grayCmd == "testgrayhost":
        sql = '''SELECT * FROM grayhost WHERE name = \'test\''''
        return ModDB.Execute("mysql", "search", sql)[0]
    # 测试主机添加，测试主机删除
    elif re.search(r'^testhost(add|del)$', grayCmd):
        sql = '''UPDATE grayhost SET `hosts` = \'{hosts_data}\' WHERE `name` = \'test\''''.format(hosts_data=parm[0])
        return ModDB.Execute("mysql", "update", sql)


# Gray Ip Sync Redis
def GrayIpSyncRedis():
    # test gray host ip list
    testGrayHostData = ModTransl.Str2List(GrayCmdSql("testgrayhost")[2], ",")
    # app gray host ip list
    appGrayHostData = ModTransl.Str2List(GrayCmdSql("appgrayhost")[2], ",")
    # app merge in test
    testGrayHostData.extend(appGrayHostData)
    # sync to redis
    ModDB.Execute("redis", "set", ("grayhost", ModTransl.List2NgxLua(sorted(testGrayHostData))))


# function command help
def CmdHelp():
    print('''
    Usage: gray-cli COMMAND [OPTION]...

    List of Commands:
    
    info [GROUP_NAME] [APP_NAME]
    
    groupadd GROUP_NAME DOMAIN_NAME             -- e.g. groupadd test_unspay_com test.unspay.com
    groupdel GROUP_NAME                         -- e.g. groupdel test_unspay_com
    
    appadd GROUP_NAME APP_NAME IP_HASH          -- e.g. appadd test_unspay_com small_agent_web false
    appmod GROUP_NAME APP_NAME IP_HASH          -- e.g. appmod test_unspay_com small_agent_web true
    appdel GROUP_NAME APP_NAME                  -- e.g. appdel test_unspay_com small_agent_web
    
    hostadd GROUP_NAME APP_NAME IP PORT BACKUP  -- e.g. hostadd test_unspay_com small_agent_web 172.22.27.103 8081 false
    hostmod GROUP_NAME APP_NAME IP BACKUP       -- e.g. hostmod test_unspay_com small_agent_web 172.22.27.103 true
    hostdel GROUP_NAME APP_NAME IP              -- e.g. hostdel test_unspay_com small_agent_web 172.22.27.103
    
    grayadd GROUP_NAME APP_NAME IP              -- e.g. grayadd test_unspay_com small_agent_web 172.22.27.104
    graydel GROUP_NAME APP_NAME IP              -- e.g. graydel test_unspay_com small_agent_web 172.22.27.105

    testhost
    testhostadd IP                              -- e.g. testhostadd 172.22.30.101 
    testhostdel IP                              -- e.g. testhostdel 172.22.30.101 

    test
    update
    
    graylock ENABLED                             -- e.g. graylock true
    ''')
