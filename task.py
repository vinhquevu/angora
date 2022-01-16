"""
Angora Task
"""
import functools
import os
import re
import shlex
import subprocess
from glob import glob
from typing import Any, Dict, List, Optional, TextIO, Union

import yaml


class Task(dict):
    """
    The Task object.  Stores all the task attributes and the run() method to
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
        self.name = name
        self.command = command
        self.triggers = triggers
        self.log = log
        self.parent_success = parent_success
        self.replay = replay
        self.config_source = config_source
        self.parents = parents  # For determining parent success
        self.messages = messages
        self.parameters = parameters

    def __repr__(self) -> str:
        return (
            f"NAME: {self.name}\n"
            f"COMMAND: {self.command}\n"
            f"TRIGGERS: {self.triggers}\n"
            f"LOG: {self.log}\n"
            f"PARENT_SUCCESS: {self.parent_success}\n"
            f"REPLAY: {self.replay}\n"
            f"CONFIG_SOURCE: {self.config_source}\n"
            f"PARENTS: {self.parents}\n"
            f"MESSAGES: {self.messages}\n"
            f"PARAMETERS: {self.parameters}\n"
        )

    @property
    def command(self) -> str:
        return self._command

    @command.setter
    def command(self, value: str) -> None:
        self._command = self._expandvars(value)

    @property
    def log(self) -> str:
        return self._log

    @log.setter
    def log(self, value) -> None:
        self._log = self._expandvars(str(value))

        if os.path.isdir(self._log):
            name = self.name.lower().replace(" ", "_")
            self._log = os.path.join(self._log, f"{name}.log")

    def _expandvars(self, value: str) -> str:
        """
        If you're not a stickler on the shell=True thing, then this is not
        necessary.  Currently handles dates and envrionment variables.
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
        if self.log:
            out = open(self.log, "a")  # type: Union[int, TextIO]
        else:
            out = subprocess.PIPE

        cmd = shlex.split(self.command) + (self.parameters if self.parameters else [])

        p = subprocess.Popen(
            cmd,
            stdout=out,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        p.wait()
        p.communicate()

        return p.returncode

    def write_log(self, text: str) -> None:
        if self.log:
            with open(self.log, "a") as log:
                log.write(text)
        else:
            print(text)  # TODO: Don't use print

    def dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "command": self.command,
            "triggers": self.triggers,
            "log": self.log,
            "parent_success": self.parent_success,
            "replay": self.replay,
            "config_source": self.config_source,
            "parents": self.parents,
            "messages": self.messages,
            "parameters": self.parameters,
        }


class Tasks:
    """
    List of tasks from parsing a config file.

    Once the list of tasks is constructed, this class has several methods to
    make accessing tasks in different ways simpler.
    """

    def __init__(self, configs: str) -> None:
        self.configs = configs
        self._tasks = []  # type: List[Task]
        self.__tree = Graph()

        self.reload()

    def __iter__(self):
        self.__index = 0
        return self

    def __next__(self):
        if self.__index < len(self._tasks):
            result = self._tasks[self.__index]
            self.__index += 1
            return result
        else:
            raise StopIteration

    @functools.lru_cache(maxsize=None)
    def get_tasks_by_trigger(self, trigger: str) -> List:
        return [task for task in self._tasks if trigger in task.triggers]

    @functools.lru_cache(maxsize=None)
    def get_task_by_name(self, name: str) -> Union[Task, None]:
        for task in self._tasks:
            if task.name == name:
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

    def reload(self) -> None:
        """
        Refresh the task list via a separate function.  This way you can pick up
        any changes without restarting anything.

        First create a list of Task objects by scanning all the config files.
        Afterward we loop over the tasks several times to create all the edges,
        which are used for determining the parent and child trees for each task.
        For the parent tree, we store the immediate parents in each task.  We
        don't store the immediate children because there isn't a use for that
        data yet.
        """
        self._tasks.clear()
        self.get_tasks_by_trigger.cache_clear()
        self.get_task_by_name.cache_clear()
        self.get_child_tree.cache_clear()
        self.get_parent_tree.cache_clear()

        for config in glob(self.configs):
            with open(config, "r") as cfg:
                tmp = yaml.full_load(cfg)

                for task in tmp:
                    task["config_source"] = os.path.basename(config)

                    self._tasks.append(Task(**task))

        for task in self._tasks:
            out_ = [(task.name, message) for message in task.messages]
            in_ = [(task.name, trigger) for trigger in task.triggers]

        for overtex, oedge in out_:
            for ivertex, iedge in in_:
                if oedge == iedge:
                    self.__tree.add_edge(Edge(iedge, overtex, ivertex))

        # get_parent_tree is recursive and we only need the first level, because
        # the function is cached and we use the data in other places we don't
        # incur a heavy penalty
        for task in self._tasks:
            task.parents = self.get_parent_tree(task.name)[task.name]


class Edge:
    """
    A connection between two tasks.

    name: The message/trigger of a Task.

    source: The task name of the calling task.  This means the "name" was in the
    messages attribute of the task.

    destination: The task name of the called task.  This means the "name" was in
    the triggers attribute of the task.

    e.g.
    name: source_task
    trigger:
        - trigger_1
    cmd: some_command_1
    messages:
        - message_1

    name: destination_task
    trigger:
        - message_1
    cmd: some_command_2
    messages:
        - message_2

    Result: Edge<message_1, source_task, destination_task>

    """

    def __init__(self, name: str, source: str, destination: str) -> None:
        self.name = name
        self.source = source
        self.destination = destination

    def __repr__(self) -> str:
        return f"{self.name}: {self.source} -> {self.destination}"


class Graph:
    """
    The graph is a collection of edges.  The edges are formed by the message ->
    trigger relationships in the task.
    """

    def __init__(self) -> None:
        self.edges = []  # type: List[Edge]

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def __repr__(self) -> str:
        return f"edges: {str(self.edges)}"
