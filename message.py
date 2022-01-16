"""
Angora Message
"""
from typing import Dict, Optional, Union

from kombu import Connection, Producer  # type: ignore


class Message:
    """
    Message object
    """

    __slots__ = (
        "exchange",
        "queue",
        "message",
        "time_stamp",
        "data",
    )

    def __init__(
        self,
        exchange: str,
        queue: str,
        message: str,
        time_stamp: Optional[str] = None,
        data: Optional[Dict] = None,
    ) -> None:
        """
        :param exchange: The RabbitMQ exchange
        :type msg: str
        :param queue: The RabbitMQ queue
        :type msg: str
        :param message: A string message, format is up to the user
        :type msg: str
        :param time_stamp: A time stamp
        :type time_stamp: str
        :param data: Any serializable object
        :type data: object
        """

        self.exchange = exchange
        self.queue = queue
        self.message = message
        self.time_stamp = time_stamp
        self.data = data

    def send(
        self,
        user: str,
        password: str,
        host: str,
        port: Union[str, int],
        routing_key: str,
    ) -> None:
        """
        Send the message to ampq message queue.  The body passed to publish()
        must be JSON serializable (which a dictionary is).
        """
        msg = {
            "exchange": self.exchange,
            "queue": self.queue,
            "message": self.message,
            "time_stamp": self.time_stamp,
            "data": self.data,
        }

        connection_str = f"amqp://{user}:{password}@{host}:{port}//"

        with Connection(connection_str) as conn:
            producer = Producer(conn)
            producer.publish(msg, exchange=self.exchange, routing_key=routing_key)
