#! /usr/bin/env python3

# import sys
import uvicorn

from collections import OrderedDict
from datetime import datetime, date

import asks
# from jinja2 import Environment, PackageLoader
# from wtforms.form import Form
# from wtforms.fields.html5 import DateField
from starlette.responses import PlainTextResponse
from starlette.templating import Jinja2Templates
from starlette.applications import Starlette

from angora.db import db

API = "localhost:55550"
templates = Jinja2Templates(directory="templates")
app = Starlette()


# def _addLastestStatus():
#     """
#     Found myself repeating this logic so moved it a protected function.
#     """
#     from angora.task import Tasks
#     from datetime import datetime
#     from dateutil.tz import gettz
#     from dateutil.parser import parse
#     from dateutil.relativedelta import relativedelta

#     tasks = []
#     all_tasks = Tasks()
#     # I could call this function for each task but that would be multiple
#     # calls to the database
#     last_task = db.get_tasks_today()

#     for task in all_tasks.tasks:
#         status = None
#         time_stamp = None
#         last_run_time = "Never"

#         for lt in last_task:
#             if lt['name'] == task['name']:
#                 status = lt['status']
#                 time_stamp = lt['time_stamp']

#                 delta = relativedelta(
#                     datetime.utcnow(),
#                     time_stamp,
#                 )

#                 last_run_time = "{} hr {} min {} sec".format(
#                     delta.hours, delta.minutes, delta.seconds
#                 )

#                 break

#         task["status"] = status
#         task["time_stamp"] = time_stamp
#         task["last_run_time"] = last_run_time

#         tasks.append(task)

#     return tasks


@app.route("/")
async def index(request):
    context = {"request": request}

    return templates.TemplateResponse("index.html", context)


@app.route("/tasks", methods=["POST"])
async def tasks(request):
    url = f"http://{API}/tasks/lastruntime/sorted/category"
    response = await asks.get(url)
    response.raise_for_status()
    
    context = {
        "request": request, "data": response.json()["data"]
    }

    return templates.TemplateResponse("tasks.html", context)


@app.route("/schedule", methods=["POST"])
async def schedule(request):
    url = f"http://{API}/tasks/scheduled"
    response = await asks.get(url)
    response.raise_for_status()
    scheduled_tasks = response.json()["data"]

    url = f"http://{API}/tasks/repeating"
    response = await asks.get(url)
    response.raise_for_status()
    repeating_tasks = response.json()["data"]

    context = {
        "request": request,
        "scheduled_tasks": OrderedDict(sorted(scheduled_tasks.items())),
        "repeating_tasks": OrderedDict(sorted(repeating_tasks.items()))
    }

    return templates.TemplateResponse(
        "schedule.html", context
    )


@app.route("/history", methods=["POST"])
async def history(request):
    form = await request.form()
    params = dict(form)
    params["run_date"] = date.today().strftime("%Y-%m-%d")

    url = f"http://{API}/tasks/history"
    response = await asks.get(url, params=params)
    response.raise_for_status()
    history = response.json()["data"]

    context = {"request": request, "history": history}

    return templates.TemplateResponse("history.html", context)


@app.route("/log")
def history(request):
    return PlainTextResponse("TODO")


@app.route("/workflow")
def history(request):
    return PlainTextResponse("TODO")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", dest="port", default=55551, type=int)
    pargs = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=pargs.port, debug=True)
