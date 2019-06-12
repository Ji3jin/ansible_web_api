#!/usr/bin/env python
# coding:utf8
import os
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
import ansible.constants as C
import ansible.cli
from ansible.errors import AnsibleError
from app import current_config
import time

base_dir = current_config.DATA_PATH

__all__ = ["Runner"]

# free to report host to `known_hosts` file.
C.HOST_KEY_CHECKING = False

# class Options
Options = namedtuple('Options',
                     ['connection', 'module_path', 'forks', 'remote_user',
                      'remote_port',
                      'private_key_file', 'ssh_common_args',
                      'ssh_extra_args',
                      'sftp_extra_args',
                      'scp_extra_args', 'become', 'become_method',
                      'become_user', 'verbosity', 'check',
                      'diff'])


class ResultCallback(CallbackBase):
  """
  Custom Callback
  """

  def __init__(self):
    self.result_q = dict(contacted={}, failed={}, unreachable={}, skipped={})

  def gather_result(self, n, res):
    self.result_q[n].update({res._host.name: res._result})

  def v2_runner_on_ok(self, result):
    self.gather_result("contacted", result)

  def v2_runner_on_failed(self, result, ignore_errors=False):
    self.gather_result("failed", result)

  def v2_runner_on_unreachable(self, result):
    self.gather_result("unreachable", result)

  def v2_runner_on_skipped(self, result):
    self.gather_result("skipped", result)

  def v2_playbook_on_task_start(self, task, is_conditional):
    pass

  def v2_playbook_on_play_start(self, play):
    pass


class Runner(object):
  """
  仿照ansible1.9 的python API,制作的ansible2.0 API的简化版本。
  参数说明:
      inventory:: 仓库对象，可以是列表，逗号间隔的ip字符串,可执行文件. 默认/etc/ansible/hosts
      module_name:: 指定要使用的模块
      module_args:: 模块参数
      forks:: 并发数量, 默认5
      timeout:: 连接等待超时时间，默认10秒
      pattern:: 模式匹配，指定要连接的主机名, 默认all
      remote_user:: 指定连接用户, 默认root
      private_key_files:: 指定私钥文件
  """

  def __init__(
      self,
      hosts=C.DEFAULT_HOST_LIST,
      module_name=C.DEFAULT_MODULE_NAME,  # * command
      module_args=C.DEFAULT_MODULE_ARGS,  # * 'cmd args'
      forks=C.DEFAULT_FORKS,  # 5
      timeout=C.DEFAULT_TIMEOUT,  # SSH timeout = 10s
      pattern="all",  # all
      remote_user=C.DEFAULT_REMOTE_USER,  # root
      module_path=None,  # dirs of custome modules
      connection_type="smart",
      become=None,
      become_method=None,
      become_user=None,
      check=False,
      passwords=None,
      extra_vars=None,
      private_key_file=C.DEFAULT_PRIVATE_KEY_FILE,
      remote_pass=C.DEFAULT_REMOTE_PASS,
      remote_port=None
  ):

    # storage & defaults
    self.pattern = pattern
    self.loader = DataLoader()
    self.module_name = module_name
    self.module_args = module_args
    self.check_module_args()
    self.gather_facts = 'no'
    self.resultcallback = ResultCallback()
    self.options = Options(
        connection=connection_type,
        ssh_common_args=None, ssh_extra_args=None,
        sftp_extra_args=None, scp_extra_args=None,
        module_path=module_path,
        forks=forks,
        become=become,
        become_method=become_method,
        become_user=become_user,
        check=check,
        remote_user=remote_user,
        private_key_file=private_key_file,
        remote_port=remote_port,
        verbosity=None, diff=False
    )
    # save host to file
    if not os.path.exists(os.path.join(base_dir, "tmp_inventory")):
      os.mkdir(os.path.join(base_dir, "tmp_inventory"))
    self.file_name = os.path.join(base_dir, "tmp_inventory",
                                  "tmp_host_{0}".format(time.time()))
    with open(self.file_name, 'w') as f:
      f.write("[all]\n")
      f.write("\n".join(hosts))
      f.write("\n")
      if remote_pass:
        f.write("""[all:vars]
ansible_connection=ssh 
ansible_user={0} 
ansible_pass={1}""".format(remote_user,remote_pass))
    self.passwords = passwords or {}
    self.inventory = InventoryManager(loader=self.loader,
                                      sources=self.file_name)
    self.variable_manager = VariableManager(loader=self.loader,
                                            inventory=self.inventory)
    if self.module_name.strip() == "shell":
      self.module_args = "source ~/.bash_profile;" + self.module_args
    self.play_source = dict(
        name="Ansible Ad-hoc",
        hosts=self.pattern,
        gather_facts=self.gather_facts,
        tasks=[dict(action=dict(
            module=self.module_name, args=self.module_args),
            register='shell_out')]
    )

    self.play = Play().load(
        self.play_source, variable_manager=self.variable_manager,
        loader=self.loader)

    self.runner = TaskQueueManager(
        inventory=self.inventory,
        variable_manager=self.variable_manager,
        loader=self.loader,
        options=self.options,
        passwords=self.passwords,
        stdout_callback=self.resultcallback
    )
    # ** end __init__() **

  def run(self):
    if not self.inventory.list_hosts("all"):
      raise AnsibleError("Inventory is empty.")

    if not self.inventory.list_hosts(self.pattern):
      raise AnsibleError(
          "pattern: %s  dose not match any hosts." % self.pattern)
    try:
      self.runner.run(self.play)
      return self.resultcallback.result_q
    except Exception as e:
      raise Exception(e)
    finally:
      if self.runner:
        self.runner.cleanup()
      if self.loader:
        self.loader.cleanup_all_tmp_files()
      if os.path.exists(self.file_name):
        os.remove(self.file_name)

  def check_module_args(self):
    if self.module_name in C.MODULE_REQUIRE_ARGS and not self.module_args:
      err = "No argument passed to '%s' module." % self.module_name
      raise AnsibleError(err)


if __name__ == '__main__':
  runner = Runner(
      module_name='shell',
      module_args='ls',
      pattern='5kcluster',
      forks=10
  )
  print(runner.run())
