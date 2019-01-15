nginx_conf_cert:
  file.recurse:
    - name: /usr/local/openresty/nginx/conf/cert
    - source: salt://nginx/conf/cert
    - user: root
    - group: root
    - file_mode: 644
    - dir_mode: 755
    - mkdir: True
    - clean: True
