#!/usr/bin/env python
# coding:utf8
import os
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
import ansible.constants as C
from ansible.errors import AnsibleError
from ansible.inventory.manager import InventoryManager
from app import current_config
import time

base_dir = current_config.DATA_PATH
__all__ = ['PlaybookRunner']
basedir = os.path.abspath(os.path.dirname(__file__))

Options = namedtuple('Options', [
  'listtags', 'listtasks', 'listhosts', 'syntax', 'connection',
  'module_path', 'forks', 'remote_user', 'remote_pass', 'remote_port',
  'private_key_file', 'timeout',
  'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args',
  'become', 'become_method', 'become_user', 'verbosity', 'check', 'extra_vars',
  'diff'])


class CallbackModule(CallbackBase):
  """
  Custom callback model for handlering the output data of
  execute playbook file,
  Base on the build-in callback plugins of ansible which named `json`.
  """

  CALLBACK_VERSION = 2.0
  CALLBACK_TYPE = 'stdout'
  CALLBACK_NAME = 'Dict'

  def __init__(self, display=None):
    super(CallbackModule, self).__init__(display)
    self.results = []
    self.output = ""
    self.item_results = {}  # {"host": []}

  def _new_play(self, play):
    return {
      'play': {
        'name': play.name,
        'id': str(play._uuid)
      },
      'tasks': []
    }

  def _new_task(self, task):
    return {
      'task': {
        'name': task.get_name(),
      },
      'hosts': {}
    }

  def v2_playbook_on_no_hosts_matched(self):
    self.output = "skipping: No match hosts."

  def v2_playbook_on_no_hosts_remaining(self):
    pass

  def v2_playbook_on_task_start(self, task, is_conditional):
    self.results[-1]['tasks'].append(self._new_task(task))

  def v2_playbook_on_play_start(self, play):
    self.results.append(self._new_play(play))

  def v2_playbook_on_stats(self, stats):
    hosts = sorted(stats.processed.keys())
    summary = {}
    for h in hosts:
      s = stats.summarize(h)
      summary[h] = s

    if self.output:
      pass
    else:
      self.output = {
        'plays': self.results,
        'stats': summary
      }

  def gather_result(self, res):
    if res._task.loop and "results" in res._result and res._host.name in self.item_results:
      res._result.update({"results": self.item_results[res._host.name]})
      del self.item_results[res._host.name]

    self.results[-1]['tasks'][-1]['hosts'][res._host.name] = res._result

  def v2_runner_on_ok(self, res, **kwargs):
    if "ansible_facts" in res._result:
      del res._result["ansible_facts"]

    self.gather_result(res)

  def v2_runner_on_failed(self, res, **kwargs):
    self.gather_result(res)

  def v2_runner_on_unreachable(self, res, **kwargs):
    self.gather_result(res)

  def v2_runner_on_skipped(self, res, **kwargs):
    self.gather_result(res)

  def gather_item_result(self, res):
    self.item_results.setdefault(res._host.name, []).append(res._result)

  def v2_runner_item_on_ok(self, res):
    self.gather_item_result(res)

  def v2_runner_item_on_failed(self, res):
    self.gather_item_result(res)

  def v2_runner_item_on_skipped(self, res):
    self.gather_item_result(res)


class PlaybookRunner(object):
  """
  The plabybook API.
  """

  def __init__(
      self,
      hosts=C.DEFAULT_HOST_LIST,  # a list or dynamic-hosts,
      # default is /etc/ansible/hosts
      playbook_path=None,  # * a playbook file
      forks=C.DEFAULT_FORKS,
      listtags=False,
      listtasks=False,
      listhosts=False,
      syntax=False,
      module_path=None,
      remote_user='root',
      timeout=C.DEFAULT_TIMEOUT,
      ssh_common_args=None,
      ssh_extra_args=None,
      sftp_extra_args=None,
      scp_extra_args=None,
      become=True,
      become_method=None,
      become_user="root",
      verbosity=None,
      extra_vars=None,
      connection_type="ssh",
      passwords=None,
      private_key_file=C.DEFAULT_PRIVATE_KEY_FILE,
      remote_pass=C.DEFAULT_REMOTE_PASS,
      remote_port=None,
      check=False
  ):

    C.RETRY_FILES_ENABLED = False
    self.callbackmodule = CallbackModule()
    if playbook_path is None or not os.path.exists(playbook_path):
      raise AnsibleError(
          "Not Found the playbook file: %s." % playbook_path)
    self.playbook_path = playbook_path
    self.loader = DataLoader()
    self.variable_manager = VariableManager()
    self.passwords = passwords or {}
    # save host to file
    if not os.path.exists(os.path.join(base_dir, "tmp_inventory")):
      os.mkdir(os.path.join(base_dir, "tmp_inventory"))
    self.file_name = os.path.join(base_dir, "tmp_inventory",
                                  "tmp_host_{0}".format(time.time()))
    with open(self.file_name, 'w') as f:
      f.write("\n".join(hosts))
    self.passwords = passwords or {}
    self.inventory = InventoryManager(loader=self.loader,
                                      sources=self.file_name)
    self.variable_manager = VariableManager(loader=self.loader,
                                            inventory=self.inventory)

    self.options = Options(
        listtags=listtags,
        listtasks=listtasks,
        listhosts=listhosts,
        syntax=syntax,
        timeout=timeout,
        connection=connection_type,
        module_path=module_path,
        forks=forks,
        remote_user=remote_user,
        remote_pass=remote_pass,
        remote_port=remote_port,
        private_key_file=private_key_file,
        ssh_common_args=ssh_common_args or "",
        ssh_extra_args=ssh_extra_args or "",
        sftp_extra_args=sftp_extra_args,
        scp_extra_args=scp_extra_args,
        become=become,
        become_method=become_method,
        become_user=become_user,
        verbosity=verbosity,
        extra_vars=extra_vars or [],
        check=check,
        diff=False
    )

    self.runner = PlaybookExecutor(
        playbooks=[self.playbook_path],
        inventory=self.inventory,
        variable_manager=self.variable_manager,
        loader=self.loader,
        options=self.options,
        passwords=self.passwords
    )
    if self.runner._tqm:
      self.runner._tqm._stdout_callback = self.callbackmodule

  def run(self):
    if not self.inventory.list_hosts("all"):
      raise AnsibleError("Inventory is empty.")

    try:
      self.runner.run()
      return self.callbackmodule.output
    except Exception as e:
      raise Exception(e)
    finally:
      if self.loader:
        self.loader.cleanup_all_tmp_files()
      if os.path.exists(self.file_name):
        os.remove(self.file_name)
