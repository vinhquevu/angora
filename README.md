# Angora
```
(\(\
(-.-)
o_(")(")
```
Angora is a job execution system based on message queues.  There is no coding required to use Angora, although everyone is encouraged to change anything to make it their own.  The jobs, a.k.a. tasks, are Linux system commands executed via Python's subprocess module, i.e. `echo 'Hello World'`.  Jobs are configured in YAML files.  Jobs are assigned to messages and when one of those matching messages is read from a job queue, the job will execute.  Each job has the option to send additional messages on success.  Those messages and their corresponding jobs are how workflows are built.  You can interact with the Angora system via a web API and the user interface is a web application.

## Installation

### Erlang
You'll need to install [Erlang](https://www.erlang.org/).  Follow the instructions for your system.  Or visit the Erlang site for more details.  

For Homebrew on OS X: `brew install erlang`  
For MacPorts on OS X: `port install erlang`  
For Ubuntu and Debian: `apt-get install erlang`  
For Fedora: `yum install erlang`  
For FreeBSD: `pkg install erlang`  

### RabbitMQ
[RabbitMQ](https://www.rabbitmq.com/) is a message broker.  Angora will work with any AMPQ message broker but it's only been tested with RabbitMQ.  Checkout the RabbitMQ download and installation [instructions](https://www.rabbitmq.com/download.html) for details about your specfic environment.

### Python Libraries
The following libraries are required.
- Celery, `pip install celery`
- PyYaml, `pip install pyyaml`

## Starting Angora
### RabbitMQ
Depending on your local installation, your steps may differ but here are the basics:
    cd /usr/local/opt/rabbitmq/sbin
    ./rabbitmq-server -detached

You can stop RabbitMQ anytime with the command: `sudo ./rabbitmqctl stop`

### Celery

### Server

### Client

## Jobs
A job is just any command you can run on the command line.  It can be as simple as `echo "hello world"` or something more complicated.  Most likely you'll be running some script, `job.sh` or `job.py`.  Angora does not interact with the job at all, it just executes it and reads the return code or exit status.  A return code of zero will be interpreted as success and anything will be interpreted as failure.  The return code being read is equivalent to `echo $?`.

### Configuration File
Configuration files should be where you're spending most of your time.  All configuration files must be saved in the `tasks/` directory and end with a `.yml` extension.  Angora will parse any file meeting that criteria on startup.

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
A valid command line statement.  What's valid will differ based the environment.  Note, Angora uses `subprocess.Popen()` to execute the given command with `shell=False`.  Using `shell=True` is typically frowned upon for security reasons, but can complicate the expected behavior of a command.  If the security is not a concern then feel free to change this setting in the code itself.  Environment variables will be expanded.

#### log
This is the optional location of the log file.  The log file is simply the captured stdout of the command.  The name of the log file will always be the name of the command.  Environment variables will be expanded.

#### messages
Identical to triggers, these are the messages that the job will transmit when complete.  The idea is of course to use a message that will trigger another job.  This is how workflows are built.  One or more messages is valid and the tag is optional.

#### replay
An opt

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
8. Replace spaces with underscores for log file
