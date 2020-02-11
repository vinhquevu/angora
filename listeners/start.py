#! /usr/bin/env python3
# TODO: Send a message to a queue instead of using a insert_task directly to
# work in a distributed mode better

from celery import Celery

from angora import EXCHANGE, USER, PASSWORD, HOST, PORT
from angora.task import Task
from angora.db.db import insert_task, insert_message, get_tasks_latest
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

    # Parent Success
    if task["parent_success"]:
        for parent in task["parents"]:
            try:
                status = get_tasks_latest(parent)[0].get("status")
            except IndexError:
                status = "fail"
            finally:
                if status != "success":
                    # Insert fail message, no replay regardless of setting
                    insert_task(
                        task["name"],
                        trigger,
                        task["command"],
                        str(task["parameters"]),
                        task["log"],
                        status="fail",
                    )

                    task.log("PARENT SUCCESS CHECK FAILED")
                    
                    return 1

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

        # task["messages"] can be None or not set at all
        for message in task.get("messages", []) or []:
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

    return retval


def archive(payload, _):
    insert_message(**payload)


def main():
    callbacks = [archive, lambda x, y: run.delay(x)]
    Queue("start", "start").listen(callbacks)


if __name__ == "__main__":
    main()
