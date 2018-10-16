#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# import
import sys
import re
import module.func_gray as ModFnGray


def Main():
    # remove gary-cli.py self
    del sys.argv[0]
    # gain command
    if len(sys.argv) >= 1:
        # command filter
        if re.search(r'^info$|^group(add|del)$|^app(add|del|mod)$|^host(add|del|mod)$|^gray(add|del)$|^test$|^update$|^graylock$|^testhost(add|del)*$|^tttt$',sys.argv[0]):
            ModFnGray.GrayCmd(sys.argv)
        else:
            ModFnGray.CmdHelp()
    else:
        ModFnGray.CmdHelp()


if __name__=='__main__':
    Main()


exit()
