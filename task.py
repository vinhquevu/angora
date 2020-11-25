"""
Angora Task
"""
import os
import re
import yaml
import shlex
import functools
import subprocess
from glob import glob
from typing import List, Dict, Optional, Union, TextIO


class Task(dict):
    """
    The Task object.  Stores all the task attributes and the run command to
    execute the task.  Inherits dict to make it JSON serializable.
    """

    def __init__(
        self,
        name: str,
        command: str,
        triggers: Optional[List] = None,
        log: Optional[str] = None,
        messages: List = [],
        parameters: List = [],
        parent_success: bool = False,
        replay: Optional[int] = None,
        config_source: Optional[str] = None,
        parents: Optional[List] = None,
    ) -> None:
        self["name"] = name
        self["command"] = command
        self["triggers"] = triggers
        self["log"] = log
        self["parent_success"] = parent_success
        self["replay"] = replay
        self["config_source"] = config_source
        self["parents"] = parents
        self["messages"] = messages
        self["parameters"] = parameters

        super().__init__()

    def __setitem__(self, key: str, value: Union[str, int, bool, List]) -> None:
        if value and key == "command":
            super().__setitem__(key, self._expandvars(str(value)))
        elif value and key == "log":
            filename = self._expandvars(str(value))

            if os.path.isdir(filename):
                name = self["name"].lower().replace(" ", "_")
                log = os.path.join(filename, f"{name}.log")
            else:
                log = filename

            super().__setitem__(key, log)
        else:
            super().__setitem__(key, value)

    def _expandvars(self, value: str) -> str:
        """
        If you're not a stickler on the shell=True thing, then this is not
        necessary.
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

    def run(self) -> int:
        """
        Tasks are just shell commands, but we don't use shell=True because
        that's frowned upon.  There's quite a bit of extra work done here
        because of that.
        """
        if self["log"]:
            out = open(self["log"], "a")  # type: Union[int, TextIO]
        else:
            out = subprocess.PIPE

        cmd = shlex.split(self["command"]) + self["parameters"]
        p = subprocess.Popen(
            cmd,
            stdout=out,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        p.wait()
        p.communicate()

        return p.returncode

    def log(self, text: str) -> None:
        if self["log"]:
            with open(self["log"], "a") as log:
                log.write(text)
        else:
            print(text)


class Tasks:
    """
    List of tasks from parsing a config file.
    """

    def __init__(self, configs: str) -> None:
        self.configs = configs
        self.tasks = []  # type: List[Task]
        self.__tree = Graph()

        self.reload()

    def reload(self) -> None:
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

        for config in glob(self.configs):
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
    def get_tasks_by_trigger(self, trigger: str) -> List:
        return [task for task in self.tasks if trigger in task["triggers"]]

    @functools.lru_cache(maxsize=None)
    def get_task_by_name(self, name: str) -> Union[Task, None]:
        for task in self.tasks:
            if task["name"] == name:
                return task

        return None

    @functools.lru_cache(maxsize=None)
    def get_child_tree(self, name: str) -> Dict:
        children = {name: []}  # type: Dict[str, List[str]]

        for edge in self.__tree.edges:
            if name == edge.source:
                children[name].append(edge.destination)
                children.update(self.get_child_tree(edge.destination))

        return children

    @functools.lru_cache(maxsize=None)
    def get_parent_tree(self, name: str) -> Dict:
        parents = {name: []}  # type: Dict[str, List[str]]

        for edge in self.__tree.edges:
            if name == edge.destination:
                parents[name].append(edge.source)
                parents.update(self.get_parent_tree(edge.source))

        return parents


class Edge:
    def __init__(self, name: str, source: str, destination: str) -> None:
        self.name = name
        self.source = source
        self.destination = destination

    def __repr__(self) -> str:
        return f"{self.name}: {self.source} -> {self.destination}"


class Graph:
    def __init__(self) -> None:
        self.edges = []  # type: List[Edge]

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def __repr__(self) -> str:
        return f"edges: {str(self.edges)}"
