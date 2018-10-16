#!/usr/bin/env python3
# -*- coding:utf-8 -*-


def Str2List(Strs, Symbol):
    '''
    transform string to list
    '''
    if Strs != '':
        Strs = Strs.strip(Symbol).split(Symbol)
    else:
        Strs = []
    return Strs


def List2Str(Lists, Symbol):
    '''
    transform list to string
    '''
    if len(Lists) > 0:
        Str = Symbol.join(Lists)
    else:
        Str = ''
    return Str


def ListRmList(SourceLists, RemoveLists):
    '''
    delete list data from list
    '''
    for Remove in RemoveLists:
        if Remove in SourceLists:
            SourceLists.remove(Remove)
    return SourceLists


def List2NgxLua(Lists):
    '''
    transform list to ngxlua
    '''
    IPs = ''
    for IP in Lists:
        if IPs == '':
            IPs = IPs + '"' + IP + '"'
        else:
            IPs = IPs + ',"' + IP + '"'
    return '{' + IPs + '}'


def Str2Bool(Str):
    return True if Str.lower() == 'true' else False