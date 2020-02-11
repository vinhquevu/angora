"""
Task objects
"""
import os
import re
import yaml
import shlex
import functools
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
        # children=None,
        parents=None,
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
        self["parents"] = parents

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
        if value and key == "command":
            super().__setitem__(key, self._expandvars(value))
        elif value and key == "log":
            filename = self._expandvars(value)

            if os.path.isdir(filename):
                name = self["name"].lower().replace(" ", "_")
                log = os.path.join(filename, f"{name}.log")
            else:
                log = filename

            super().__setitem__(key, log)
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
        if self["log"]:
            out = open(self["log"], "a")
        else:
            out = subprocess.PIPE

        cmd = shlex.split(self["command"]) + self["parameters"]
        p = subprocess.Popen(
            cmd,
            stdout=out,
            stderr=subprocess.STDOUT,
            # env={"PATH": "/usr/local/bin/:/usr/bin:/bin:"},
            universal_newlines=True,
        )
        p.wait()
        p.communicate()

        return p.returncode

    def log(self, text):
        if self["log"]:
            with open(self["log"], "a") as log:
                log.write(text)
        else:
            print(text)


class Tasks:
    """
    List of tasks from parsing a config file.
    """

    def __init__(self):
        self.tasks = []
        self.__tree = Graph()

        self.reload()

    def reload(self):
        """
        Refresh the task list via a separate function.  This way you can pick up
        any changes without restarting anything.

        First create a list of Task objects by scanning all the config files. 
        Afterward we loop over the tasks several times to create all the edges,
        which are used for determining the parent and child trees for each task.
         For the parent tree, we store the immdiate parents in each task.  We
        don't store the immediate childrem because there isn't a use for that
        data yet.
        """
        self.tasks.clear()
        self.get_tasks_by_trigger.cache_clear()
        self.get_task_by_name.cache_clear()
        self.get_child_tree.cache_clear()
        self.get_parent_tree.cache_clear()
        
        for config in glob(CONFIGS):
            with open(config, "r") as cfg:
                tmp = yaml.full_load(cfg)

                for task in tmp:
                    task["config_source"] = os.path.basename(config)

                    self.tasks.append(Task(**task))

        _in = []
        _out = []

        for task in self.tasks:
            for message in task["messages"]:
                _out.append((task["name"], message))

            for trigger in task["triggers"]:
                _in.append((task["name"], trigger))

        for overtex, oedge in _out:
            for ivertex, iedge in _in:
                if oedge == iedge:
                    self.__tree.add_edge(Edge(iedge, overtex, ivertex))

        for task in self.tasks:
            task["parents"] = self.get_parent_tree(task["name"])[task["name"]]

    @functools.lru_cache(maxsize=None)
    def get_tasks_by_trigger(self, trigger):
        return [task for task in self.tasks if trigger in task["triggers"]]

    @functools.lru_cache(maxsize=None)
    def get_task_by_name(self, name):
        for task in self.tasks:
            if task["name"] == name:
                return task
        
        return None

    @functools.lru_cache(maxsize=None)
    def get_child_tree(self, name):
        children = {name: []}

        for edge in self.__tree.edges:
            if name == edge.source:
                children[name].append(edge.destination)
                children.update(self.get_child_tree(edge.destination))

        return children

    @functools.lru_cache(maxsize=None)
    def get_parent_tree(self, name):
        parents = {name: []}

        for edge in self.__tree.edges:
            if name == edge.destination:
                parents[name].append(edge.source)
                parents.update(self.get_parent_tree(edge.source))

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
        return f"{self.name}: {self.source} -> {self.destination}"


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
