
import time

from tcp_tests import logger
from tcp_tests.helpers.log_helpers import pretty_repr

LOG = logger.logger


class ExecuteCommandsMixin(object):
    """docstring for ExecuteCommands"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay
        super(ExecuteCommandsMixin, self).__init__()

    def execute_commands(self, commands, label="Command"):
        """Execute a sequence of commands

        Main propose is to implement workarounds for salt formulas like:
        - exit_code == 0 when there are actual failures
        - salt_master and/or salt_minion stop working after executing a formula
        - a formula fails at first run, but completes at next runs

        :param label: label of the current sequence of the commands, for log
        :param commands: list of dicts with the following data:
        commands = [
            ...
            {
                # Required:
                'cmd': 'shell command(s) to run',
                'node_name': 'name of the node to run the command(s)',
                # Optional:
                'description': 'string with a readable command description',
                'retry': {
                    'count': int,  # How many times should be run the command
                                   # until success
                    'delay': int,  # Delay between tries in seconds
                },
                'skip_fail': bool  # If True - continue with the next step
                                   # without failure even if count number
                                   # is reached.
                                   # If False - rise an exception (default)
            },
            ...
        ]
        """
        for n, step in enumerate(commands):
            # Required fields
            action_cmd = step.get('cmd')
            action_do = step.get('do')
            action_upload = step.get('upload')
            action_download = step.get('download')
            # node_name = step.get('node_name')
            # Optional fields
            description = step.get('description', action_cmd)
            # retry = step.get('retry', {'count': 1, 'delay': 1})
            # retry_count = retry.get('count', 1)
            # retry_delay = retry.get('delay', 1)
            # skip_fail = step.get('skip_fail', False)

            msg = "[ {0} #{1} ] {2}".format(label, n + 1, description)
            log_msg = "\n\n{0}\n{1}".format(msg, '=' * len(msg))

            if action_cmd:
                self.execute_command(step, msg)
            elif action_do:
                self.command2(step, msg)
            elif action_upload:
                LOG.info(log_msg)
                self.action_upload(step)
            elif action_download:
                LOG.info(log_msg)
                self.action_download(step)

    def execute_command(self, step, msg, return_res=None):
        # Required fields
        cmd = step.get('cmd')
        node_name = step.get('node_name')
        # Optional fields
        description = step.get('description', cmd)
        retry = step.get('retry', {'count': 1, 'delay': 1})
        retry_count = retry.get('count', 1)
        retry_delay = retry.get('delay', 1)
        skip_fail = step.get('skip_fail', False)

        with self.__underlay.remote(node_name=node_name) as remote:

            for x in range(retry_count, 0, -1):
                time.sleep(3)

                retry_msg = (' (try {0} of {1}, skip_fail={2}, node_name={3})'
                             .format(retry_count - x + 1,
                                     retry_count,
                                     skip_fail,
                                     node_name))
                LOG.info("\n\n{0}\n{1}".format(
                    msg + retry_msg, '=' * len(msg + retry_msg)))

                result = remote.execute(cmd, verbose=True)
                if return_res:
                    return result

                # Workaround of exit code 0 from salt in case of failures
                failed = 0
                for s in result['stdout'] + result['stderr']:
                    if s.startswith("Failed:"):
                        failed += int(s.split("Failed:")[1])
                    if 'Minion did not return. [No response]' in s:
                        failed += 1
                    if 'Minion did not return. [Not connected]' in s:
                        failed += 1
                    if s.startswith("[CRITICAL]"):
                        failed += 1
                    if 'Fatal' in s:
                        failed += 1

                if result.exit_code != 0:
                    time.sleep(retry_delay)
                elif failed != 0:
                    LOG.error(
                        " === SALT returned exit code = 0 while "
                        "there are failed modules! ===")
                    time.sleep(retry_delay)
                else:
                    break

                if x == 1 and skip_fail is False:
                    # In the last retry iteration, raise an exception
                    raise Exception("Step '{0}' failed"
                                    .format(description))

    def command2(self, step, msg):
        # Required fields
        do = step['do']
        target = step['target']
        state = step.get('state')
        states = step.get('states')
        # Optional fields
        args = step.get('args')
        kwargs = step.get('kwargs')
        description = step.get('description', do)
        retry = step.get('retry', {'count': 1, 'delay': 1})
        retry_count = retry.get('count', 1)
        retry_delay = retry.get('delay', 1)
        skip_fail = step.get('skip_fail', False)

        if not bool(state) ^ bool(states):
            raise ValueError("You should use state or states in step")

        for x in range(retry_count, 0, -1):
            time.sleep(3)

            retry_msg = (' (try {0} of {1}, skip_fail={2}, target={3})'
                         .format(retry_count - x + 1,
                                 retry_count,
                                 skip_fail,
                                 target))
            LOG.info("\n\n{0}\n{1}".format(
                msg + retry_msg, '=' * len(msg + retry_msg)))

            method = getattr(self._salt, self._salt._map[do])
            command_ret = method(tgt=target, state=state or states,
                                 args=args, kwargs=kwargs)
            command_ret = command_ret if \
                isinstance(command_ret, list) else [command_ret]
            results = [(r['return'][0], f) for r, f in command_ret]

            # FIMME: Change to debug level
            LOG.info(" === States output =======================\n"
                     "{}\n"
                     " =========================================".format(
                         pretty_repr([r for r, f in results])))

            all_fails = [f for r, f in results if f]
            if all_fails:
                LOG.error("States finished with failures.\n{}".format(
                    all_fails))
                time.sleep(retry_delay)
            else:
                break

            if x == 1 and skip_fail is False:
                # In the last retry iteration, raise an exception
                raise Exception("Step '{0}' failed"
                                .format(description))

    def action_upload(self, step):
        """Upload from local host to environment node

        Example:

        - description: Upload a file
          upload:
            local_path: /tmp/
            local_filename: cirros*.iso
            remote_path: /tmp/
          node_name: ctl01
          skip_fail: False
        """
        node_name = step.get('node_name')
        local_path = step.get('upload', {}).get('local_path', None)
        local_filename = step.get('upload', {}).get('local_filename', None)
        remote_path = step.get('upload', {}).get('remote_path', None)
        description = step.get('description', local_path)
        skip_fail = step.get('skip_fail', False)

        if not local_path or not remote_path:
            raise Exception("Step '{0}' failed: please specify 'local_path', "
                            "'local_filename' and 'remote_path' correctly"
                            .format(description))

        if not local_filename:
            # If local_path is not specified then uploading a directory
            with self.__underlay.remote(node_name=node_name) as remote:
                LOG.info("Uploading directory {0} to {1}:{2}"
                         .format(local_path, node_name, remote_path))
                remote.upload(source=local_path.rstrip(),
                              target=remote_path.rstrip())
                return

        result = {}
        with self.__underlay.local() as local:
            result = local.execute('cd {0} && find . -type f -name "{1}"'
                                   .format(local_path, local_filename))
            LOG.info("Found files to upload:\n{0}".format(result))

        if not result['stdout'] and not skip_fail:
            raise Exception("Nothing to upload on step {0}"
                            .format(description))

        with self.__underlay.remote(node_name=node_name) as remote:
            file_names = result['stdout']
            for file_name in file_names:
                source_path = local_path + file_name.rstrip()
                destination_path = remote_path.rstrip() + file_name.rstrip()
                LOG.info("Uploading file {0} to {1}:{2}"
                         .format(source_path, node_name, remote_path))
                remote.upload(source=source_path, target=destination_path)

    def action_download(self, step):
        """Download from environment node to local host

        Example:

        - description: Download a file
          download:
            remote_path: /tmp/
            remote_filename: report*.html
            local_path: /tmp/
          node_name: ctl01
          skip_fail: False
        """
        node_name = step.get('node_name')
        remote_path = step.get('download', {}).get('remote_path', None)
        remote_filename = step.get('download', {}).get('remote_filename', None)
        local_path = step.get('download', {}).get('local_path', None)
        description = step.get('description', remote_path)
        skip_fail = step.get('skip_fail', False)

        if not remote_path or not remote_filename or not local_path:
            raise Exception("Step '{0}' failed: please specify 'remote_path', "
                            "'remote_filename' and 'local_path' correctly"
                            .format(description))

        with self.__underlay.remote(node_name=node_name) as remote:

            result = remote.execute('find {0} -type f -name {1}'
                                    .format(remote_path, remote_filename))
            LOG.info("Found files to download:\n{0}".format(result))

            if not result['stdout'] and not skip_fail:
                raise Exception("Nothing to download on step {0}"
                                .format(description))

            file_names = result['stdout']
            for file_name in file_names:
                LOG.info("Downloading {0}:{1} to {2}"
                         .format(node_name, file_name, local_path))
                remote.download(destination=file_name.rstrip(),
                                target=local_path)
