#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse
import signal
import json

TAG = "littleworld"
PORT = 8000


class c:
    dbuild = ["docker", "build"]
    drun = ["docker", "run"]
    file = ["-f", "Dockerfile.dev"]
    dtag = f"{TAG}.dev"
    ptag = f"{TAG}.prod"
    port = ["-p", f"{PORT}:8000"]
    vmount = ["-v", f"{os.getcwd()}/back:/app"]
    denv = ["--env-file", "./env"]
    penv = ["--env-file", "./penv"]
    shell = "/bin/bash"
    redis_port = ["-p", "6379:6379"]


subprocess_capture_out = {
    "capture_output": True,
    "text": True
}


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--btype', default="dev", help="prod, dev, any")
    parser.add_argument(
        '-o', '--output', help="Ouput file or path required by some actions")
    parser.add_argument(
        '-i', '--input', help="Input file required by some actions")
    parser.add_argument('actions', metavar='A', type=str, default=[
                        "build", "migrate", "run"], nargs='?', help='action')
    return parser


def args():
    return _parser().parse_args()


def extract_static():
    pass


def _is_dev(a):
    return "dev" in a.btype


def _running_instances():
    _cmd = ["docker", "ps", "--format",
            r"""{"ID":"{{ .ID }}", "Image": "{{ .Image }}", "Names":"{{ .Names }}"}"""]
    print(" ".join(_cmd))
    out = str(subprocess.run(_cmd, **subprocess_capture_out).stdout)
    ps = [eval(x) for x in out.split("\n") if x.strip()]
    return [x for x in ps if TAG in x["Image"]]


def kill():
    """ Kills all the running container instances """
    ps = _running_instances()
    _cmd = ["docker", "kill"]
    for p in ps:
        _c = _cmd + [p["ID"]]
        print(' '.join(_c))
        subprocess.run(_c)


def _run_in_running(dev, commands):
    ps = [x for x in _running_instances() if (
        "dev" if dev else "prod") in x["Image"]]
    assert len(ps) > 0, "no running instances found"
    _cmd = ["docker", "exec", "-it", ps[0]["ID"], *commands]
    subprocess.run(" ".join(_cmd), shell=True)


def shell(dev=True):
    """ Run a shell on a running container instance """
    _run_in_running(dev, [c.shell])


def dumpdata(args):
    """ Creates a full database fixture """
    assert _is_dev(args), "Dumping data only allowed in dev"
    output = []
    if not args.output:
        print("No '-o' output specified, dumping to stdout")
    else:
        output = ["--output", args.output]
    _run_in_running(_is_dev(args), ["python3", "manage.py",
                    "dumpdata", *(["--indent", "2"] if not args.output else []), *output])


def loaddata(args):
    """ Load data from fixture """
    assert _is_dev(args), "Loading fixture data is only allowed in dev"
    assert args.input, "Please provide '-i' input file"
    _run_in_running(_is_dev(args), ["python3", "manage.py",
                    "dumpdata", "-i", args.input])


def migrate(args):
    """ Migrate db inside docker container """
    run(_is_dev(args), background=True)
    _run_in_running(_is_dev(args), ["python3", "manage.py",
                    "makemigrations"])
    _run_in_running(_is_dev(args), ["python3", "manage.py",
                    "migrate"])
    kill()


def build(dev=True):
    """
    Builds the docker container 
    (if dev): uses the Dockerfile.dev
    """
    if not dev:
        raise NotImplementedError
    _cmd = [*c.dbuild, *c.file, "-t", c.dtag if dev else c.ptag, "."]
    print(" ".join(_cmd))
    subprocess.run(_cmd)


def redis(dev):
    """
    Runs a local instance of `redis-server` ( required for the chat )
    """
    assert dev, "Local redis is only for development"
    _cmd = [*c.drun, *c.redis_port, "-d", "redis:5"]
    print(' '.join(_cmd))
    subprocess.run(_cmd)


def run(dev=True, background=False):
    """
    Running the docker image, this requires a build image to be present.
    Rebuild the image when ever you cange packages.
    if dev: 
        Then container will mount the local `./back` folder,
        and forward port `c.port` (default 8000)
    """
    _cmd = [*c.drun, *(c.denv if dev else c.penv), *c.vmount,
            *c.port, "-d" if background else "-t", c.dtag if dev else c.ptag]
    print(" ".join(_cmd))

    if background:
        subprocess.run(_cmd)
    else:
        def handler(signum, frame):
            print("EXITING\nKilling container...")
            kill()
        signal.signal(signal.SIGINT, handler)
        p = subprocess.call(" ".join(_cmd), shell=True, stdin=subprocess.PIPE)


ACTIONS = {
    "redis": {
        "alias": ["rds", "rd", "redis-server"],
        "continue": True,
        "func": redis,
        "exec": lambda a: redis(_is_dev(a))
    },
    "kill": {
        "alias": ["k"],
        "func": kill,
        "exec": lambda a: kill()
    },
    "shell": {
        "alias": ["s", "sh", "$"],
        "func": shell,
        "exec": lambda a: shell(_is_dev(a))
    },
    "run": {
        "alias": ["r"],
        "func": run,
        "exec": lambda a: run(_is_dev(a))
    },
    "build": {
        "alias": ["b"],
        "continue": True,
        "func": build,
        "exec": lambda a: build(_is_dev(a))
    },
    "help": {
        "alias": ["h", "?"],
        "continue": False,
        "exec": lambda a: _print_help(a)
    },
    "migrate": {
        "alias": ["m"],
        "continue": True,
        "func": migrate,
        "exec": lambda a: migrate(a)
    },
    "dumpdata": {
        "alias": ["dump", "backup"],
        "continue": False,
        "func": dumpdata,
        "exec": lambda a: dumpdata(a)
    },
    "loaddata": {
        "alias": ["load", "db_init"],
        "continue": False,
        "func": loaddata,
        "exec": lambda a: loaddata(a)
    }
}


def _print_help(a):
    print(main.__doc__)
    _parser().print_help()
    print("Generating action help messages...")
    for act in ACTIONS:
        print(
            f"action '{act}' (with aliases {', '.join(ACTIONS[act]['alias'])})")
        f = ACTIONS[act].get("func", None)
        if f:
            info = ACTIONS[act]['func'].__doc__
            print(f"\tinfo: {info}\n")
        else:
            print("\tNo info availabol")


def _action_by_alias(alias):
    for act in ACTIONS:
        if alias in [*ACTIONS[act]["alias"], act]:
            return act, ACTIONS[act]
    else:
        raise Exception(f"Action or alias '{alias}' not found")


def main():
    """
    Entrypoint for `run.py` 
    Using the script requires *only* docker and python!
    e.g:
    `./run.py ?`:
        Show basic doc/ help message
    `./run.py`:
        Default; Build, then run development container
    `./run.py build run redis`:
        Also start redis server for local dev
    `./run.py shell`:
        Login to `c.shell` on a *running* container
    """
    a = args()
    for action in a.actions if isinstance(a.actions, list) else [a.actions]:
        k, _action = _action_by_alias(action)
        print(f"Performing '{k}' -action")
        _action["exec"](a)
        if not _action.get("continue", False):
            print(f"Ran into final action '{k}'")
            break
    print("Exiting `run.py`...")


if __name__ == "__main__":
    main()
