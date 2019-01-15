# Gray System 灰度

## 语言
python3 lua

## 架构
访问控制
nginx + lua + redis
灰度配置
python3 + mysql + redis + saltstack

## 简介
在接入层，通过IP地址作为决策依据，将相应IP灰度到目标应用主机
通过灰度命令变更配置写入mysql，生成nginx配置及反向代理配置
灰度命令调用saltstack同步nginx配置并进行nginx配置测试
测试通过后灰度命令执行变更，nginx配置reload，修改redis灰度决策开关

**详细部署使用介绍详见 docs 目录**
