from angora.listener import Queue


def main():
    callbacks = []
    queue = Queue("finish", "finish")
    queue.listen(callbacks)


if __name__ == "__main__":
    main()

