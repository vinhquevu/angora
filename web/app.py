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


@app.route("/")
async def index(request):
    context = {"request": request}

    return templates.TemplateResponse("index.html", context)


@app.route("/dashboard", methods=["POST"])
async def load_dashboard_view(request):
    url = f"http://{API}/tasks/today"

    params={"status": "start"}
    response = await asks.get(url, params=params)
    response.raise_for_status()
    executed = response.json()["data"]

    params={"status": "success"}
    response = await asks.get(url, params=params)
    response.raise_for_status()
    successful = response.json()["data"]

    params={"status": "fail"}
    response = await asks.get(url, params=params)
    response.raise_for_status()
    failed = response.json()["data"]

    params={"status": "replay"}
    response = await asks.get(url, params=params)
    response.raise_for_status()
    replayed = response.json()["data"]

    url = f"http://{API}/tasks/today/notrun"
    response = await asks.get(url)
    response.raise_for_status()
    notrun = response.json()["data"]

    context = {
        "request": request,
        "executed": len(executed),
        "successful": len(successful),
        "failed": len(failed),
        "replayed": len(replayed),
        "notrun": len(notrun),
    }
    
    return templates.TemplateResponse("dashboard.html", context)


@app.route("/tasks", methods=["POST"])
async def load_tasks_view(request):
    url = f"http://{API}/tasks/lastruntime/sorted/category"
    response = await asks.get(url)
    response.raise_for_status()
    
    context = {
        "request": request, "data": response.json()["data"]
    }

    return templates.TemplateResponse("tasks.html", context)


@app.route("/task", methods=["POST"])
async def load_task_detail(request):
    params = await request.form()
    url = f"http://{API}/tasks/lastruntime"
    response = await asks.get(url, params=params)
    response.raise_for_status()
    
    context = {
        "request": request, "task": response.json()["data"][0]
    }

    return templates.TemplateResponse("task.html", context)

@app.route("/schedule", methods=["POST"])
async def load_schedule_view(request):
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


@app.route("/log", methods=["POST"])
async def log(request):
    params = await request.form()
    url = f"http://{API}/tasks/log"
    response = await asks.get(url, params=params)
    response.raise_for_status()
    log = response.json()["data"]

    context = {"request": request, "log": log}

    return templates.TemplateResponse("log.html", context)    


@app.route("/workflow", methods=["POST"])
async def workflow(request):
    params = await request.form()
    url = f"http://{API}/tasks/children"
    response = await asks.get(url, params=params)
    response.raise_for_status()
    children = response.json()["data"]

    context = {"request": request, "children": children}

    return templates.TemplateResponse('workflow.html', context)


@app.route("/execute/params", methods=["POST"])
async def get_task_params(request):
    params = await request.form()
    url = f"http://{API}/tasks"
    response = await asks.get(url, params=params)
    response.raise_for_status()
    
    context = {
        "request": request, "task": response.json()["data"][0]
    }

    return templates.TemplateResponse("execute.html", context)


@app.route("/execute/send", methods=["POST"])
async def send_task_message(request):
    form = await request.form()
    params = {
        "message": form["trigger"],
        "queue": "initialize",
        "routing_key": "initialize",
    }

    if form["parameters"]:
        temp_str = form["parameters"]
        
        for _ in ("=", "\n", "\n\r"):
            temp_str = temp_str.replace(_, " ")

        params["params"] = temp_str.split(" ")

    url = f"http://{API}/send"
    response = await asks.get(url, params=params)
    response.raise_for_status()
    
    return PlainTextResponse(response.json()["data"])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", dest="port", default=55551, type=int)
    pargs = parser.parse_args()

    uvicorn.run(app, host="0.0.0.0", port=pargs.port, debug=True)
