
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

    def ensure_running_service(self, service_name, host, check_cmd,
                               state_running='start/running'):
        """Check if the service_name running or try to restart it

        :param service_name: name of the service that will be checked
        :param node_name: node on which the service will be checked
        :param check_cmd: shell command to ensure that the service is running
        :param state_running: string for check the service state
        """
        cmd = "service {0} status | grep -q '{1}'".format(
            service_name, state_running)
        with self.__underlay.remote(host=host) as remote:
            result = remote.execute(cmd)
            if result.exit_code != 0:
                LOG.info("{0} is not in running state on the node {1},"
                         " trying to start".format(service_name, host))
                cmd = ("service {0} stop;"
                       " sleep 3; killall -9 {0};"
                       "service {0} start; sleep 5;"
                       .format(service_name))
                remote.execute(cmd)

                remote.execute(check_cmd)
                remote.execute(check_cmd)

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
            cmd = step.get('cmd')
            do = step.get('do')
            # node_name = step.get('node_name')
            # Optional fields
            description = step.get('description', cmd)
            # retry = step.get('retry', {'count': 1, 'delay': 1})
            # retry_count = retry.get('count', 1)
            # retry_delay = retry.get('delay', 1)
            # skip_fail = step.get('skip_fail', False)

            msg = "[ {0} #{1} ] {2}".format(label, n + 1, description)
            LOG.info("\n\n{0}\n{1}".format(msg, '=' * len(msg)))

            if cmd:
                self.execute_command(step)
            elif do:
                self.command2(step)

    def execute_command(self, step):
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
                result = remote.execute(cmd, verbose=True)

                # Workaround of exit code 0 from salt in case of failures
                failed = 0
                for s in result['stdout']:
                    if s.startswith("Failed:"):
                        failed += int(s.split("Failed:")[1])

                if result.exit_code != 0:
                    time.sleep(retry_delay)
                    LOG.info(
                        " === RETRY ({0}/{1}) ========================="
                        .format(x - 1, retry_count))
                elif failed != 0:
                    LOG.error(
                        " === SALT returned exit code = 0 while "
                        "there are failed modules! ===")
                    LOG.info(
                        " === RETRY ({0}/{1}) ======================="
                        .format(x - 1, retry_count))
                else:
                    if self.__config.salt.salt_master_host != '0.0.0.0':
                        # Workarounds for crashed services
                        self.ensure_running_service(
                            "salt-master",
                            self.__config.salt.salt_master_host,
                            "salt-call pillar.items",
                            'active (running)')  # Hardcoded for now
                        self.ensure_running_service(
                            "salt-minion",
                            self.__config.salt.salt_master_host,
                            "salt 'cfg01*' pillar.items",
                            "active (running)")  # Hardcoded for now
                        break

                if x == 1 and skip_fail is False:
                    # In the last retry iteration, raise an exception
                    raise Exception("Step '{0}' failed"
                                    .format(description))

    def command2(self, step):
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
                LOG.info(" === RETRY ({0}/{1}) ========================="
                         .format(x - 1, retry_count))
            else:
                break

            if x == 1 and skip_fail is False:
                # In the last retry iteration, raise an exception
                raise Exception("Step '{0}' failed"
                                .format(description))
