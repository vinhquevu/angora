from kombu import Connection, Producer


class Message(dict):
    """
    Message protocol, basically a modified python dictionary.
    """

    __keys = ("exchange", "queue", "message", "time_stamp", "data")

    def __init__(self, exchange, queue, message, time_stamp=None, data=None):
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

        # for key, value in self.items():
        #     setattr(self, key, value)

        super().__init__()

    # def __setattr__(self, key, value):
    #     if key in self.__keys:
    #         super(Message, self).__setattr__(key, value)
    #         super(Message, self).__setitem__(key, value)
    #     else:
    #         raise KeyError("{} is not a valid key".format(key))

    def __setitem__(self, key, value):
        if key in self.__keys:
            super().__setitem__(key, value)
        else:
            raise KeyError("{} is not a valid key".format(key))

    def send(self, user, password, host, port, routing_key):
        connection_str = "amqp://{}:{}@{}:{}//".format(user, password, host, port)

        with Connection(connection_str) as conn:
            producer = Producer(conn)
            producer.publish(self, exchange=self["exchange"], routing_key=routing_key)
