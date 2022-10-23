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

## Tools

`run.py` manages full docker and frontend builds.

For info run `./run.py ?` or check the script.

## Current state

This is still work in progress main missing parts are:

- [ ] automated webpack builds ( dockerized )
- [ ] seperated repo for example production build
