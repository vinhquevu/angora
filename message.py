"""
Angora Message
"""
from typing import Dict, Optional, Union
from kombu import Connection, Producer


class Message(dict):
    """
    Message protocol, basically a modified python dictionary.  Inherit dict to make it JSON serializable.
    """

    __keys = ("exchange", "queue", "message", "time_stamp", "data")

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
        :type time_stamp: datetime
        :param data: Any serializable object
        :type data: object
        """

        self["exchange"] = exchange
        self["queue"] = queue
        self["message"] = message
        self["time_stamp"] = time_stamp
        self["data"] = data

        super().__init__()

    def __setitem__(self, key: str, value: Union[str, Dict]) -> None:
        if key in self.__keys:
            super().__setitem__(key, value)
        else:
            raise KeyError("{} is not a valid key".format(key))

    def send(self, user, password, host, port, routing_key) -> None:
        connection_str = "amqp://{}:{}@{}:{}//".format(user, password, host, port)

        with Connection(connection_str) as conn:
            producer = Producer(conn)
            producer.publish(self, exchange=self["exchange"], routing_key=routing_key)
