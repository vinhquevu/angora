#! /usr/bin/env python3
import os
import argparse
import subprocess

from listener import Queue
from db import db

def archive(payload, _):
    db.insert_message(**payload)

def start_server(args):
    callbacks = [archive]
    Queue("angora", "angora").listen(callbacks)

def start_client(args):
    queue_name = os.uname()[1]
    
    if args.host:
        queue_name = args.host

    callbacks = [archive]
    Queue(queue_name, queue_name).listen(callbacks)

def clear_replay(args):
    print("CLEAR REPLAY")
    print(args.subcommand)

def start_web(args: argparse.Namespace):
    print(f"Starting web {args.module}")
    cmd = [f"./web/{args.module}.py"]

    stdout = subprocess.STDOUT
    if args.background:
        print("Running in background")
        stdout = subprocess.DEVNULL
    try:
        p = subprocess.Popen(cmd, stdout=stdout)

        if not args.background:
            p.wait()
    except KeyboardInterrupt:
        p.terminate()

    
    def maintain_db(args):
        if args.subcommand == "init"
            db.initDB()
        


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Angora command line tool")
    subparsers = parser.add_subparsers(dest="cmd")
    subparsers.required = True

    server_subparser = subparsers.add_parser(
        "server", help="Start Angora server"
    )
    server_subparser.set_defaults(func=start_server)

    client_subparser = subparsers.add_parser("client", help="Start Angora client")
    client_subparser.add_argument("--host", help="Host name or IP of client")
    client_subparser.set_defaults(func=start_client)

    web_subparser = subparsers.add_parser("web", help="Start Angora web component")
    web_subparser.add_argument("module", help="Module name", choices=("api", "app"))
    web_subparser.add_argument("--port", type=int)
    web_subparser.add_argument("--reload", action="store_true")
    web_subparser.add_argument("--background", action="store_true")
    web_subparser.set_defaults(func=start_web)

    replay_subparser = subparsers.add_parser(
        "replay", help="Replay queue maintenance"
    )
    replay_subparser.add_argument("subcommand", help="Command", choices=("create", "clear"))
    replay_subparser.set_defaults(func=clear_replay)

    db_subparser = subparsers.add_parser("database", help="Database maintenance")
    db_subparser.add_argument("subcommnd", help="Command", choices=("init",))
    db_subparser.set_defaults(func=maintain_db)

    args = parser.parse_args()
    args.func(args)


