#! /usr/bin/env python3

import argparse
from collections import OrderedDict
from datetime import datetime, date

import uvicorn
import httpx

from starlette.responses import PlainTextResponse
from starlette.templating import Jinja2Templates
from starlette.applications import Starlette


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

    params = {"status": "start"}
    response = await httpx.get(url, params=params)
    response.raise_for_status()
    executed = response.json()["data"]

    params = {"status": "success"}
    response = await httpx.get(url, params=params)
    response.raise_for_status()
    successful = response.json()["data"]

    params = {"status": "fail"}
    response = await httpx.get(url, params=params)
    response.raise_for_status()
    failed = response.json()["data"]

    params = {"status": "replay"}
    response = await httpx.get(url, params=params)
    response.raise_for_status()
    replayed = response.json()["data"]

    url = f"http://{API}/tasks/today/notrun"
    response = await httpx.get(url)
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
    response = await httpx.get(url)
    response.raise_for_status()

    context = {"request": request, "data": response.json()["data"]}

    return templates.TemplateResponse("tasks.html", context)


@app.route("/task", methods=["POST"])
async def load_task_detail(request):
    params = await request.form()
    url = f"http://{API}/tasks/lastruntime"
    response = await httpx.get(url, params=params)
    response.raise_for_status()

    context = {"request": request, "task": response.json()["data"][0]}

    return templates.TemplateResponse("task.html", context)


@app.route("/schedule", methods=["POST"])
async def load_schedule_view(request):
    url = f"http://{API}/tasks/scheduled"
    response = await httpx.get(url)
    response.raise_for_status()
    scheduled_tasks = response.json()["data"]

    url = f"http://{API}/tasks/repeating"
    response = await httpx.get(url)
    response.raise_for_status()
    repeating_tasks = response.json()["data"]

    context = {
        "request": request,
        "scheduled_tasks": OrderedDict(sorted(scheduled_tasks.items())),
        "repeating_tasks": OrderedDict(sorted(repeating_tasks.items())),
    }

    return templates.TemplateResponse("schedule.html", context)


@app.route("/task/workflow", methods=["POST"])
async def load_workflow_view(request):
    params = await request.form()

    # Children
    url = f"http://{API}/task/children"
    response = await httpx.get(url, params=params)
    response.raise_for_status()
    children = response.json()["data"]

    # Parents
    url = f"http://{API}/task/parents"
    response = await httpx.get(url, params=params)
    response.raise_for_status()
    parents = response.json()["data"]

    # Task Details
    url = f"http://{API}/tasks/lastruntime"

    tasks = {}

    for task in set(list(children) + list(parents)):
        params = {"name": task}
        response = await httpx.get(url, params=params)
        response.raise_for_status()

        tasks[task] = templates.env.get_template("task.html").render(task=response.json()["data"][0])

    context = {"request": request, "children": children, "parents": parents, "task_name": params["name"], "tasks": tasks}

    return templates.TemplateResponse("workflow.html", context)


@app.route("/management", methods=["POST"])
async def load_management_view(request):
    context = {"request": request}
    return templates.TemplateResponse("management.html", context)


@app.route("/task/history", methods=["POST"])
async def get_history(request):
    form = await request.form()
    params = dict(form)
    params["run_date"] = date.today().strftime("%Y-%m-%d")

    url = f"http://{API}/task/history"
    response = await httpx.get(url, params=params)
    response.raise_for_status()
    history = response.json()["data"]

    context = {"request": request, "history": history}

    return templates.TemplateResponse("history.html", context)


@app.route("/task/log", methods=["POST"])
async def get_log(request):
    params = await request.form()
    url = f"http://{API}/task/log"
    response = await httpx.get(url, params=params)
    response.raise_for_status()
    log = response.json()["data"]

    context = {"request": request, "log": log}

    return templates.TemplateResponse("log.html", context)


@app.route("/task/execute/params", methods=["POST"])
async def get_task_params(request):
    params = await request.form()
    url = f"http://{API}/tasks"
    response = await httpx.get(url, params=params)
    response.raise_for_status()

    context = {"request": request, "task": response.json()["data"][0]}

    return templates.TemplateResponse("execute.html", context)


@app.route("/task/execute/send", methods=["POST"])
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
    response = await httpx.get(url, params=params)
    response.raise_for_status()

    return PlainTextResponse(response.json()["data"])


@app.route("/management/reload", methods=["POST"])
async def reload_tasks(request):
    url = f"http://{API}/tasks/reload"
    response = await httpx.get(url)
    response.raise_for_status()

    message = "Configuration files reloaded.  Any updates to tasks have been loaded."

    context = {"request": request, "message": message}

    return templates.TemplateResponse("basic_message_modal.html", context)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", dest="port", default=55551, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("app:app", host="0.0.0.0", port=args.port, reload=args.reload)
