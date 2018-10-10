-- import module
local redis = require("resty.redis")
local json = require "cjson"
-- function
function split(str,reps)
        local resultStrList = {}
        string.gsub(str,'[^'..reps..']+', function ( w ) table.insert( resultStrList,w ) end)
        return resultStrList
end
function file_exists(path)
	local file = io.open(path, "rb")
	if file then file:close() end
	return file ~= nil
end
-- set default policy
ngx.var.ups_pol = "allserver#" .. ngx.var.app_name
-- gray lock
if file_exists("/tmp/gray.lock") then
	return
end
-- create instance
local redis_instance = redis:new()
-- set timeout
redis_instance:set_timeout(100)
-- create connect
local host = "172.22.27.111"
local port = 6379
local conn_state, err = redis_instance:connect(host, port)
-- connect check
if not conn_state then
	return redis_instance:close()
end
-- upstream policy
local res, err = redis_instance:get(ngx.var.app_name)
if res == "1" then
	-- analysis remote_addr
	ip = split(ngx.var.proxy_add_x_forwarded_for,',')[1]
	-- gain ip list
	local res, err = redis_instance:get("gray_ip_list")
	res, err = loadstring("return " .. res)
	local iplist = res()
	-- traversal ip list
	for k, v in pairs(iplist) do
	        if string.find(ip,"^" ..v.. "$") then
			-- ngx.log(ngx.INFO, "gray: ", v)
			ngx.var.ups_pol = "develop#" .. ngx.var.app_name
			return redis_instance:close()
	        end
	end
else
	ngx.var.ups_pol = "produce#" .. ngx.var.app_name
	return redis_instance:close() 
end
