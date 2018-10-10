#!/usr/bin/env python3
# -*- coding:utf-8 -*-


def str2list(strs, symbol):
    '''
    transform string to list
    '''
    if strs != '':
        strs = strs.strip(symbol).split(symbol)
    else:
        strs = []
    return strs


def list2str(lists, symbol):
    '''
    transform list to string
    '''
    if len(lists) > 0:
        str = symbol.join(lists)
    else:
        str = ''
    return str


def list_rm_list(source_lists, remove_lists):
    '''
    delete list data from list
    '''
    for remove in remove_lists:
        if remove in source_lists:
            source_lists.remove(remove)
    return source_lists


def list2ngxlua(lists):
    '''
    transform list to ngxlua
    '''
    ips = ''
    for ip in lists:
        if ips == '':
            ips = ips + '"' + ip + '"'
        else:
            ips = ips + ',"' + ip + '"'
    return '{' + ips + '}'


def str2bool(str):
    return True if str.lower() == 'true' else False