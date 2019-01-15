nginx_conf_vhost:
  file.recurse:
    - name: /usr/local/openresty/nginx/conf/vhost
    - source: salt://nginx/conf/vhost
    - user: root
    - group: root
    - file_mode: 644
    - dir_mode: 755
    - mkdir: True
    - clean: True
