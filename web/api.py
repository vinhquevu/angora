#! /usr/bin/env python3
import argparse
import re
from collections import defaultdict
from typing import Any, Dict, List

import uvicorn  # type: ignore
from fastapi import FastAPI, Query
from starlette.middleware.cors import CORSMiddleware

from angora import CONFIGS, EXCHANGE, HOST, PASSWORD, PORT, USER
from angora.db import db
from angora.message import Message
from angora.task import Tasks

app = FastAPI(version="0.0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"])

TASKS = Tasks(CONFIGS)


@app.get("/send")
async def send(
    message: str, queue: str, routing_key: str, params: List[str] = Query([])
):
    """
    Send a message to Angora.
    """
    print(message, queue, routing_key, params)

    try:
        Message(EXCHANGE, queue, message, data=params).send(
            USER, PASSWORD, HOST, PORT, routing_key
        )
    except AttributeError:
        status = "error"
    else:
        status = "ok"

    return {"status": status, "data": message}


@app.get("/tasks")
async def get_tasks(name=None):
    """
    Retrieve a task(s).
    """
    all_tasks = TASKS.tasks

    if name:
        all_tasks = [task for task in all_tasks if task["name"] == name]

    return {"data": all_tasks}


@app.get("/tasks/reload")
async def reload_tasks():
    """
    Refresh data in tasks object
    """
    TASKS.reload()


@app.get("/tasks/today/notrun")
async def get_tasks_notrun():
    # all_tasks = TASKS.tasks
    tasks_today = {_["name"] for _ in db.get_tasks_today()}

    notrun = [task for task in TASKS if task["name"] not in tasks_today]

    return {"data": notrun}


@app.get("/tasks/today/{status}")
async def get_tasks_today(status=None):
    """
    Return tasks run today with a certain status.  If status is left blank, then
    return all teaks run today.
    """
    tasks = db.get_tasks_today(status=status)

    return {"data": tasks}


@app.get("/tasks/lastruntime")
async def get_tasks_last_run_time(name=None):
    """
    Return a list of tasks with the last run time stats.  The tasks returned
    will not be Task objects, instead the process will serialize the object into
    a dictionary (json) and you'll lose any attributes associated with the Task
    object.

    TODO: make db.get_tasks_latest() accept an arg for better performance. Make
    TASKS work when passing in a key.
    """
    all_tasks = TASKS.tasks
    last_task = db.get_tasks_latest()

    if name:
        all_tasks = [task for task in all_tasks if task["name"] == name]

    for task in all_tasks:
        status = None
        time_stamp = None

        for lt in last_task:
            if lt["name"] == task["name"]:
                status = lt["status"]

                if not time_stamp:
                    time_stamp = lt["time_stamp"]
                elif lt["time_stamp"] > time_stamp:
                    time_stamp = lt["time_stamp"]

        task["status"] = status
        task["time_stamp"] = time_stamp

    return {"data": all_tasks}


def _format_category(category):
    """
    For convenience. This assumes a snake case naming convention for task yaml
    config files.
    """
    return category.rstrip(".yml").rstrip(".yaml").replace("_", " ").upper()


@app.get("/tasks/categories")
async def get_task_categories():
    """
    Return a list of categories, a pretty format of the config source or file
    name that task is saved.
    """
    categories = [_format_category(task["config_source"]) for task in TASKS.tasks]

    return {"data": sorted(set(categories))}


@app.get("/tasks/lastruntime/sorted/category")
async def get_task_last_run_time_by_category():
    tasks = await get_tasks_last_run_time()

    data = defaultdict(lambda: [])

    for task in tasks["data"]:
        data[_format_category(task["config_source"])].append(task)

    return {"data": data}


