#! /usr/bin/env python3

from angora import EXCHANGE, USER, PASSWORD, HOST, PORT
from angora.db import db
from angora.task import Tasks
from angora.message import Message
from angora.listener import Queue


_tasks = Tasks()


def parse_task(payload, _):
    # if payload["message"] == "management_reload_tasks":
    #     _tasks.reload()
    #     return

    tasks = _tasks.get_tasks_by_trigger(payload["message"])

    for task in tasks:
        task["parameters"] = payload["data"]
        msg = Message(EXCHANGE, "start", payload["message"], data=task)
        msg.send(USER, PASSWORD, HOST, PORT, "start")


def archive(payload, _):
    db.insert_message(**payload)


def main():
    callbacks = [archive, parse_task]
    Queue("initialize", "initialize").listen(callbacks)


if __name__ == "__main__":
    main()
