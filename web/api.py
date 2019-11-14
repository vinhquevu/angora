#! /usr/bin/env python3
import re
import argparse

from datetime import datetime
from dateutil.relativedelta import relativedelta

import uvicorn

from fastapi import FastAPI

from starlette.middleware.cors import CORSMiddleware

from angora import EXCHANGE, USER, PASSWORD, HOST, PORT
from angora.db import db
from angora.task import Tasks
from angora.message import Message

app = FastAPI(version="0.0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"])


@app.get("/send")
async def send(message, queue, routing_key, params=None):
    """
    Send a message to Angora
    """
    msg = Message(EXCHANGE, queue, message, data=params)

    try:
        msg.send(USER, PASSWORD, HOST, PORT, routing_key)
    except AttributeError:
        status = "error"
    else:
        status = "ok"

    return {"status": status, "message": message}


@app.get("/tasks/lastruntime")
async def get_tasks_last_run_time():
    """
    Return a list of tasks with the last run time stats.  The tasks returned
    will not be Task objects, instead the process will serialize the object
    into a dictionary (json) and you'll lose any attributes associated with
    the Task object.
    """
    all_tasks = Tasks().tasks
    last_task = db.get_tasks_latest()

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
    For convenience. This does assume a snake case naming convention for task yaml config files.
    """
    return category.rstrip(".yml").replace("_", " ").upper()


@app.get("/tasks/categories")
async def get_task_categories():
    """
    Return a list of categories, a pretty format of the config source or file
    name that task is saved.
    """
    categories = [_format_category(task["config_source"]) for task in Tasks().tasks]

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


@app.get("/tasks/history")
async def get_task_history(run_date, task_name=None):
    tasks = db.get_tasks(run_date, task_name)

    return {"data": tasks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", default=55550, type=int)
    parser.add_argument("--debug", action="store_true")
    pargs = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=pargs.port, debug=pargs.debug)
