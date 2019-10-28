#! /usr/bin/env python3

from angora import EXCHANGE
from angora.listener import Queue


def main():
    queue_args = {
        "x-message-ttl": 600000,  # 10 minutes
        # "x-message-ttl": 60000, # 1 minute debug
        "x-dead-letter-exchange": EXCHANGE,
        "x-dead-letter-routing-key": "start",
    }

    Queue("replay", "replay", queueArgs=queue_args).clear()


if __name__ == "__main__":
    main()
