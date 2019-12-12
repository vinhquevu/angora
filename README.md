# Angora
```
(\(\
(-.-)
o_(")(")
```
Angora is a job execution system based on message queues.  There is no coding required to use Angora, although everyone is encouraged to change anything to make it their own.  The jobs, a.k.a. tasks, are Linux system commands executed via Python's subprocess module.  Jobs are configured in YAML files.  Jobs are assigned to messages and when one of those matching messages is read from a job queue, the job will execute.  Each job has the option to send additional messages on success.  Those messages and their corresponding jobs are how workflows are built.  You can interact with the Angora system via a web API and the user interface is a web application.

## Installation

### Libraries
The following libraries are required.
- Celery
- PyYaml

### Erlang

### RabbitMQ

## Start
### RabbitMQ
cd /usr/local/opt/rabbitmq/sbin
./rabbitmq-server -detached
sudo ./rabbitmqctl stop 
### Celery

### Server

### Client

## Jobs
A job is just any command you can run on the command line.  It can be as simple as `echo "hello world"` or something more complicated.  Most likely you'll be running some script, `job.sh` or `job.py`.  Angora does not interact with the job at all, it just executes it and reads the return code.  A return code of zero will be interpreted as success and anything will be interpreted as failure.

### Config File
Example:
```
-   name: example_job
    triggers:
        -   shell.print.env
    command: "env"
    log: "$HOME/angora/logs/"
    messages:
        -   shell.print.message.test
```
#### name
`name` is any arbitrary string.  The example is in snake case but that's not a requirement.  The only requirement is that the name is unique.

#### triggers
One or more strings that will cause this job to execute.  You must have at least one trigger.

#### commmand

#### log

#### messages

#### replay

#### parent_success

### Workflows

### Schedules

## User Interface

## TODO
1. don't initialize Tasks every time, it's costly
2. index tasks by name for faster lookup
3. index tasks by trigger for faster lookup
4. Optimize graph drawing
5. Change app.route to post?
6. Convert to Quart
7. Distributed operation
