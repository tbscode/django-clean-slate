#!/usr/bin/env python3
from ast import alias
from cProfile import label
from functools import partial
from decorator import decorator
import os
import sys
import subprocess
import argparse
import signal
import json

TAG = "littleworld_back"
FRONT_TAG = "littleworld_front"
PORT = 8000


class c:
    # Backend container stuff
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

    # Frontend container stuff
    front_docker_file = ["-f", "Dockerfile.front"]
    vmount_front = ["-v", f"{os.getcwd()}/front:/app"]
    front_tag = f"{FRONT_TAG}.dev"


subprocess_capture_out = {
    "capture_output": True,
    "text": True
}

ACTIONS = {}  # Populated with the `@register_action` decorator


def _dispatch_register_action_decorator(f, name=None, cont=False, call=None, alias=[]):
    ACTIONS.update({name if name else f.__name__: {
        "alias": alias,
        "continue": cont,
        "func": f,
        "exec": call if call else lambda a: f(a)
    }})

    def run(*args, **kwargs):
        return f(*args, **kwargs)
    return run


def register_action(**kwargs):
    return partial(_dispatch_register_action_decorator, **kwargs)


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


def _env_as_dict(path: str) -> dict:
    with open(path, 'r') as f:
        return dict(tuple(line.replace('\n', '').split('=')) for line
                    in f.readlines() if not line.startswith('#'))


def args():
    return _parser().parse_args()


def extract_static():
    pass


def _is_dev(a):
    return "dev" in a.btype


def _running_instances(tag=TAG):
    """ Get a list of running instance for docker 'tag' """
    _cmd = ["docker", "ps", "--format",
            r"""{"ID":"{{ .ID }}", "Image": "{{ .Image }}", "Names":"{{ .Names }}"}"""]
    out = str(subprocess.run(_cmd, **subprocess_capture_out).stdout)
    ps = [eval(x) for x in out.split("\n") if x.strip()]
    return [x for x in ps if tag in x["Image"]]


@register_action(cont=True, alias=["k"])
def kill(args, front=True, back=True):
    """ Kills all the running container instances (back & front)"""
    ps = [*(_running_instances() if back else []),
          *(_running_instances(tag=FRONT_TAG) if front else [])]
    _cmd = ["docker", "kill"]
    for p in ps:
        _c = _cmd + [p["ID"]]
        print(' '.join(_c))
        subprocess.run(_c)


def _run_in_running(dev, commands, backend=True, capture_out=False, work_dir=None):
    """
    Runns command in a running container.
    Per default this looks for a backend container.
    It will look for a frontend container with backend=False
    """
    ps = [x for x in _running_instances() if (
        "dev" if dev else "prod") in x["Image"]] if backend else _running_instances(tag=FRONT_TAG)
    assert len(ps) > 0, "no running instances found"
    _cmd = ["docker", "exec",
            *(["-w", work_dir] if work_dir else []), "-it", ps[0]["ID"], *commands]
    if not capture_out:
        subprocess.run(" ".join(_cmd), shell=True)
    else:
        return str(subprocess.run(_cmd, **subprocess_capture_out).stdout)


@register_action(alias=["s", "sh", "$"])
def shell(args):
    """ Run a shell on a running container instance """
    _run_in_running(_is_dev(args), [c.shell])


@register_action(alias=["dump", "backup"])
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


@register_action(alias=["load", "db_init"])
def loaddata(args):
    """ Load data from fixture """
    assert _is_dev(args), "Loading fixture data is only allowed in dev"
    assert args.input, "Please provide '-i' input file"
    _run_in_running(_is_dev(args), ["python3", "manage.py",
                    "dumpdata", "-i", args.input])


@register_action(alias=["m"], cont=True)
def migrate(args):
    """ Migrate db inside docker container """
    run(_is_dev(args), background=True)
    _run_in_running(_is_dev(args), ["python3", "manage.py",
                    "makemigrations"])
    _run_in_running(_is_dev(args), ["python3", "manage.py",
                    "migrate"])
    kill(args, front=False)


