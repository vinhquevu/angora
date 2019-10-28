import kombu
import socket


class Queue:
    """
    An object representing a queue in RabbitMQ.

    A listener can listen to one or more queues and have one or more
    callbacks.  Consumer expects a sequence of queues.  Angora is designed to
    only have one listener per queue.  A kombu.Queue object is passed as a
    list to kombu.Consumer for this reason.

    Once you create a Queue object, you can do two things: start up the
    listener or clear the queue.
    """

    def __init__(
        self,
        queueName,
        routingKey,
        queueArgs=None,
        user="guest",
        password="guest",
        host="localhost",
        port=5672,
        exchangeName="angora",
        exchangeType="direct",
    ):
        self.queueName = queueName
        self.routingKey = routingKey
        self.queueArgs = queueArgs
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.exchangeName = exchangeName
        self.exchangeType = exchangeType

        self.__exchange = kombu.Exchange(
            self.exchangeName, type=self.exchangeType
        )
        self.__queue = kombu.Queue(
            self.queueName,
            self.__exchange,
            self.routingKey,
            queue_arguments=queueArgs
        )
        self.__connectionStr = "amqp://{}:{}@{}:{}//".format(
            self.user, self.password, self.host, self.port
        )

    def listen(self, callbacks=None):
        with kombu.Connection(self.__connectionStr) as conn:
            with kombu.Consumer(
                conn, [self.__queue], callbacks=callbacks, no_ack=True
            ):
                try:
                    print("STARING LISTENER")
                    for _ in kombu.eventloop(conn):
                        pass
                except KeyboardInterrupt:
                    print("\nExiting\n")

    def clear(self):
        with kombu.Connection(self.__connectionStr) as conn:
            with kombu.Consumer(conn, [self.__queue], no_ack=True):
                try:
                    conn.drain_events(timeout=2)
                except socket.timeout:
                    print("\nQueue has been drained\n")
