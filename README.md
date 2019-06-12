# Exec ansible api through web application

本项目对Ansible2+的接口进行了封装，并开发了WEB应用层，方便对Ansible接口进行调用,以对机器进行统一管理。

启动方式：
```
pip install --no-cache-dir -r requirements.txt

gunicorn manage:app -c gunicorn.conf.py
```

API接口示例：

#### Run Command

Url：`/api/v1/run` [`POST`]

Request（application/json）:

```
{
    "module":"shell",
    "args":"hostname",
    "remote_user":"hdfs",
    "hosts":["10.0.0.1","10.0.0.2"],
    "sync":true,
    "private_keyfile":"private_key_file", (可空,与remote_user不共存)
    "remote_pass":"password", (可空,与private_keyfile不共存)
    "remote_port":"22", (可空)
    "forks":5(可空)
}
```

Response（application/json）：

```
{
    "status":"success",
    "msg":"ok for async, log for sync"
}
```