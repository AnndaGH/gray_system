#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# import
import os
import sys
import re
import time
# import json
import module.database as db
import module.func_transform as tr


# function
def generate_nginx_upstream(name):
    for types in ['product', 'gray']:
        filename = types + '_' + name + '.conf'
        sql = '''SELECT {host_type}_host FROM application WHERE name = \'{app_name}\''''.format(host_type=types, app_name=name)
        data = tr.str2list(db.gray_data_process("mysql", db.execute("mysql", "search", sql)[0]), ",")
        sql = '''SELECT port FROM application WHERE name = \'{app_name}\''''.format(app_name=name)
        port = db.gray_data_process("mysql", db.execute("mysql", "search", sql)[0])
        if len(data) > 0:
            with open("/srv/salt/nginx/conf/upstream/" + filename, 'w') as f:
                f.write("upstream %s_%s {\n\tip_hash;\n" % (types, name))
                for ip in data:
                    f.write("\tserver %s:%s;\n" % (ip, port))
                f.write("}\n")
        else:
            os.remove("/srv/salt/nginx/conf/upstream/" + filename)


# main
def main():
    # gain command
    if len(sys.argv) > 1:
        # connect database
        db.connect("mysql")
        db.connect("redis")
        # command select
        app_name = sys.argv[1]
        if app_name == "devget" or app_name == "devset":
            gray_cmd(app_name, "dev_ip_list", "devlist")
        else:
            try:
                app_cmd = sys.argv[2]
            except:
                app_cmd = "status"
            # search app_name
            data = db.gray_cmd_sql("status", app_name)
            # gray_cmd
            if data or app_cmd == "create":
                gray_cmd(app_cmd, app_name, data)
            else:
                print("The application name has not been found.")

        # disconnect database
        db.disconnect("mysql")

    else:
        print("please enter the parameters.")


