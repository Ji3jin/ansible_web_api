#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import request
from app import app
from app.api import baseapi
from app import executor
import json
import os, stat
from app import current_config
import uuid


@app.route('/', methods=['GET'])
def hello_ansible_api():
    return "Hello Ansible Api"


@app.route('/api/v1/run', methods=['POST'])
@baseapi.catch
def ansible_run():
    data = json.loads(request.get_data())
    run_type = data["module"]
    run_cmd = data["args"]
    remote_user = data["remote_user"]
    remote_pass = data.get("remote_pass")
    remote_port = int(data.get("remote_port", "22"))
    run_hosts = data["hosts"]
    is_sync = data["sync"]
    private_keyfile = data.get("private_keyfile")
    if private_keyfile is None and remote_pass is None:
        return baseapi.failed("must set keyfile or password")
    if private_keyfile is not None:
        keyfile_path = os.path.join(current_config.DATA_PATH, "keyfile",
                                    uuid.uuid4().hex)
        with open(keyfile_path, 'w') as f:
            f.write(private_keyfile)
        os.chmod(keyfile_path, stat.S_IRWXU)
    else:
        keyfile_path = None
    forks = 10 if data.get("forks") is None else data.get("forks")
    response = "ok"
    if is_sync:
        response = baseapi.run(run_type, run_cmd, remote_user, remote_pass, remote_port,
                               run_hosts, keyfile_path, forks)
    else:
        executor.submit(baseapi.run, run_type, run_cmd, remote_user, remote_pass,
                        remote_port, run_hosts, keyfile_path, forks)
    if keyfile_path is not None and os.path.exists(keyfile_path):
        os.remove(keyfile_path)
    return baseapi.success(response)


@app.route('/api/v1/play', methods=['POST'])
@baseapi.catch
def ansible_play():
    data = json.loads(request.get_data())
    path = data["path"]
    remote_user = data["remote_user"]
    remote_pass = data.get("remote_pass")
    remote_port = int(data.get("remote_port", "22"))
    run_hosts = data["hosts"]
    is_sync = data["sync"]
    private_keyfile = data.get("private_keyfile")
    if private_keyfile is None and remote_pass is None:
        return baseapi.failed("must set keyfile or password")
    if private_keyfile is not None:
        keyfile_path = os.path.join(current_config.DATA_PATH, "keyfile",
                                    uuid.uuid4().hex)
        with open(keyfile_path, 'w') as f:
            f.write(private_keyfile)
        os.chmod(keyfile_path, stat.S_IRWXU)
    else:
        keyfile_path = None
    forks = 10 if data.get("forks") is None else data.get("forks")
    response = "ok"
    if is_sync:
        response = baseapi.play(path, remote_user, remote_pass, remote_port, run_hosts,
                                keyfile_path, forks)
    else:
        executor.submit(baseapi.play, path, remote_user, remote_pass, remote_port,
                        run_hosts, keyfile_path, forks)
    if keyfile_path is not None and os.path.exists(keyfile_path):
        os.remove(keyfile_path)
    return baseapi.success(response)


@app.route('/api/v1/transform', methods=['POST'])
@baseapi.catch
def ansible_transform():
    data = json.loads(request.get_data())
    path = data.get("path")
    target_path = data["target_path"]
    file_data = data.get("data")
    need_del = False
    config_path = os.path.join(current_config.DATA_PATH, "config",
                               uuid.uuid4().hex)
    if file_data is not None:
        need_del = True
        with open(config_path, 'wb') as f:
            f.write(file_data)
    remote_user = data["remote_user"]
    remote_pass = data.get("remote_pass")
    remote_port = int(data.get("remote_port", "22"))
    run_hosts = data["hosts"]
    is_sync = data["sync"]
    private_keyfile = data.get("private_keyfile")
    if private_keyfile is None and remote_pass is None:
        return baseapi.failed("must set keyfile or password")
    if private_keyfile is not None:
        keyfile_path = os.path.join(current_config.DATA_PATH, "keyfile",
                                    uuid.uuid4().hex)
        with open(keyfile_path, 'w') as f:
            f.write(private_keyfile)
        os.chmod(keyfile_path, stat.S_IRWXU)
    else:
        keyfile_path = None
    forks = 10 if data.get("forks") is None else data.get("forks")
    response = "ok"
    if is_sync:
        response = baseapi.transform(path, target_path, remote_user, remote_pass,
                                     remote_port, run_hosts, keyfile_path, forks, need_del)
    else:
        executor.submit(baseapi.transform, path, target_path, remote_user, remote_pass,
                        remote_port, run_hosts, keyfile_path, forks, need_del)
    if need_del and os.path.exists(config_path):
        os.remove(config_path)
    if keyfile_path is not None and os.path.exists(keyfile_path):
        os.remove(keyfile_path)
    return baseapi.success(response)


@app.route('/api/v1/ping', methods=['POST'])
@baseapi.catch
def ping():
    data = json.loads(request.get_data())
    run_type = "ping"
    run_cmd = None
    remote_user = data["remote_user"]
    remote_pass = data.get("remote_pass")
    remote_port = int(data.get("remote_port", "22"))
    run_hosts = data["hosts"]
    is_sync = data["sync"]
    private_keyfile = data.get("private_keyfile")
    if private_keyfile is not None:
        keyfile_path = os.path.join(current_config.DATA_PATH, "keyfile",
                                    uuid.uuid4().hex)
        with open(keyfile_path, 'w') as f:
            f.write(private_keyfile)
        os.chmod(keyfile_path, stat.S_IRWXU)
    else:
        keyfile_path = None
    forks = 10 if data.get("forks") is None else data.get("forks")
    response = "ok"
    if is_sync:
        response = baseapi.run(run_type, run_cmd, remote_user, remote_pass, remote_port,
                               run_hosts, keyfile_path, forks, )
    else:
        executor.submit(baseapi.run, run_type, run_cmd, remote_user, remote_pass,
                        remote_port, run_hosts, keyfile_path, forks)
    if keyfile_path is not None and os.path.exists(keyfile_path):
        os.remove(keyfile_path)
    return baseapi.success(response)