@register_action(alias=["b"], cont=True)
def build(args):
    """
    Builds the docker container
    (if dev): uses the Dockerfile.dev
    """
    if not _is_dev(args):
        raise NotImplementedError
    _cmd = [*c.dbuild, *c.file, "-t", c.dtag if _is_dev(args) else c.ptag, "."]
    print(" ".join(_cmd))
    subprocess.run(_cmd)


def _make_webpack_command(env, config, debug: bool, watch: bool):
    _cmd = [
        './node_modules/.bin/webpack',
        *(["--watch"] if watch else []),
        '--env', f'PUBLIC_PATH={env["WEBPACK_PUBLIC_PATH"]}',
        '--env', f'DEV_TOOL={env["WEBPACK_DEV_TOOL"]}',
        '--env', 'DEBUG=1' if debug else 'DEBUG=0',
        '--mode', 'development' if debug else 'production',
        '--config', config]
    return _cmd


@register_action(alias=["fb", "bf"], cont=True)
def build_front(args):
    """
    Builds the frontends
    1. Build the frontend docker image
    2. Run the container ( keep it running artifically see Dockerfile.front )
    3. Run `npm i`
    4. For all frontends ( check `env.FR_FRONTENDS` ) run `npm i`
    5. For all frontends run webpack build
    6. Kill the frontend container
    """
    if not _is_dev(args):
        raise NotImplementedError
    _cmd = [*c.dbuild, *c.front_docker_file, "-t",
            c.front_tag, "."]
    print(" ".join(_cmd))
    subprocess.run(_cmd)  # 1
    _cmd = [*c.drun, *(c.denv if _is_dev(args) else c.penv), *
            c.vmount_front, "-d", c.front_tag]
    env = _env_as_dict(c.denv[1])
    subprocess.run(_cmd)  # 2
    _run_in_running(_is_dev(args), ["npm", "i"], backend=False)  # 3
    frontends = env["FR_FRONTENDS"].split(",")
    print(
        f'`npm i` for frontends: {frontends} \nAdd frontends under `FR_FRONTENDS` in env, place them in front/apps/')
    for front in frontends:
        _run_in_running(
            _is_dev(args), ["npm", "i"], work_dir=f"/app/apps/{front}", backend=False)  # 4
    # Frontend builds can only be performed with the webpack configs present
    with open('./front/webpack.template.js', 'r') as f:
        webpack_template = f.read()
    for front in frontends:
        config_path = f'front/webpack.{front}.config.js'
        if not os.path.isfile(config_path):
            # The config doesn't yet exist so we create it from template
            print(
                f"webpack config for '{front}' doesn't yet exist, creating '{config_path}'")
            with open(config_path, 'w') as f:
                f.write(webpack_template.replace("$frontendName", front))
            # Then we also have to add the build command to 'front/package.json'
            # This adds 3 scripts: watch_<front>, build_<front>_dev, build_<front>_prod
            print("Writing new commands to 'front/package.json'")
            with open(f'front/package.json', 'r+') as f:
                package = json.loads(f.read())
                f.seek(0)
                package["scripts"].update({
                    f"watch_{front}": " ".join(_make_webpack_command(env, f'webpack.{front}.config.js', watch=True, debug=True)),
                    f"build_{front}_dev": " ".join(_make_webpack_command(env, f'webpack.{front}.config.js', watch=False, debug=True)),
                    f"build_{front}_prod": " ".join(_make_webpack_command(env, f'webpack.{front}.config.js', watch=False, debug=False)),
                })
                f.write(json.dumps(package, indent=2))
                f.truncate()
        _run_in_running(
            _is_dev(args), ["npm", "run", f"build_{front}_{args.btype}"], backend=False)
    kill(args, back=False)


@register_action(alias=["rds", "rd", "redis-server"])
def redis(args):
    """
    Runs a local instance of `redis-server` ( required for the chat )
    """
    assert _is_dev(args), "Local redis is only for development"
    _cmd = [*c.drun, *c.redis_port, "-d", "redis:5"]
    print(' '.join(_cmd))
    subprocess.run(_cmd)


@register_action(alias=["r"], call=lambda a: run(_is_dev(a)))
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
            kill(None, front=False)
        signal.signal(signal.SIGINT, handler)
        p = subprocess.call(" ".join(_cmd), shell=True, stdin=subprocess.PIPE)


@register_action(name="help", alias=["h", "?"])
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
