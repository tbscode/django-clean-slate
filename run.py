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
    dtag = ["-t", f"{TAG}.dev"]
    ptag = ["-t", f"{TAG}.prod"]
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
    parser.add_argument('actions', metavar='A', type=str, default=[
                        "build", "run"], nargs='?', help='action')
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


def shell(dev=True):
    """ Run a shell on a running container instance """
    ps = [x for x in _running_instances() if (
        "dev" if dev else "prod") in x["Image"]]
    assert len(ps) > 0, "no running instances found"
    _cmd = ["docker", "exec", "-it", ps[0]["ID"], c.shell]
    subprocess.run(" ".join(_cmd), shell=True)


def build(dev=True):
    """
    Builds the docker container 
    (if dev): uses the Dockerfile.dev
    """
    if not dev:
        raise NotImplementedError
    _cmd = [*c.dbuild, *c.file, *(c.dtag if dev else c.ptag), "."]
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


def run(dev=True):
    """
    Running the docker image, this requires a build image to be present.
    Rebuild the image when ever you cange packages.
    if dev: 
        Then container will mount the local `./back` folder,
        and forward port `c.port` (default 8000)
    """
    _cmd = [*c.drun, *(c.denv if dev else c.penv), *c.vmount,
            *c.port, *(c.dtag if dev else c.ptag)]
    print(" ".join(_cmd))

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
    }
}


def _print_help(a):
    _parser().print_help()
    print("Generating action help messages...")
    for act in ACTIONS:
        print(f"action '{act}' ")
        f = ACTIONS[act].get("func", None)
        if f:
            info = ACTIONS[act]['func'].__doc__
            print(f"\tinfo: {info}\n")
    pass


def _action_by_alias(alias):
    for act in ACTIONS:
        if alias in [*ACTIONS[act]["alias"], act]:
            return act, ACTIONS[act]
    else:
        raise Exception(f"Action or alias '{alias}' not found")


def main():
    """
    Entrypoint for `run.py` 
    Using the script requires *only* docker!
    e.g:
    `./run.py`: ( use without local python install via `docker run -it --rm --name runpy -v "$PWD":/rapp -w /rapp python:3 python run.py` )
        Default; Build, then run development container
    `./run.py build run redis`:
        Also start redis server for local dev
    `./run.py shell`:
        Login to `c.shell` on a *running* container
    """
    a = args()
    for action in a.actions:
        k, _action = _action_by_alias(action)
        print(f"Performing '{k}' -action")
        _action["exec"](a)
        if not _action.get("continue", False):
            print(f"Ran into final action '{action}'")
            break
    print("Exiting `run.py`...")


if __name__ == "__main__":
    main()
