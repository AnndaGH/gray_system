#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#####################################################################################################################
#   Gray System                                                                                 Create 2018/07/26   #
#   Author Annda Ver 1.0.0                                                                      Update 2018/10/16   #
#####################################################################################################################

# import database
import pymysql
import redis
import re


def Connect(dbType):
    '''
    connect database dbType: mysql, redis
    '''
    if dbType == "mysql":
        global db
        global cursor
        dbConfig = {
            'host': '172.22.27.114',
            'port': 3306,
            'user': 'gray',
            'password': 'qwe123++',
            'db': 'gray_system',
            'charset': 'utf8mb4'
        }
        try:
            db = pymysql.connect(**dbConfig)
            cursor = db.cursor()
        except Exception as error:
            print(error)
            exit()
    elif dbType == "redis":
        global rds
        global pool
        try:
            pool = redis.ConnectionPool(host='172.22.27.111', port=6379, decode_responses=True)
            rds = redis.StrictRedis(connection_pool=pool)
        except Exception as error:
            print(error)
            exit()


def Execute(dbType, sqlType, sql):
    if dbType == "mysql":
        if sqlType == "search":
            try:
                cursor.execute(sql)
                # return cursor.fetchone()  # 返回的数据类型 元组
                return cursor.fetchall()
            except Exception as error:
                print(error)
        elif re.search(r'^insert$|^update$|^delete$', sqlType):
            try:
                cursor.execute(sql)  # 执行sql语句
                db.commit()  # 提交到数据库执行
                return 1
            except Exception as error:
                db.rollback()  # 发生错误则回滚
                print(error)
                return 0
    elif dbType == "redis":
        if sqlType == "get":
            return rds.get(sql)
        elif sqlType == "set":
            rds.set(sql[0], sql[1])
        elif sqlType == "del":
            rds.delete(sql)


def Disconnect(dbType):
    if dbType == "mysql":
        db.close()
    elif dbType == "redis":
        pass
