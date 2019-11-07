#! /usr/bin/env python3
import argparse

from datetime import datetime
from dateutil.relativedelta import relativedelta

import uvicorn

from fastapi import FastAPI

# from starlette.middleware.cors import CORSMiddleware

from angora import EXCHANGE, USER, PASSWORD, HOST, PORT
from angora.db import db
from angora.task import Tasks
from angora.message import Message

app = FastAPI(version="0.0.1")
# app.add_middleware(CORSMiddleware, allow_origins=["*"])


@app.get("/send", tags=["angora"])
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


@app.get("/tasks/status", tags=["angora"])
async def get_tasks_status():
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

                if lt["time_stamp"] > time_stamp:
                    time_stamp = lt["time_stamp"]

                delta = relativedelta(datetime.utcnow(), time_stamp)

                last_run_time = "{} hr {} min {} sec".format(
                    delta.hours, delta.minutes, delta.seconds
                )

        task["status"] = status
        task["time_stamp"] = time_stamp
        task["last_run_time"] = last_run_time

    return {"data": all_tasks}


@app.get("/tasks/categories", tags=["angora"])
async def get_task_categories():
    """
    Return a list of categories, a pretty format of the config source or file
    name that task is saved.
    """
    categories = []

    for task in Tasks().tasks:
        category = task["config_source"]
        categories.append(category.rstrip('.yml').replace('_', ' ').upper())

    return {"data": sorted(set(format_category(task) for task in Tasks().tasks))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", dest="port", default=55555, type=int)
    pargs = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=pargs.port, debug=True)
