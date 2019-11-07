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
        queue_name,
        routing_key,
        queue_args=None,
        user="guest",
        password="guest",
        host="localhost",
        port=5672,
        exchange_name="angora",
        exchange_type="direct",
    ):
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.queue_args = queue_args
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type

        self.__exchange = kombu.Exchange(
            self.exchange_name, type=self.exchange_type
        )
        self.__queue = kombu.Queue(
            self.queue_name,
            self.__exchange,
            self.routing_key,
            queue_arguments=queue_args
        )
        self.__connection_str = "amqp://{}:{}@{}:{}//".format(
            self.user, self.password, self.host, self.port
        )

    def listen(self, callbacks=None):
        with kombu.Connection(self.__connection_str) as conn:
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
        with kombu.Connection(self.__connection_str) as conn:
            with kombu.Consumer(conn, [self.__queue], no_ack=True):
                try:
                    conn.drain_events(timeout=2)
                except (socket.timeout, NotImplementedError):
                    print("\nQueue has been drained\n")
