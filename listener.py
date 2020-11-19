"""
Angora Queue
"""

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

    @property
    def queue(self):
        return kombu.Queue(
            self.queue_name,
            kombu.Exchange(self.exchange_name, type=self.exchange_type),
            self.routing_key,
            queue_arguments=self.queue_args,
        )

    @property
    def connection_str(self):
        return "amqp://{}:{}@{}:{}//".format(
            self.user, self.password, self.host, self.port
        )

    def listen(self, callbacks=None):
        """
        Start a listener and handle messeages with the callback(s).  If the
        queue does not already exist in the exchange, it will be created.
        """
        with kombu.Connection(self.connection_str) as conn:
            with kombu.Consumer(conn, [self.queue], callbacks=callbacks, no_ack=True):
                try:
                    print("STARTING LISTENER")
                    for _ in kombu.eventloop(conn):
                        pass
                except KeyboardInterrupt:
                    print("\nExiting\n")

    def clear(self):
        """
        Clear a queue of messages.  If the queue does not exist in the exchange,
        it will be created.  If the queue doesn't exist, this is the same as
        creating an empty queue with no listener.
        """
        with kombu.Connection(self.connection_str) as conn:
            with kombu.Consumer(conn, [self.queue], no_ack=True):
                try:
                    conn.drain_events(timeout=2)
                except (socket.timeout, NotImplementedError):
                    print("\nQueue has been drained\n")
