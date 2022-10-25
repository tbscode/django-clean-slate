# django clean slate by tbscode

This is a clean slate fullstack web setup.

system requirements: `python > 3.8`, `docker`

> This refects ( in part ) the stack used on little-world.com

## The stack

The whole stack is fully dockerized.

Backend:

- django ( 4.1.2 )
  - General backend routing and authentication
- channels + daphne ( 4.0.0 )
  - async asgi application interface and websocket handlers
- celery ( 5.2.7 )
  - background ad reoccuring task management

Frontend:

- django-webpack ( serving bundles )
- react app(s) ( bundled with webpack )

> As alternative to serving static js bundles this stack might be updated to use django-nextjs

## Documentation

Are automaticly generated using `sphinx` and published to [Git Hub Pages](https://tbscode.github.io/django-clean-slate).
Docs can be generated localy using `./run.py docs` or automaticly using a github workflow.

e.g.: see full documentation of `./run.py` [here](https://tbscode.github.io/django-clean-slate/apidoc/extra_mods.run.html#module-extra_mods.run)

## Tools

`run.py` manages full docker and frontend builds.

For info run `./run.py ?` or check the script.

## Current state

This is still work in progress main missing parts are:

- [ ] Integrate django webpackloader
- [ ] Example async view and example consumer
- [ ] seperated repo for example production build
