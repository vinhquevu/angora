"""
Task objects
"""
import os
import re
import yaml
import shlex
import subprocess
from glob import glob

from angora import CONFIGS


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
        parent_success=False,
        replay=None,
        config_source=None,
    ):
        self["name"] = name
        self["command"] = command
        self["triggers"] = triggers
        # self["type"] = type
        self["log"] = log
        # self["queue"] = queue
        self["parent_success"] = parent_success
        self["replay"] = replay
        self["config_source"] = config_source

        if messages:
            self["messages"] = messages
        else:
            self["messages"] = []

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

    # @property
    # def category(self):
    #     """
    #     Format the category name. It's the file name in upper case and
    #     spaces instead of underscores
    #     """
    #     return self["config_source"].rstrip('.yml').replace('_', ' ').upper()

    def _expandvars(self, value):
        """
        If you're not a stickler on the shell=True thing, then this is not necessary.
        """
        # Safely expand date
        pattern = re.compile(r"\$\((date.*)\)")

        try:
            dateValue = pattern.findall(value)[0]
        except IndexError:
            pass
        else:
            date_sub = subprocess.check_output(
                shlex.split(dateValue.replace("date", "/bin/date")),
                universal_newlines=True,
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
        if os.path.isdir(self["log"]):
            log = os.path.join(self["log"], f"{self['name']}.log")
        else:
            log = self["log"]

        cmd = shlex.split(self["command"]) + self["parameters"]
        print(cmd)
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
        """
        tasks
        -----

        trees
        -----

        """

        self.tasks = []
        self.trees = Graph()

        for config in glob(CONFIGS):
            with open(config, "r") as cfg:
                tmp = yaml.full_load(cfg)

                for task in tmp:
                    task["config_source"] = os.path.basename(config)

                    self.tasks.append(Task(**task))

        __in = []
        __out = []
        for task in self.tasks:
            # self.trees.add_node(Node(task["name"], task))

            for trigger in task["triggers"]:
                __in.append((task["name"], trigger))

            for message in task["messages"]:
                __out.append((task["name"], message))

        for overtex, oedge in __out:
            for ivertex, iedge in __in:
                if oedge == iedge:
                    self.trees.add_edge(Edge(iedge, overtex, ivertex))

    def get_tasks_by_trigger(self, trigger):
        return [task for task in self.tasks if trigger in task["triggers"]]

    def get_children(self, name):
        children = {name: []}

        for edge in self.trees.edges:
            if name == edge.source:
                children[name].append(edge.destination)
                children.update(self.get_children(edge.destination))

        return children

    def get_parents(self, name):
        parents = {name: []}

        for edge in self.trees.edges:
            if name == edge.destination:
                parents[name].append(edge.source)
                parents.update(self.get_parents(edge.source))

        return parents



# class Node:
#     def __init__(self, name, data):
#         self.name = name
#         self.data = data

#     def __repr__(self):
#         return self.name


class Edge:
    def __init__(self, name, source, destination):
        self.name = name
        self.source = source
        self.destination = destination

    def __repr__(self):
        return f"{self.name}:{self.source}->{self.destination}"


class Graph:
    def __init__(self):
        # self.nodes = []
        self.edges = []

    # def add_node(self, node):
    #     self.nodes.append(node)

    def add_edge(self, edge):
        self.edges.append(edge)

    def __repr__(self):
        return (
            # f"nodes: {str(self.nodes)}\n\n"
            f"edges: {str(self.edges)}"
        )
