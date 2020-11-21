"""
Angora Database
"""
import os
import sqlite3
from typing import Optional, Union, Generator, Dict, List
from datetime import datetime, date
from sqlalchemy import (
    Column,
    # Table,
    Integer,
    Text,
    DateTime,
    create_engine,
    # MetaData,
)

from contextlib import contextmanager
from sqlalchemy import cast, Date
from sqlalchemy.sql import func, and_
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


_database = os.path.join(os.path.dirname(__file__), "log.db")
_base = declarative_base()


@contextmanager
def _session() -> Generator:
    engine = create_engine("sqlite:///{}".format(_database))
    session = scoped_session(sessionmaker(autocommit=True, autoflush=True, bind=engine))
    yield session
    session.close()


class Messages(_base):
    __tablename__ = "messages"
    message_id = Column("id", Integer, primary_key=True)
    exchange = Column("exchange", Text)
    queue = Column("queue", Text)
    message = Column("message", Text)
    data = Column("data", Text)
    time_stamp = Column(
        "time_stamp",
        DateTime(),
        default=datetime.now,
        index=True,
        nullable=False,
    )


class Tasks(_base):
    __tablename__ = "tasks"
    task_id = Column("id", Integer, primary_key=True)
    name = Column("name", Text)
    trigger = Column("trigger", Text)
    command = Column("command", Text)
    parameters = Column("parameters", Text)
    log = Column("log", Text)
    status = Column("status", Text)
    time_stamp = Column("time_stamp", DateTime(), default=datetime.now, index=True)


def init_db() -> None:
    engine = create_engine("sqlite:///{}".format(_database))

    if not engine.dialect.has_table(engine, "messages"):
        _base.metadata.tables["messages"].create(engine)

    if not engine.dialect.has_table(engine, "tasks"):
        _base.metadata.tables["tasks"].create(engine)


def insert_message(
    exchange: str,
    queue: str,
    message: str,
    data: Optional[Dict] = None,
    time_stamp: Optional[str] = None,
) -> None:
    values = {
        "exchange": exchange,
        "queue": queue,
        "message": message,
    }

    # Set Nullable values
    if data:
        values["data"] = str(data)

    if time_stamp:
        values["time_stamp"] = time_stamp

    with _session() as session:
        session.execute(Messages.__table__.insert(), values)


def get_messages_today() -> List:
    with _session() as session:
        result = session.query(Messages.__table__).filter(
            Messages.time_stamp >= date.today()
        )

    return [dict(zip(row.keys(), row)) for row in result]


def insert_task(
    name: str,
    trigger: str,
    command: str,
    parameters: str,
    log: str,
    status: str,
    time_stamp: Optional[str] = None,
) -> None:
    values = {
        "name": name,
        "trigger": trigger,
        "command": command,
        "parameters": parameters,
        "log": log,
        "status": status,
    }

    # Set Nullable values
    if time_stamp:
        values["time_stamp"] = time_stamp

    with _session() as session:
        session.execute(Tasks.__table__.insert(), values)


def get_tasks_today(status: Optional[str] = None) -> List:
    return get_tasks(status=status, start_datetime=date.today())


def get_tasks_latest(name: Optional[str] = None) -> List:
    filters = [Tasks.time_stamp >= date.today()]

    if name:
        filters.append(Tasks.name == name)

    with _session() as session:
        max_time = (
            session.query(Tasks.name, func.max(Tasks.time_stamp).label("time_stamp"))
            .filter(*filters)
            .group_by(Tasks.name)
            .cte()
        )

        query = (
            session.query(Tasks.__table__)
            .join(
                max_time,
                and_(
                    Tasks.name == max_time.c.name,
                    Tasks.time_stamp == max_time.c.time_stamp,
                ),
            )
            .filter(Tasks.time_stamp >= date.today())
        )

    return [dict(zip(row.keys(), row)) for row in query]


def get_tasks(
    run_date: Optional[str] = None,
    name: Optional[str] = None,
    trigger: Optional[str] = None,
    command: Optional[str] = None,
    parameters: Optional[str] = None,
    log: Optional[str] = None,
    status: Optional[str] = None,
    start_datetime: Union[datetime, date, None] = None,
    end_datetime: Union[datetime, date, None] = None,
) -> List:

    filters = []

    if run_date:
        filters.append(cast(Tasks.time_stamp, Text).startswith(run_date))
    if name:
        filters.append(Tasks.name == name)
    if trigger:
        filters.append(Tasks.trigger == trigger)
    if parameters:
        filters.append(Tasks.parameters == parameters)
    if log:
        filters.append(Tasks.log == log)
    if status:
        filters.append(Tasks.status == status)
    if start_datetime:
        filters.append(Tasks.time_stamp >= start_datetime)
    if end_datetime:
        filters.append(Tasks.time_stamp <= end_datetime)

    with _session() as session:
        query = (
            session.query(Tasks.__table__).filter(*filters).order_by(Tasks.time_stamp)
        )

    return [dict(zip(row.keys(), row)) for row in query]


# def clearDB():
#     with sqlite3.connect(_database) as conn:
#         conn.execute("DELETE FROM messages;")
#         conn.execute("DELETE FROM tasks;")


# def getMsgLog(
#     exchange=None,
#     queue=None,
#     message=None,
#     data=None,
#     time_stamp=None
# ):
#     return


# def getTaskLog(
#     name,
#     trigger,
#     command,
#     parameters,
#     log,
#     status,
#     time_stamp
# ):
#     return
