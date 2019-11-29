# Angora
```
(\(\
(-.-)
o_(")(")
```
Angora is a job execution system based on message queues.  There is no coding required to use Angora.  The jobs or tasks are Linux system commands executed via Python's subprocess module.  Jobs are configured in YAML files.  Jobs are assigned to messages and when one of those matching messages is read from a job queue, the job will execute.  Each job has the option to send additional messages on success.  Those messages and their corresponding jobs are how workflows are built.  You can interact with the Angora system via a web API and the user interface is a web application.

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

## User Interface

## Configuring Jobs

### Config File

### Workflows

### Schedules


## TODO
1. don't initialize Tasks every time, it's costly
2. index tasks by name for faster lookup
3. index tasks by trigger for faster lookup
4. Optimize graph drawing
5. Change app.route to post?
6. Convert to Quart
7. Distributed operation
