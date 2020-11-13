# Angora
```
(\(\
(-.-)
o_(")(")
```
Angora is a job execution system based on message queues.  There is no Python
coding required to use Angora, or at least very little, although everyone is
encouraged to make it their own. The jobs, a.k.a. tasks, are Linux system
commands executed via Python's subprocess module, i.e. `echo 'Hello World'`.
Jobs are configured in YAML files.  Jobs are assigned to messages and when one
of those matching messages is read from a job queue, the job will execute.  Each
job has the option to send additional messages on success.  Those messages and
their corresponding jobs are how workflows are built.  You can interact with the
Angora system via a web API and the user interface is a web application.

## Installation
### Erlang
You'll need to install [Erlang](https://www.erlang.org/).  Follow the
instructions for your system or visit the Erlang site for more details.

For Homebrew on OS X: `brew install erlang`  
For MacPorts on OS X: `port install erlang`  
For Ubuntu and Debian: `apt-get install erlang`  
For Fedora: `yum install erlang`  
For FreeBSD: `pkg install erlang`  

### RabbitMQ
[RabbitMQ](https://www.rabbitmq.com/) is a message broker.  Angora will work
with any AMPQ message broker but it's only been tested with RabbitMQ.  Checkout
the RabbitMQ download and installation
[instructions](https://www.rabbitmq.com/download.html) for details about your
specfic environment.

### Python Libraries
The following libraries are required.
- Celery, `pip install celery`
- PyYaml, `pip install pyyaml`
- SQLAlchemy, `pip install sqlalchemy`
- FastAPI, `pip install fastapi`
- Uvicorn, `pip install uvicorn`
- HTTPX, `pip install httpx`

## Starting Angora

Make sure the angora folder is on the PYTHONPATH.
```
    export PYTHONPATH=/path/to/angora:$PYTHTONPATH
```

### RabbitMQ
Depending on your local installation, your steps may differ but here are the basics:
```
    cd /usr/local/opt/rabbitmq/sbin
    ./rabbitmq-server -detached
```
You can stop RabbitMQ anytime with the command: `sudo ./rabbitmqctl stop`

### Celery
You need to start the Celery worker from the directory containing the celery
jobs to run.  In the case of Angora there is only one and it is in `client.py`.
You need to start a Celery worker on each client.

    cd listeners/
    celery -A client worker --concurrency=8 --loglevel=debug -Ofair 2>&1

#### --concurrency
You'll want to set this number at something greater than one in order to
facilite running jobs in parallel.  This number does not need to match the
number of cores or threads you intend to use.  The default is the number of CPUs
detected.  Checkout the [Celery
documentation](https://docs.celeryproject.org/en/latest/userguide/workers.html)
for more on concurrency vs workers and other Celery details.

#### -Ofair
This sets the scheduling strategy to fair which in most cases is required for
Angora to work properly.  As of Celery 4.x this should be the default behavior.

### Server
`./listeners/server.py`

This will start up a listener for a queue named `initialize`.  If the queue does
not exist it will be created by simply starting up a listener.  There are two
callbacks, one logs all messages, the other searches for any job with a matching
trigger.  If any are found, those jobs are sent to the client queue.  You should
only have one instance of the server running, even in a distributed setup.

### Client
`./listeners/start.py`

This will start up a listener for a queue named `start`.  If the queue does not
exist it will be created by simply starting up a listener.  There is one
callback which executes the given job.

### Replay
`./listeners/replay.py`

This will create a queue named `replay` if it does not exist.  If the queue does
exist it will clear that queue.  You must run this at least once when starting
up an instance of Angora for the replay feature to work.

### Web API
A web API written with FastAPI.  Interfacing with Angora is meant to occur
through the API, although it is not a requirement.
### Web App
The default user interface to Angora.  The user is welcome to customize this in
any way they see fit.
## Jobs
A job is just any command you can run on the command line.  It can be as simple
as `echo "hello world"` or something more complicated.  Most likely you'll be
running some script, `job.sh` or `job.py`.  Angora does not interact with the
job at all, it just executes it and reads the return code or exit status.  A
return code of zero will be interpreted as success and anything will be
interpreted as failure.  The return code being read is equivalent to `echo $?`.

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
Optional field of one or more messages that the job will transmit when complete.  These are identical to triggers.  The idea is of course to use a string that will trigger another job.  This is how workflows are built.

#### replay
An optional field with the number of replay attempts.  A job will replay if it's exit status is anything other than zero.  If the tag is omitted a job will replay an infinite amount of times, this is considered the default behavior.  If set to any positive integer, the job will replay this many times.  If set to zero, the job will never replay.

#### parent_success
An optional file, set to `True` or `False`.  Omitting the tag is equivalent to `False`.  Checking that previous jobs have completed within a workflow may be required.  On instance is if a job may have multiple parents within a workflow.  The default behavior is for the job to execute whenever a message is read from the queue that correctly triggers that job.  In the case of multiple parents, the job will run multiple times.  If `parent_success` is set to `True` then the job will not execute unless all parent jobs are marked successful.  Another situation that may require checking parent success is if a job is executed manually but is dependent on the previous job.  Any time the parent success check fails, the job is marked as failing with no replay.  Parent success only checks the immediately preceeding parents.  If the job is depending on the entire preceeding workflow being successful, then you must set `parent_success` to `True` and all previous jobs.

### Workflows
At it's base, Angora isn't anything spectacular technologically.  It's a listener/callback application that matches strings.  One of it's main purposes though is to chain jobs together to build workflows.  This is all done via the configuration files.

```
-   name: step_1
    triggers:
        -   example.step.1
    command: echo "HELLO"
```

The preceeding is a single simple job.  When a job completes successfully any strings set in the `messages` tag will be sent to the job queue.
```
-   name: step_1
    triggers:
        -   example.step.1
    command: echo "HELLO"
    messages:
        -   example.step.2

-   name: step_2
    triggers:
        -   example.step.2
    command: echo "WORLD"
```

When `step_1` completes successfully, it will send `example.step.2` to the job queue.  The message is in turn matched to the trigger of job `step_2` which will then execute.

A single job can trigger multiple child jobs.
```
-   name: step_1
    triggers:
        -   example.step.1
    command: echo "HELLO WORLD"
    messages:
        -   example.step.2
        -   example.step.3
        -   example.step.4
```

Also a job can have several triggers, equating to several parent jobs.
```
-   name: step_4
    triggers:
        -   example.step.1
        -   example.step.2
        -   example.step.3
    command: echo "HELLO WORLD"
    messages:
        -   example.step.5
```

Admittedly, there are currently no tools to help build workflows.  The only option is to manually build them via the configuration files.  The web application has a method of viewing workflows.  The user is encouraged to use this to aid in the building of any workflows.

### Schedules
There are no acutal schedules in Angora.  How then do you schedule a job to run at a certain time?  Keep in mind Angora is very simple, it's waiting to read a string off a message queue, and then execute any job it can match.  In order to schedule a job, you schedule the message, not the job.  The simplest way of doing this is using crontab.  We interface with Angora via a web API, so we're going to cron a curl command.
```
*/5 * 1-5 * * curl -d "msg=time.`date +'\%H\%M'`" "http://angora/send"
```
Basically, at 1:05AM, this command will send a message of `time.0105` to the queue to be processed.  Any job with with that tirgger will then execute.  There, that's scheduling.  Remember, you can have as many jobs with the same trigger as you want, so the same message of `time.0105` can trigger 100 different jobs.

It's not just specific times that you can apply this method.  You can send the same message at set intervals and thus create a repeating task.
```
*/30 * 1-5 * * curl -d "msg=time.interval.30"" "http://angora/send"
```
This message will be sent every 30 minutes, and thus any job with `time.interval.30` as a trigger will run every 30 minutes.

A philosophical note, many may not agree with using crontab in this way.  "What's the point of a job orchestration system if I still have to use crontab?"  Yeah, I get that.  But I prefer to keep things simple.  As I mentioned before, Angora is at it's core, a listener/callback application.  Why program a scheduling application when I have a very reliable one in crontab already?

## User Interface
The user interface is a basic web application.  It's written using Starlette and Bootstrap 4.  Here you can view basic job statuses, execute jobs manually, view schedules, and view workflows.  Screenshots coming soon.

## Distributed Setup
COMING SOON


## TODO
1. Distributed operation
2. index tasks by name for faster lookup
3. index tasks by trigger for faster lookup
4. Convert to Quart?
5. Create the concept of a unique run id
6. Control EVERYTHING from the API


Notes
from celery import current_app
from celery.bin import worker


if __name__ == '__main__':
    app = current_app._get_current_object()

    worker = worker.worker(app=app)

    options = {
        'broker': 'amqp://guest:guest@localhost:5672//',
        'loglevel': 'INFO',
        'traceback': True,
    }

    worker.run(**options)
