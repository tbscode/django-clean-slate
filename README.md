# django clean slate by tbscode

![Django Tests + Container Build](https://github.com/tbscode/django-clean-slate/actions/workflows/tests.yaml/badge.svg)
![Build Docs](https://github.com/tbscode/django-clean-slate/actions/workflows/docs.yaml/badge.svg)

This is a clean slate fullstack web setup.

system requirements: `python > 3.8`, `docker`

> This refects ( in part ) the stack used on little-world.com

## The stack

The whole stack is fully dockerized.

Backend:

- django ( 4.1.2 )
  - General backend routing and authentication
- channels ( 4.0.0 )
  - async asgi application interface and websocket handlers
- celery ( 5.2.7 )
  - background ad reoccuring task management

Frontend:

- django-webpack ( serving bundles )
- react app(s) ( bundled with webpack )

> As alternative to serving static js bundles this stack might be updated to use django-nextjs

## Deployment

The **production** application is suppsed to be deployed with Kubernetes `k8s.io` ( configurations are **not included** in this repo ).
For production I recommend a pooled postgressql database, a redis memory store (for websocket support), a s3 storage bucked for serving static files and a load balanced k8 node pool. This configuration allowes full horizontal - on demand - scaling.

This repo offers a **staging** deployment! For staging we can easily use [`white-noise`](http://whitenoise.evans.io/en/stable/) to serve static files, a simple in-container redis instance and a simple in-container sqllite database. This can be auto deployed on a free-tier Heroku instance - or similar - using the `Dockerfile.stage` in combination with a github workflow.

This even offers the flexibility of seperate staging for seperate developers simply by opening mulitple Heroku accounts.

> If you wan't to use this 'clean-slate' for a hoppy project a free ( or hobby ) tier Heroku instance might be completely sufficient

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
