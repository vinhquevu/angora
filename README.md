# Angora

```
(\(\
(-.-)
o_(")(")
```
## Introduction

## Installation
--

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


## TODO
1. don't initialize Tasks every time, it's costly
2. index tasks by name for faster lookup
3. index tasks by trigger for faster lookup
4. Optimize graph drawing
5. Change app.route to post?
6. Convert to Quart
