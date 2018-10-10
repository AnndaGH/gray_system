#!/usr/bin/python3

# import json
# import re
#
# import urllib.request
# import urllib.parse
#
# content = input("请输入需要翻译的内容：")
#
# url = 'http://fanyi.youdao.com/translate?smartresult=dict&smartresult=rule'
# data = {}
# data['i'] = content
# data['from'] = 'AUTO'
# data['to'] = 'AUTO'
# data['smartresult'] = 'dict'
# data['client'] = 'fanyideskweb'
# data['salt'] = '3eba5723f4b63b79'
# data['sign'] = 'PAhegGYmHA8DAR5KbXs1IU7BdJLF1F8q'
# data['doctype'] = 'json'
# data['version'] = '2.1'
# data['keyfrom'] = 'fanyi.web'
# data['action'] = 'FY_BY_REALTIME'
# data['typoResult'] = 'false'
# data = urllib.parse.urlencode(data).encode('utf-8')
#
# response = urllib.request.urlopen(url, data)
# html = response.read().decode('utf-8')
#
# target = json.loads(html)
# print("翻译结果：%s" % (target['translateResult'][0][0]['tgt']))


import http.client
import hashlib
import json
import urllib
import random
import sys


def baidu_translate(content):
    appid = '20160611000023109'
    secretKey = 'rkd7Y2hEr8ESxaTevuoo'
    httpClient = None
    myurl = '/api/trans/vip/translate'
    q = content
    fromLang = 'en'  # 源语言 zh
    toLang = 'zh'  # 翻译后的语言 jp
    salt = random.randint(32768, 65536)
    sign = appid + q + str(salt) + secretKey
    sign = hashlib.md5(sign.encode()).hexdigest()
    myurl = myurl + '?appid=' + appid + '&q=' + urllib.parse.quote(
        q) + '&from=' + fromLang + '&to=' + toLang + '&salt=' + str(
        salt) + '&sign=' + sign

    try:
        httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
        httpClient.request('GET', myurl)
        # response是HTTPResponse对象
        response = httpClient.getresponse()
        jsonResponse = response.read().decode("utf-8")  # 获得返回的结果，结果为json格式
        js = json.loads(jsonResponse)  # 将json格式的结果转换字典结构
        dst = str(js["trans_result"][0]["dst"])  # 取得翻译后的文本结果
        print(dst)  # 打印结果
    except Exception as e:
        print(e)
    finally:
        if httpClient:
            httpClient.close()


if __name__ == '__main__':
    baidu_translate(sys.argv[1])
    #print()
    # while True:
    #     print("请输入要翻译的内容,如果退出输入q")
    #     content = input()
    #     if (content == 'q'):
    #         break
    #