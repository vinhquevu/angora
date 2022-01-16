"""
Angora Queue
"""
import logging
import socket
from typing import Dict, Optional

import kombu  # type: ignore

log = logging.getLogger(__name__)


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
        queue_name: str,
        routing_key: str,
        queue_args: Optional[Dict] = None,
        user: str = "guest",
        password: str = "guest",
        host: str = "localhost",
        port: int = 5672,
        exchange_name: str = "angora",
        exchange_type: str = "direct",
    ) -> None:
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
    def queue(self) -> kombu.Queue:
        return kombu.Queue(
            self.queue_name,
            kombu.Exchange(self.exchange_name, type=self.exchange_type),
            self.routing_key,
            queue_arguments=self.queue_args,
        )

    @property
    def connection_str(self) -> str:
        return "amqp://{}:{}@{}:{}//".format(
            self.user, self.password, self.host, self.port
        )

    def listen(self, callbacks: Optional[list] = None) -> None:
        """
        Start a listener and handle messeages with the callback(s).  If the
        queue does not already exist in the exchange, it will be created.
        """
        log.info("Staring listener")
        log.info("Exchange: %s", self.queue.exchange.name)
        log.info("Queue: %s", self.queue.name)
        with kombu.Connection(self.connection_str) as conn:
            with kombu.Consumer(conn, [self.queue], callbacks=callbacks, no_ack=True):
                try:
                    for _ in kombu.eventloop(conn):
                        pass
                except KeyboardInterrupt:
                    log.info("Exiting")

    def clear(self) -> None:
        """
        Clear a queue of messages.  If the queue does not exist in the exchange,
        it will be created.  If the queue doesn't exist, this is the same as
        creating an empty queue with no listener.
        """
        log.info("Clearing queue")
        log.info("Exchange: %s", self.queue.exchange.name)
        log.info("Queue: %s", self.queue.name)

        with kombu.Connection(self.connection_str) as conn:
            with kombu.Consumer(conn, [self.queue], no_ack=True):
                try:
                    conn.drain_events(timeout=2)
                except (socket.timeout, NotImplementedError):
                    log.info("Complete")