def gray_cmd(cmd, name, data):
    if cmd == "status":
        print("application:", data[1], "\tport:", data[2])
        print("product_host:", data[3])
        print("gray_host:", data[4])
        print("gray_status:", db.execute("redis", "get", name))

    elif cmd == "devget":  # 打印开发环境灰度IP地址
        print("dev_ip_list:", db.gray_cmd_sql(cmd, name)[2])

    elif cmd == "devset":  # 更新开发环境灰度IP地址
        db.gray_cmd_sql(cmd, name, "host", sys.argv[2])  # 更新写入数据库
        db.gray_ip_sync()  # 灰度IP同步
        print("devset successful.")

    elif cmd == "grayadd":  # 添加主机到灰度列表
        product_host = tr.str2list(data[3], ",")  # 数据库中获取，生产主机列表，字符转为列表类型
        if len(product_host) == 0:
            return print("no more host add to gray.")
        gray_host = tr.str2list(data[4], ",")  # 数据库中获取，灰度主机列表，字符转为列表类型
        host_list = tr.str2list(sys.argv[3], ",")  # 命令中获取，灰度主机列表，字符转为列表类型
        for host in host_list:
            if host in product_host:
                product_host.remove(host)
                gray_host.append(host)
        db.gray_cmd_sql(cmd, name, "product_host", tr.list2str(product_host, ","))  # 更新写入数据库
        db.gray_cmd_sql(cmd, name, "gray_host", tr.list2str(gray_host, ","))  # 更新写入数据库

        # 同步IP数据 及 应用灰度状态 到 redis
        if len(gray_host) > 0:
            # step 1 灰度主机IP表生成
            db.gray_ip_sync()
            # step 2 nginx 配置修改
            generate_nginx_upstream(name)  # 配置生成同步
            os.remove("/var/cache/salt/master/file_lists/roots/base.p")  # 删除salt-master文件缓存
            os.popen("salt -L '172.19.31.21,172.19.31.22' state.sls nginx_conf_upstream").read()  # salt 文件同步
            # step 3 nginx reload
            os.popen("salt -L '172.19.31.21,172.19.31.22' cmd.run 'service openresty reload'").read()
            # step 4 redis 灰度控制
            db.execute("redis", "set", name, 1)  # 应用灰度状态
        print("gray add successful.")

    elif cmd == "graydel":  # 删除主机到生产列表
        gray_host = tr.str2list(data[4], ",")
        if len(gray_host) == 0:
            return print("no more host del for gray.")
        product_host = tr.str2list(data[3], ",")  # 数据库中获取，生产主机列表，字符转为列表类型
        host_list = tr.str2list(sys.argv[3], ",")
        for host in host_list:
            if host in gray_host:
                gray_host.remove(host)
                product_host.append(host)
        db.gray_cmd_sql(cmd, name, "product_host", tr.list2str(product_host, ","))  # 更新写入数据库
        db.gray_cmd_sql(cmd, name, "gray_host", tr.list2str(gray_host, ","))  # 更新写入数据库

        # 同步IP数据 及 应用灰度状态 到 redis
        if len(gray_host) == 0:
            # step 1 redis 灰度控制
            db.execute("redis", "set", name, 0)  # 取消灰度状态
            # step 2 灰度主机IP表生成
            db.gray_ip_sync()
            # step 3 nginx 配置修改同步
            generate_nginx_upstream(name)  # 配置生成
            os.remove("/var/cache/salt/master/file_lists/roots/base.p")  # 删除salt-master文件缓存
            os.popen("salt -L '172.19.31.21,172.19.31.22' state.sls nginx_conf_upstream").read()  # salt 文件同步
            # step 4 nginx reload
            os.popen("salt -L '172.19.31.21,172.19.31.22' cmd.run 'service openresty reload'").read()
        print("gray del successful.")

    elif cmd == "replace":  # 置换灰度主机
        db.gray_cmd_sql(cmd, name, "product_host", data[4])  # 更新写入数据库
        db.gray_cmd_sql(cmd, name, "gray_host", data[3])  # 更新写入数据库
        # step 1 nginx 配置修改同步
        generate_nginx_upstream(name)  # 配置生成
        os.remove("/var/cache/salt/master/file_lists/roots/base.p")  # 删除salt-master文件缓存
        os.popen("salt -L '172.19.31.21,172.19.31.22' state.sls nginx_conf_upstream").read()  # salt 文件同步
        # step 2 nginx reload
        os.popen("salt -L '172.19.31.21,172.19.31.22' cmd.run 'service openresty reload'").read()
        # step 3 灰度主机IP表生成
        db.gray_ip_sync()
        print("gray replace successful.")

    elif cmd == "merge":  # 合并灰度主机
        product_host = tr.str2list(data[3], ",")  # 数据库中获取，生产主机列表，字符转为列表类型
        gray_host = tr.str2list(data[4], ",")  # 数据库中获取，灰度主机列表，字符转为列表类型
        product_host.extend(gray_host)
        db.gray_cmd_sql(cmd, name, "product_host", tr.list2str(product_host, ","))  # 更新写入数据库
        db.gray_cmd_sql(cmd, name, "gray_host", '')  # 更新写入数据库
        # step 1 灰度主机IP表生成
        db.gray_ip_sync()
        # step 2 redis 灰度控制
        db.execute("redis", "set", name, 0)  # 取消灰度状态
        # step 3 nginx 配置修改同步
        generate_nginx_upstream(name)  # 配置生成
        os.remove("/var/cache/salt/master/file_lists/roots/base.p")  # 删除salt-master文件缓存
        os.popen("salt -L '172.19.31.21,172.19.31.22' state.sls nginx_conf_upstream").read()  # salt 文件同步
        # step 4 nginx reload
        os.popen("salt -L '172.19.31.21,172.19.31.22' cmd.run 'service openresty reload'").read()
        print("gray merge successful.")

    elif cmd == "create":  # 创建应用
        if data:
            print('the application has already existed.')
        else:
            res = input("Please confirm the application information:[Y/N] ")
            if res == "Y" or res == "y":
                db.gray_cmd_sql(cmd, name, sys.argv[3])
                db.execute("redis", "set", name, 0)
                print("application %s create successful." % name)

    elif cmd == "remove":  # 移除应用
        res = input("Please confirm the application information:[Y/N] ")
        if res == "Y" or res == "y":
            db.gray_cmd_sql(cmd, name)
            db.execute("redis", "del", name)
            print("application %s remove successful." % name)

    elif cmd == "hostadd":  # 添加主机
        product_host = tr.str2list(data[3], ",")  # 数据库中获取，生产主机列表，字符转为列表类型
        product_host.extend(tr.str2list(sys.argv[3], ","))  # 命令行字符转列表后，与生产主机列表合并
        product_host = list(set(product_host))  # 列表去重
        product_host = tr.list2str(product_host, ",")  # 列表转字符类型
        db.gray_cmd_sql(cmd, name, "product_host", product_host)  # 更新写入数据库
        print("host add successful.")

    elif cmd == "hostdel":  # 删除主机
        host_list = tr.str2list(data[3], ",")  # 数据库中获取，生产主机列表，字符转为列表类型
        host_list = tr.list_rm_list(host_list, tr.str2list(sys.argv[3], ","))  # 删除指定主机
        host_list = tr.list2str(host_list, ",")  # 列表转字符类型
        db.gray_cmd_sql(cmd, name, "product_host", host_list)  # 更新写入数据库
        print("host del successful.")

    else:
        print("command help")


if __name__=='__main__':
    main()


exit()
