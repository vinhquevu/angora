#! /usr/bin/env python3

# import sys
import uvicorn

from collections import OrderedDict
# from datetime import datetime, timedelta

import asks
# from jinja2 import Environment, PackageLoader
# from wtforms.form import Form
# from wtforms.fields.html5 import DateField
from starlette.responses import PlainTextResponse
from starlette.templating import Jinja2Templates
from starlette.applications import Starlette

from angora.db import db

API = "localhost:55555"
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
    # url = f"http://{API}/tasks/status"
    # tasks = _addLastestStatus()

    # def category_format(x):
    #     """
    #     Format the category name. It's the file name in upper case and
    #     spaces instead of underscores
    #     """
    #     return x.rstrip('.yml').replace('_', ' ').upper()

    # The names of the files get set to config_source and that is used to set
    # the category.  On the Task View page all the tasks are organzied under
    # this category name.
    url = f"http://{API}/tasks/categories"
    response = await asks.get(url)
    response.raise_for_status()
    categories = response.json()["data"]
    
    url = f"http://{API}/tasks/status"
    response = await asks.get(url)
    response.raise_for_status()
    tasks = response.json()["data"]

    data = {}
    for task in tasks:
        data.get(task.category, []).append(task)


    # # Order the dict before returning
    context = {
        "request": request, "data": data
    }

    # import pprint
    # pprint.pprint(OrderedDict(sorted(categories.items())))

    return templates.TemplateResponse("tasks.html", context)


@app.route("/schedule", methods=["POST"])
async def schedule(request):
    import re
    tasks = _addLastestStatus()

    scheduled_tasks = {}
    pattern = re.compile(r'time.\d{4}')

    for task in tasks:
        for trigger in task["triggers"]:
            if pattern.match(trigger):
                time = "{}:{}".format(trigger[5:7], trigger[7:9])

                if time in scheduled_tasks:
                    scheduled_tasks[time].append(task)
                    break
                else:
                    scheduled_tasks[time] = [task]

    repeating_tasks = {}
    pattern = re.compile(r'time.interval.\d+')

    for task in tasks:
        for trigger in task["triggers"]:
            if pattern.match(trigger):
                interval = trigger.split(".")[-1]

                if interval in repeating_tasks:
                    repeating_tasks[interval].append(task)
                    break
                else:
                    repeating_tasks[interval] = [task]

    context = {
        "request": request,
        "scheduled_tasks": OrderedDict(sorted(scheduled_tasks.items())),
        "repeating_tasks": OrderedDict(sorted(repeating_tasks.items()))
    }

    return templates.TemplateResponse(
        'schedule.html', context
    )


@app.route("/history")
def history(request):
    return PlainTextResponse("TODO")


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
    parser.add_argument("--port", dest="port", default=55555, type=int)
    pargs = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=pargs.port, debug=True)
