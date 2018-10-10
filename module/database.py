#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# import database
import pymysql
import redis
import re


def connect(db_type):
    '''
    connect database db_type: mysql, redis
    '''
    if db_type == "mysql":
        global db
        global cursor
        db_config = {
            'host': '172.22.27.114',
            'port': 3306,
            'user': 'gray',
            'password': 'qwe123++',
            'db': 'gray_system',
            'charset': 'utf8mb4'
        }
        try:
            db = pymysql.connect(**db_config)
            cursor = db.cursor()
        except Exception as error:
            print(error)
            exit()
    elif db_type == "redis":
        global rds
        global poll
        try:
            pool = redis.ConnectionPool(host='172.22.27.111', port=6379, decode_responses=True)
            rds = redis.StrictRedis(connection_pool=pool)
        except Exception as error:
            print(error)
            exit()


def execute(db_type, sql_type, sql):
    if db_type == "mysql":
        if sql_type == "search":
            try:
                cursor.execute(sql)
                # return cursor.fetchone()  # 返回的数据类型 元组
                return cursor.fetchall()
            except Exception as error:
                print(error)
        elif re.search(r'^insert$|^update$|^delete$', sql_type):
            try:
                cursor.execute(sql)  # 执行sql语句
                db.commit()  # 提交到数据库执行
                return 1
            except Exception as error:
                db.rollback()  # 发生错误则回滚
                print(error)
                return 0

    elif db_type == "redis":
        if sql_type == "get":
            return rds.get(sql)
        elif sql_type == "set":
            rds.set(sql[0], sql[1])
        elif sql_type == "del":
            rds.delete(sql)


def disconnect(db_type):
    if db_type == "mysql":
        db.close()
    elif db_type == "redis":
        pass



