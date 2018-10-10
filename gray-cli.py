#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# import
import sys
import re
import module.func_gray as gr


def main():
    del sys.argv[0] # remove gary-cli.py self
    # gain command
    if len(sys.argv) >= 1:
        # command filter
        if re.search(r'^info$|^group(add|del)$|^app(add|del|mod)$|^host(add|del|mod)$|^gray(add|del)$|^test$|^update$|^graylock$|^grayhost(add|del)*$|^tttt$',sys.argv[0]):
            gr.gray_cmd(sys.argv)
        else:
            gr.command_help()
    else:
        gr.command_help()


if __name__=='__main__':
    main()


exit()
