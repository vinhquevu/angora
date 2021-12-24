#! /usr/bin/env python3
"""
Main Angora entry point.  Start each component of Angora from here.
"""
import os
import argparse
import logging
from typing import Dict
from functools import partial

import kombu

from celery import Celery

from task import Task, Tasks
from message import Message
from listener import Queue
from db import db

from angora import (
    EXCHANGE,
    USER,
    PASSWORD,
    HOST,
    PORT,
    CONFIGS,
)

TASKS = Tasks(CONFIGS)
log = logging.getLogger("")

##########
# Celery #
# ########
# Name has to be the same as the module that contains the task.  In this case
# it's "main"
app = Celery("main", inlcude="main")
app.conf.update(accept_content=["application/json"], task_serializer="json")


@app.task()
def run(payload: Dict) -> int:
    """
    Run

    This is the sole Celery task.  Typically, Celery applications run different
    Python functions and are identified by Celery with the @app.task decorator.
    Angora has just one Celery task, but what we run is a shell command which
    is executed via subprocess.
    """
    trigger = payload["message"]
    task = Task(**payload["data"])
    print(f"RUN: {task}")
    log.info(f"RUN: {task}")

    if payload["queue"] == "replay":
        status = payload["queue"]
    else:
        status = "start"

    insert_task = partial(
        db.insert_task,
        task["name"],
        trigger,
        task["command"],
        str(task["parameters"]),
        task["log"],
    )

    # Archive the task
    insert_task(status=status)

    # Parent Success
    if task["parent_success"]:
        for parent in task["parents"]:
            try:
                status = db.get_tasks_latest(parent)[0].get("status")
            except IndexError:
                status = "fail"
            finally:
                if status != "success":
                    # Insert fail message, no replay regardless of setting
                    insert_task(status="fail")

                    task.log("PARENT SUCCESS CHECK FAILED")

                    return 1

    retval = task.run()

    # Success
    if retval == 0:
        insert_task(status="success")

        # task["messages"] can be None or not set at all
        for message in task.get("messages", []) or []:
            Message(EXCHANGE, "angora", message, data=task["parameters"]).send(
                USER, PASSWORD, HOST, PORT, "angora"
            )

    # Failure
    else:
        insert_task(status="fail")

        # Replay
        # If replay is None (infinite)
        # if replay is greater than zero
        if task["replay"] is None:
            Message(EXCHANGE, "replay", trigger, data=task).send(
                USER, PASSWORD, HOST, PORT, "replay"
            )
        elif task["replay"] > 0:
            Message(EXCHANGE, "replay", trigger, data=task).send(
                USER, PASSWORD, HOST, PORT, "replay"
            )
            task["replay"] -= 1

    return retval


def archive(payload: Dict, _: kombu.Message) -> None:
    print(f"ARCHIVE: {payload}")
    log.info(f"ARCHIVE: {payload}")
    db.insert_message(**payload)


def parse_task(payload: Dict, _: kombu.Message) -> None:
    print(f"PARSE TASK: {payload}")
    log.info(f"PARSE TASK: {payload}")
    task_queue_name = os.uname()[1]
    tasks = TASKS.get_tasks_by_trigger(payload["message"])

    for task in tasks:
        task["parameters"] = payload["data"]
        print(task)
        Message(EXCHANGE, task_queue_name, payload["message"], data=task).send(
            USER, PASSWORD, HOST, PORT, task_queue_name
        )


def maintain_db(args: argparse.Namespace) -> None:
    """
    Initialize the database with Messages and Tasks tables.  Just calls
    init_db() from the db module.
    """
    db.init_db()


def start_server(args: argparse.Namespace) -> None:
    """
    Start the Angora server.  It's a RabbitMQ queue named "angora".  There are
    two callbacks, archive(), and parse_task().
    """
    callbacks = [archive, parse_task]
    Queue("angora", "angora").listen(callbacks)


def start_client(args: argparse.Namespace) -> None:
    """
    Start an Angora task client.  It's a RabbitMQ queue.  The default name is
    the name of the local host.  There are two callbacks, archive() and a lambda
    function that calls run.delay().  The delay() executes run() as a Celery
    task.
    """
    callbacks = [archive, lambda x, y: run.delay(x)]
    Queue(args.queue_name, args.queue_name).listen(callbacks)


def clear_replay(args: argparse.Namespace) -> None:
    """
    Start the Replay queue.  The Replay queue is a RabbitMQ dead letter queue.
    After a set amount of time, messages in the Replay queue are released to a
    designated client task queue.  Creating the Replay queue is the same as
    clearing it, if the queue doesn't exist when the clear() method runs then
    the queue is created.
    """
    queue_args = {
        "x-message-ttl": args.ttl,
        "x-dead-letter-exchange": EXCHANGE,
        "x-dead-letter-routing-key": args.routing_key,
    }
    Queue("replay", "replay", queue_args=queue_args).clear()


def start_celery(args: argparse.Namespace) -> None:
    import logging

    _worker = app.Worker()
    _worker.setup_defaults(
        concurrency=args.concurrency,
        loglevel=logging.getLevelName(args.loglevel),
        logfile=args.logfile,
        optimization="fair",
    )
    _worker.start()


def start_web(args: argparse.Namespace) -> None:
    import uvicorn

    print(f"Starting web {args.module}")

    # Pass the app as a string so you can use the reload argument
    uvicorn.run(
        f"web.{args.module}:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Angora command line tool")
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    server_subparser = subparsers.add_parser("server", help="Start Angora server")
    server_subparser.set_defaults(func=start_server)

    client_subparser = subparsers.add_parser("client", help="Start Angora client")
    client_subparser.add_argument(
        "--queue-name",
        help="Name of the client queue, default is the name of the local host",
        default=os.uname()[1],
    )
    client_subparser.set_defaults(func=start_client)

    replay_subparser = subparsers.add_parser("replay", help="Create/Clear replay queue")
    replay_subparser.add_argument(
        "--routing-key",
        help="Name of queue that replay queue will release messages to, default is local host name",
        default=os.uname()[1],
    )
    replay_subparser.add_argument(
        "--ttl",
        type=int,
        help="Queue lifetime in milliseconds, default is 10 minutes",
        default=600000,
    )
    replay_subparser.set_defaults(func=clear_replay)

    db_subparser = subparsers.add_parser("initdb", help="Database maintenance")
    db_subparser.set_defaults(func=maintain_db)

    celery_subparser = subparsers.add_parser("celery", help="Start Celery worker")
    celery_subparser.add_argument("--concurrency", type=int, default=8)
    celery_subparser.add_argument(
        "--loglevel", choices=("INFO", "WARN", "DEBUG"), default="INFO"
    )
    celery_subparser.add_argument("--logfile", default="./logs/celery.log")
    celery_subparser.set_defaults(func=start_celery)

    web_subparser = subparsers.add_parser("web", help="Start Angora web component")
    web_subparser.add_argument("module", help="Module name", choices=("api", "app"))
    web_subparser.add_argument("--host", default="0.0.0.0")
    web_subparser.add_argument("--port", type=int, default=55550)
    web_subparser.add_argument("--reload", action="store_true")
    web_subparser.set_defaults(func=start_web)

    args = parser.parse_args()
    args.func(args)