@app.get("/tasks/scheduled")
async def get_tasks_scheduled():
    """
    Retrieve all tasks that have a time trigger
    """
    tasks = await get_tasks_last_run_time()

    # Hard coded pattern for time messages
    pattern = re.compile(r"time.\d{4}")

    scheduled_tasks = defaultdict(lambda: [])

    for task in tasks["data"]:
        for trigger in task["triggers"]:
            if pattern.match(trigger):
                time = f"{trigger[5:7]}:{trigger[7:9]}"

                scheduled_tasks[time].append(task)

    scheduled_tasks = {key: scheduled_tasks[key] for key in sorted(scheduled_tasks)}
    return {"data": scheduled_tasks}


@app.get("/tasks/repeating")
async def get_tasks_repeating():
    """
    Retrieve all tasks that have a repeating interval trigger
    """
    tasks = await get_tasks_last_run_time()

    pattern = re.compile(r"time.interval.\d+")

    repeating_tasks = {}

    for task in tasks["data"]:
        for trigger in task["triggers"]:
            if pattern.match(trigger):
                interval = trigger.split(".")[-1]
                repeating_tasks.setdefault(interval, []).append(task)

    return {"data": repeating_tasks}


@app.get("/task/history")
async def get_task_history(run_date, name):
    tasks = db.get_tasks(run_date, name)

    return {"data": tasks}


@app.get("/task/log")
async def get_task_log(name):
    """
    This assumes that logs are files that are accessible to the API.
    """
    for task in TASKS.tasks:
        if task["name"] == name:
            if not task.get("log"):
                return {"ok": True, "data": "TASK NOT LOGGED"}

            log = task.get("log")
            break
    else:
        return {"data": "NO MATCHING TASK"}

    try:
        with open(log, "r") as _:
            return {"ok": True, "data": "".join(_.readlines()[-100:])}
    except IOError:
        return {"data": "LOG FILE MISSING"}


@app.get("/task/children")
async def get_task_children(name):
    """
    Retrieve all the child tasks for a specified task.
    """
    return {"data": TASKS.get_child_tree(name)}


@app.get("/task/children/lastruntime")
async def get_task_children_lastruntime(name):
    """
    Retrieve all the child tasks for a specified task but also include the
    status and runtime of the most recently run instance.
    """

    child_tree = TASKS.get_child_tree(name)
    tasks_lastruntime = await get_tasks_last_run_time()

    data = {}

    for task_name, children in child_tree.items():
        for task in tasks_lastruntime["data"]:
            if task["name"] == task_name:
                data[task_name] = {
                    "status": task["status"],
                    "time_stamp": task["time_stamp"],
                    "children": children,
                }
                break

    return {"data": data}


@app.get("/task/parents")
async def get_task_parents(name):
    """
    Retrieve all the parent tasks for a specified task.
    """
    return {"data": TASKS.get_parent_tree(name)}


@app.get("/task/parents/lastruntime")
async def get_task_parents_lastruntime(name):
    """
    Retrieve all the parent tasks for a specified task but also include the
    status and runtime of the most recently run instance.
    """
    parent_tree = TASKS.get_parent_tree(name)
    tasks_lastruntime = await get_tasks_last_run_time()

    data = {}

    for task_name, parents in parent_tree.items():
        for task in tasks_lastruntime["data"]:
            if task["name"] == task_name:
                data[task_name] = {
                    "status": task["status"],
                    "time_stamp": task["time_stamp"],
                    "parents": parents,
                }
                break

    return {"data": data}


@app.get("/task/family/lastruntime")
async def get_family_tree(name: str) -> Dict[str, Any]:
    """
    Retrieve parents and children and combine into one dictionary.

    NOTE: The root, or task passed in as name, will be the only task with both a
    "parents" and "children" key.

    In Python 3.9+ you can use the "|"
    """

    children = await get_task_children_lastruntime(name)
    parents = await get_task_parents_lastruntime(name)

    data = defaultdict(lambda: {})  # type: Dict[str, Dict[str, Any]]

    for task_name, value in parents["data"].items():
        data[task_name] = {**data[task_name], **value}

    for task_name, value in children["data"].items():
        data[task_name] = {**data[task_name], **value}

    return {"data": data}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", default=55550, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("api:app", host="0.0.0.0", port=args.port, reload=args.reload)
