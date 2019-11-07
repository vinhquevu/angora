#! /usr/bin/env python3
# TODO: Send a message to a queue instead of using a insert_task directly to
# work in a distributed mode better

from celery import Celery

from angora import EXCHANGE, USER, PASSWORD, HOST, PORT
from angora.task import Task
from angora.db.db import insert_task, insert_message
from angora.message import Message
from angora.listener import Queue


# Celery name has to be the same as the module that contains the task.  In
# this case it's "start"
app = Celery(
    "start", broker="amqp://", backend="amqp://", include="angora.listeners.start"
)
app.conf.update(
    CELERY_ACCEPT_CONTENT=["application/json"], CELERY_TASK_SERIALIZER="json"
)


@app.task()
def run(payload):
    trigger = payload["message"]
    status = payload["queue"]
    task = Task(**payload["data"])

    # Archive the task
    insert_task(
        task["name"],
        trigger,
        task["command"],
        str(task["parameters"]),
        task["log"],
        status=status,
    )

    retval = task.run()

    # Success
    if retval == 0:
        insert_task(
            task["name"],
            trigger,
            task["command"],
            str(task["parameters"]),
            task["log"],
            status="success",
        )

        for message in task.get("messages", []):
            Message(EXCHANGE, "initialize", message, data=task["parameters"]).send(
                USER, PASSWORD, HOST, PORT, "initialize"
            )

    # Failure
    else:
        insert_task(
            task["name"],
            trigger,
            task["command"],
            str(task["parameters"]),
            task["log"],
            status="fail",
        )

        # Replay
        # If replay is None (infinite)
        # if replay is greater than zero
        if task["replay"] is None:
            print("INF")
            Message(EXCHANGE, "replay", trigger, data=task).send(
                USER, PASSWORD, HOST, PORT, "replay"
            )
        elif task["replay"] > 0:
            print("REG")
            Message(EXCHANGE, "replay", trigger, data=task).send(
                USER, PASSWORD, HOST, PORT, "replay"
            )
            task["replay"] -= 1
        print("DONE")

    return retval


def archive(payload, _):
    insert_message(**payload)


def main():
    callbacks = [archive, lambda x, y: run.delay(x)]
    Queue("start", "start").listen(callbacks)


if __name__ == "__main__":
    main()
