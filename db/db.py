"""
Angora Database
"""
# pylint: disable=too-many-arguments,too-few-public-methods,no-member
import os
from typing import Optional, Generator, Dict, List, Union
from datetime import datetime, date
from contextlib import contextmanager
from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    create_engine,
    cast,
)
from sqlalchemy.sql import func, and_
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


DATABASE = os.path.join(os.path.dirname(__file__), "log.db")
ENGINE = create_engine("sqlite:///{}".format(DATABASE))
SESSION = scoped_session(sessionmaker(bind=ENGINE))
BASE = declarative_base()


@contextmanager
def _session() -> Generator:
    session = SESSION()

    try:
        yield session
        session.commit()
        session.flush()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class Messages(BASE):
    """
    Messages table
    """

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


class Tasks(BASE):
    """
    Tasks table
    """

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
    """
    Create database tables
    """
    if not ENGINE.dialect.has_table(ENGINE, "messages"):
        BASE.metadata.tables["messages"].create(ENGINE)

    if not ENGINE.dialect.has_table(ENGINE, "tasks"):
        BASE.metadata.tables["tasks"].create(ENGINE)


def insert_message(
    exchange: str,
    queue: str,
    message: str,
    data: Optional[Dict] = None,
    time_stamp: Optional[str] = None,
) -> None:
    """
    Insert message record into messages table
    """
    with _session() as session:
        session.add(
            Messages(
                exchange=exchange,
                queue=queue,
                message=message,
                data=data,
                time_stamp=time_stamp,
            )
        )


def get_messages_today() -> List:
    """
    Query messages inserted since the start of the current day.
    """
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
    """
    Insert task records into tasks table
    """
    with _session() as session:
        session.add(
            Tasks(
                name=name,
                trigger=trigger,
                command=command,
                parameters=parameters,
                log=log,
                status=status,
                time_stamp=time_stamp,
            )
        )


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
    """
    Query tasks
    """

    filters = []

    if run_date:
        filters.append(cast(Tasks.time_stamp, Text).startswith(run_date))
    if name:
        filters.append(Tasks.name == name)
    if trigger:
        filters.append(Tasks.trigger == trigger)
    if command:
        filters.append(Tasks.command == command)
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


def get_tasks_today(status: Optional[str] = None) -> List:
    """
    Query task records inserted since start of current day.
    """
    return get_tasks(status=status, start_datetime=date.today())


def get_tasks_latest(name: Optional[str] = None) -> List:
    """
    Query the lastest instance of each unique task since the start of the
    current day.
    """
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


# def clearDB():
#     with sqlite3.connect(DATABASE) as conn:
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
