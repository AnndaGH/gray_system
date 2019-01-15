nginx_conf_upstream:
  file.recurse:
    - name: /usr/local/openresty/nginx/conf/upstream
    - source: salt://nginx/conf/upstream
    - user: root
    - group: root
    - file_mode: 644
    - dir_mode: 755
    - mkdir: True
    - clean: True
