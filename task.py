"""
Task objects
"""
import os
import re
import yaml
import shlex
import subprocess
from glob import glob


CONFIGS = os.path.join(os.path.dirname(__file__), 'tasks/*.yml')


class Task(dict):
    """
    The Task object.  Stores all the task attributes and the run command to execute the task.
    """
    def __init__(
        self,
        name,
        command,
        triggers=None,
        # type=None,
        log=None,
        messages=None,
        parameters=None,
        # queue=None,
        parentSuccess=False,
        replay=None,
        configSource=None,
        requiredArgs=None,
    ):
        self["name"] = name
        self["command"] = command
        self["triggers"] = triggers
        # self["type"] = type
        self["log"] = log
        self["messages"] = messages
        # self["queue"] = queue
        self["parentSuccess"] = parentSuccess
        self["replay"] = replay
        self["configSource"] = configSource
        self["requiredArgs"] = requiredArgs
        if parameters:
            self["parameters"] = parameters
        else:
            self["parameters"] = []

        super().__init__()

    def __setitem__(self, key, value):
        if value and key in ("command", "log"):
            super().__setitem__(key, self._expandvars(value))
        else:
            super().__setitem__(key, value)

    def _expandvars(self, value):
        # Safely expand date
        pattern = re.compile(r'\$\((date.*)\)')

        try:
            dateValue = pattern.findall(value)[0]
        except IndexError:
            pass
        else:
            date_sub = subprocess.check_output(
                shlex.split(dateValue.replace("date", "/bin/date")),
                universal_newlines=True
            )
            value = pattern.sub(date_sub.splitlines()[0], value)

        # Expand environment variables
        return os.path.expandvars(value)

    def run(self):
        """
        Tasks are just shell commands, but we don't use shell=True because
        that's frowned upon.  There's quite a bit of extra work done here
        because of that.
        """
        print("RUNNING")
        if os.path.isdir(self["log"]):
            log = os.path.join(self["log"], f"{self['name']}.log")
        else:
            log = self["log"]

        cmd = shlex.split(self["command"]) + self["parameters"]

        p = subprocess.Popen(
            cmd,
            stdout=open(log, "ab"),
            stderr=subprocess.STDOUT,
            # env={"PATH": "/usr/local/bin/:/usr/bin:/bin:"},
            universal_newlines=True,
        )
        p.wait()
        p.communicate()

        return p.returncode


class Tasks:
    """
    List of tasks from parsing a config file.
    """
    def __init__(self):
        self.tasks = []

        for config in glob(CONFIGS):
            with open(config, 'r') as cfg:
                tmp = yaml.full_load(cfg)

                for task in tmp:
                    task["configSource"] = os.path.basename(config)

                    self.tasks.append(Task(**task))

    def get_tasks_by_trigger(self, trigger):
        return [task for task in self.tasks if trigger in task["triggers"]]


class Node:
    def __init__(self, name, data):
        self._name = name
        self._data = data

    def __repr__(self):
        return self._name

    @property
    def name(self):
        return self._name

    @property
    def data(self):
        return self._data


class Edge:
    pass


class Graph:
    pass
