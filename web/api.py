#! /usr/bin/env python3
import os
import re
import argparse

from typing import List
from datetime import datetime
from dateutil.relativedelta import relativedelta

import uvicorn

from fastapi import FastAPI, Query
from starlette.middleware.cors import CORSMiddleware


from angora import (
    EXCHANGE,
    USER,
    PASSWORD,
    HOST,
    PORT,
    CONFIGS,
)
from angora.db import db
from angora.task import Tasks
from angora.message import Message

app = FastAPI(version="0.0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# TODO: move to startup class
TASKS = Tasks(CONFIGS)


@app.get("/send")
async def send(
    message: str, queue: str, routing_key: str, params: List[str] = Query([])
):
    """
    Send a message to Angora
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
    all_tasks = TASKS.tasks

    if name:
        all_tasks = [task for task in all_tasks if task["name"] == name]

    return {"data": all_tasks}


@app.get("/tasks/reload")
async def reload_tasks():
    TASKS.reload()


@app.get("/tasks/today/notrun")
async def get_tasks_notrun():
    all_tasks = TASKS.tasks
    tasks_today = {_["name"] for _ in db.get_tasks_today()}

    notrun = [task for task in all_tasks if task["name"] not in tasks_today]

    return {"data": notrun}


@app.get("/tasks/today/{status}")
async def get_tasks_today(status=None):
    tasks = db.get_tasks_today(status=status)

    return {"data": tasks}


@app.get("/tasks/lastruntime")
async def get_tasks_last_run_time(name=None):
    """
    Return a list of tasks with the last run time stats.  The tasks returned
    will not be Task objects, instead the process will serialize the object
    into a dictionary (json) and you'll lose any attributes associated with
    the Task object.
    """
    all_tasks = TASKS.tasks
    last_task = db.get_tasks_latest()

    if name:
        all_tasks = [task for task in all_tasks if task["name"] == name]

    for task in all_tasks:
        status = None
        time_stamp = None
        last_run_time = "Never"

        for lt in last_task:
            if lt["name"] == task["name"]:
                status = lt["status"]

                if not time_stamp:
                    time_stamp = lt["time_stamp"]
                elif lt["time_stamp"] > time_stamp:
                    time_stamp = lt["time_stamp"]

                delta = relativedelta(datetime.utcnow(), time_stamp)

                last_run_time = "{} hr {} min {} sec".format(
                    delta.hours, delta.minutes, delta.seconds
                )

        task["status"] = status
        task["time_stamp"] = time_stamp
        task["last_run_time"] = last_run_time

    return {"data": all_tasks}


def _format_category(category):
    """
    For convenience. This assumes a snake case naming convention for task yaml config files.
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

    data = {}

    for task in tasks["data"]:
        data.setdefault(_format_category(task["config_source"]), []).append(task)

    return {"data": data}


@app.get("/tasks/scheduled")
async def get_tasks_scheduled():
    tasks = await get_tasks_last_run_time()

    pattern = re.compile(r"time.\d{4}")

    scheduled_tasks = {}

    for task in tasks["data"]:
        for trigger in task["triggers"]:
            if pattern.match(trigger):
                time = f"{trigger[5:7]}:{trigger[7:9]}"

                scheduled_tasks.setdefault(time, []).append(task)

    return {"data": scheduled_tasks}


@app.get("/tasks/repeating")
async def get_tasks_repeating():
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
    This assumes that logs are files that are accessible to the api.
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
    return {"data": TASKS.get_child_tree(name)}


@app.get("/task/parents")
async def get_task_parents(name):
    return {"data": TASKS.get_parent_tree(name)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", default=55550, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("api:app", host="0.0.0.0", port=args.port, reload=args.reload)
