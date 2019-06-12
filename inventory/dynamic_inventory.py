#!/bin/env python
# -*- encoding: utf8 -*-

import sys
from argparse import ArgumentParser
import ConfigParser
import os, stat
import re
from time import time
import logging
import urllib
import httplib2
import requests
import socket

import simplejson as json
from ansible import utils
from ansible.plugins.callback import CallbackBase
from ansible import errors
from ansible.utils.display import Display


# NOTE -- this file assumes Ansible is being accessed FROM the xbox
# server, so it does not attempt to login with a username and password.
# this will be addressed in a future version of this script.


class DynamicInventory(object):

    def __init__(self):
        """ Main execution path """

        self._display = Display()
        self.cache = dict()
        self.inventory = dict()  # A list of groups and the hosts in that group

        # Read settings and parse CLI arguments
        self.read_settings()
        self.parse_cli_args()

        # Cache
        if self.args.refresh_cache:
            self.update_cache()
        elif not self.is_cache_valid():
            self.update_cache()
        else:
            self.load_inventory_from_cache()

        data_to_print = ""

        # Data to print
        if self.args.host:
            data_to_print = self.get_host_info()

        elif self.args.list:
            # Display list of instances for inventory
            data_to_print = self.json_format_dict(self.inventory, True)

        else:  # default action with no options
            data_to_print = self.json_format_dict(self.inventory, True)

        print(data_to_print)

    def get_host_list(self):
        http = httplib2.Http()
        # headers = {
        #    'Content-type': 'application/x-www-form-urlencoded',
        #    'User-Agent': 'ansible-host-getter'}

        for group in self.groups:
            body = {'token': self.token, 'tag': group}
            url = self.url_get_hostlist  # + urllib.urlencode(body)
            r = requests.get(url, params=body)
            if r.status_code != 200:
                raise AnsibleXboxResponseError('%s %s' % (r.status_code, r.text))
            else:
                hosts = json.loads(r.content)['hosts']
                self._display.display('[DEBUG] [get_host_list] url[%s] ==> hosts[%s]' % (url, len(hosts)),
                                      log_only=True)
                for host in hosts:
                    self.push(self.inventory, 'all', host)

    def get_host_tags(self):

        all_item_num = len(self.inventory['all'])
        item_per_req = 200
        req_group_num = int((item_per_req + all_item_num - 1) / item_per_req)

        for group in range(1, req_group_num + 1):
            idx_left = (group - 1) * item_per_req
            idx_right = min(group * item_per_req, all_item_num)
            self._display.display(
                '[DEBUG] [get_host_tags] all[%d] per[%d] group[%d/%d] idx[%d:%d)' %
                (all_item_num, item_per_req, group, req_group_num, idx_left, idx_right),
                log_only=True
            )
            host_list = '_'.join(self.inventory['all'][idx_left:idx_right])

            # http = httplib2.Http()
            # headers = {
            #    'Content-type': 'application/x-www-form-urlencoded',
            #    'User-Agent': 'ansible-host-getter'}

            body = {'token': self.token, 'hosts': host_list}
            url = self.url_get_hosttags  # + urllib.urlencode(body)
            r = requests.get(url, params=body)

            if r.status_code not in (200, 304):
                raise AnsibleXboxResponseError('%s %s' % (r.status_code, r.text))
            data = json.loads(r.content)
            self._display.display('[DEBUG] [get_host_tags] url[%s] ==> hosts[%s]' % (url, len(data['tag_list'])),
                                  log_only=True)

            if data['succ'] != 0 or not data['tag_list']:
                raise AnsibleXboxQueryError("note:[%s] url:[%s]" % (data['err_note'], url))
            if len(data['tag_list']) != idx_right - idx_left:
                self._display.display('[WARN] Host num in response lower than query sent, some host may lost', 'yallow')

            for host in json.loads(r.content)['tag_list'].keys():
                self.cache[host] = dict()
                # ip = 'Unknown'
                # try:
                #    ip = socket.gethostbyname(host)
                # except:
                #    pass
                self.cache[host]['ip'] = [host]
                tagstrs = json.loads(r.content)['tag_list'][host]
                print(host, tagstrs)
                for tagstr in tagstrs.split(','):
                    self.push(self.inventory, tagstr, host)

    def get_host_info(self):
        """ Get variables about a specific host """

        if not self.cache or len(self.cache) == 0:
            # Need to load index from cache
            self.load_cache_from_cache()

        if not self.args.host in self.cache:
            # try updating the cache
            self.update_cache()

            if not self.args.host in self.cache:
                # host might not exist anymore
                return self.json_format_dict({}, True)

        return self.json_format_dict(self.cache[self.args.host], True)

    def is_cache_valid(self):
        """ Determines if the cache files have expired, or if it is still valid """

        if os.path.isfile(self.cache_path_inventory):
            mod_time = os.path.getmtime(self.cache_path_inventory)
            current_time = time()
            if (mod_time + self.cache_max_age) > current_time:
                if os.path.isfile(self.cache_path_cache):
                    return True

        return False

    def read_settings(self):
        config = ConfigParser.SafeConfigParser()
        config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), "ansible.cfg"))
        self.url_get_hostlist = config.get('ansible_global', 'get_host_url')
        self.url_get_hosttags = config.get('ansible_global', 'get_tags_url')
        cache_path = os.path.expanduser(config.get('ansible_global', 'cache_path'))
        deny_users = config.get('ansible_global', 'deny_users').split(',')

        user = os.environ['USER']
        if user in deny_users:
            self._display.display(
                '[ERROR] [read_settings] User %s is denied to use ansible script, if you think it shouldn\'t, contact chengshengbo@xiaomi.com' % user)
            sys.exit(1)

        os.makedirs(cache_path, stat.S_IRWXU, exist_ok=True)

        self.token = config.get('ansible_global', 'token')
        self.groups = config.get('ansible_global', 'groups').split(',')
        self.cache_max_age = config.getint('ansible_global', 'cache_max_age')

        self.cache_path_cache = cache_path + "/.ansible.cache"
        self.cache_path_inventory = cache_path + "/.ansible.index"

    def parse_cli_args(self):
        """ Command line argument processing """

        parser = ArgumentParser(description='Produce an Ansible Inventory file')
        parser.add_argument('--list', action='store_true', default=True, help='List instances (default: True)')
        parser.add_argument('--host', action='store', help='Get all the variables about a specific instance')
        parser.add_argument('--refresh-cache', action='store_true', default=False,
                            help='Force refresh of cache by making API requests to xbox (default: False - use cache files)')
        self.args = parser.parse_args()

    def update_cache(self):
        """ Make calls to xbox and save the output in a cache """

        self.get_host_list()
        self.get_host_tags()

        self.write_to_cache(self.cache, self.cache_path_cache)
        self.write_to_cache(self.inventory, self.cache_path_inventory)

    def push(self, my_dict, key, element):
        """ Pushed an element onto an array that may not have been defined in the dict """

        if key not in my_dict:
            # new tag
            my_dict[key] = [element]
        elif element not in my_dict[key]:
            # tag with new value
            my_dict[key].append(element)
        else:
            # already have this tag and value
            pass

    def load_cache_from_cache(self):
        """ Reads the cache from the cache file sets self.cache """

        cache = open(self.cache_path_cache, 'r')
        json_cache = cache.read()
        self.cache = json.loads(json_cache)

    def load_inventory_from_cache(self):
        """ Reads the index from the cache file sets self.index """

        cache = open(self.cache_path_inventory, 'r')
        json_inventory = cache.read()
        self.inventory = json.loads(json_inventory)

    def write_to_cache(self, data, filename):
        """ Writes data in JSON format to a file """

        json_data = self.json_format_dict(data, True)
        cache = open(filename, 'w')
        cache.write(json_data)
        cache.close()

    def to_safe(self, word):
        """ Converts 'bad' characters in a string to underscores so they can be used as Ansible groups """

        return re.sub("[^A-Za-z0-9\-]", "_", word)

    def json_format_dict(self, data, pretty=False):
        """ Converts a dict to a JSON object and dumps it as a formatted string """

        if pretty:
            return json.dumps(data, sort_keys=True, indent=2)
        else:
            return json.dumps(data)


class AnsibleXboxResponseError(errors.AnsibleError):
    pass


class AnsibleXboxQueryError(errors.AnsibleError):
    pass


DynamicInventory()
