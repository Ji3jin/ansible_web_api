#!/usr/bin/env python
# -*- coding: utf-8 -*-
import functools
from flask import jsonify, current_app
import os
from app.core.ansible_runner import Runner
from app.core.ansible_playbook import PlaybookRunner


def success(data, status_code=200, **kwargs):
    result = {
        'status': 'success',
        'msg': data,
    }
    resp = {**result, **kwargs}
    return jsonify(resp), status_code


def failed(err_msg, status_code=200, **kwargs):
    result = {
        'status': 'failed',
        'msg': err_msg,
    }
    resp = {**result, **kwargs}
    return jsonify(resp), status_code


def catch(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return exception(e)

    return inner


def exception(e):
    resp = {
        'status': 'failed',
        'msg': str(e)
    }
    return jsonify(resp), 200



def run(run_type, run_cmd, remote_user, remote_pass, remote_port, run_hosts,
        private_keyfile=None, forks=10):
    runner = Runner(
        module_name=run_type,
        module_args=run_cmd,
        remote_user=remote_user,
        hosts=run_hosts,
        private_key_file=private_keyfile,
        remote_pass=remote_pass,
        remote_port=remote_port,
        forks=forks
    )
    result = runner.run()
    # insert into db
    return result


def transform(path, target_path, remote_user, remote_pass, remote_port,
              run_hosts, private_keyfile=None, forks=10, need_del=False):
    runner = Runner(
        module_name="shell",
        module_args="mkdir -p {0}".format(os.path.dirname(target_path)),
        remote_user=remote_user,
        remote_port=remote_port,
        hosts=run_hosts,
        private_key_file=private_keyfile,
        remote_pass=remote_pass,
        forks=forks
    )
    runner.run()
    runner = Runner(
        module_name="copy",
        module_args="src={0} dest={1}".format(path, target_path),
        remote_user=remote_user,
        remote_port=remote_port,
        hosts=run_hosts,
        private_key_file=private_keyfile,
        remote_pass=remote_pass,
        forks=forks
    )
    result = runner.run()
    # insert into db
    if need_del:
        os.remove(path)
    return result


def play(path, remote_user, remote_pass, remote_port, run_hosts,
         private_keyfile=None, forks=10):
    play_book = PlaybookRunner(
        playbook_path=path,
        remote_user=remote_user,
        remote_port=remote_port,
        hosts=run_hosts,
        private_key_file=private_keyfile,
        remote_pass=remote_pass,
        forks=forks
    )
    # insert into db
    result = play_book.run()
    return result