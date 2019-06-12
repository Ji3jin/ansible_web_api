#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from flask import Flask
from config import config
from .core.executor import Executor
import pymysql
from DBUtils.PersistentDB import PersistentDB

config_name = os.getenv('FLASK_CONFIG') or 'default'

app = Flask(__name__)
app.config.from_object(config[config_name])
config[config_name].init_app(app)
executor = Executor(app)

current_config = config[config_name]

db_config = {
  'host': current_config.MYSQL_HOST,
  'port': current_config.MYSQL_PORT,
  'database': current_config.MYSQL_DB,
  'user': current_config.MYSQL_USER,
  'password': current_config.MYSQL_PWD,
}

db_pool = PersistentDB(pymysql, **db_config)

os.makedirs(os.path.join(current_config.DATA_PATH, "keyfile"), exist_ok=True)
os.makedirs(os.path.join(current_config.DATA_PATH, "config"), exist_ok=True)
os.makedirs(current_config.LOG_PATH, exist_ok=True)

from .api import api as api_blueprint

app.register_blueprint(api_blueprint)
