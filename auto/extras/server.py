#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

"""
Test server to act as CentralEGA endpoint for users
"""

import sys
import os
import asyncio
# import ssl
import yaml
from pathlib import Path
from functools import wraps
from base64 import b64decode

# import logging as LOG

from aiohttp import web
import jinja2
import aiohttp_jinja2

instances = {}
for instance in os.environ.get('LEGA_INSTANCES', '').strip().split(','):
    instances[instance] = (Path(f'/cega/users/{instance}'), os.environ[f'CEGA_REST_{instance}_PASSWORD'])
default_inst = os.environ.get('DEFAULT_INSTANCE', 'lega')


def protected(func):
    @wraps(func)
    def wrapped(request):
        auth_header = request.headers.get('AUTHORIZATION')
        if not auth_header:
            raise web.HTTPUnauthorized(text=f'Protected access\n')
        _, token = auth_header.split(None, 1)  # Skipping the Basic keyword
        passwd = b64decode(token).decode()
        info = instances.get(default_inst)
        if info is not None and info[1] == passwd:
            request.match_info['lega'] = default_inst
            request.match_info['users_dir'] = info[0]
            return func(request)
        raise web.HTTPUnauthorized(text=f'Protected access\n')
    return wrapped


@aiohttp_jinja2.template('users.html')
async def index(request):
    users = {}
    for instance, (users_dir, _) in instances.items():
        users[instance] = {}
        files = (f for f in users_dir.iterdir() if f.is_file())
        for f in files:
            with open(f, 'r') as stream:
                users[instance][f.stem] = yaml.load(stream)
    return {"cega_users": users}


@protected
async def user(request):
    name = request.match_info['name']
    lega_instance = request.match_info['lega']
    users_dir = request.match_info['users_dir']

    try:
        with open(f'{users_dir}/{name}.yml', 'r') as stream:
            d = yaml.load(stream)
            return web.json_response(d)
    except OSError:
        raise web.HTTPBadRequest(text=f'No info for user {name} in LocalEGA {lega_instance}... yet\n')


@protected
async def userid(request):
    uid = request.match_info['id']
    lega_instance = request.match_info['lega']
    users_dir = request.match_info['users_dir']

    try:
        with open(f'{users_dir}_ids/{uid}.yml', 'r') as stream:
            d = yaml.load(stream)
            return web.json_response(d)
    except OSError:
        raise web.HTTPBadRequest(text=f'No info for user id {userid} in LocalEGA {lega_instance}... yet\n')


# Unprotected access
async def pgp_pbk(request):
    name = request.match_info['id']
    try:
        with open(f'/ega/users/pgp/{name}.pub', 'r') as stream:  # 'rb'
            return web.Response(text=stream.read())              # .hex()
    except OSError:
        raise web.HTTPBadRequest(text=f'No info about {name} in CentralEGA... yet\n')


def main():

    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"

    # ssl_certfile = Path(CONF.get('keyserver', 'ssl_certfile')).expanduser()
    # ssl_keyfile = Path(CONF.get('keyserver', 'ssl_keyfile')).expanduser()
    # LOG.debug(f'Certfile: {ssl_certfile}')
    # LOG.debug(f'Keyfile: {ssl_keyfile}')

    # sslcontext = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    # sslcontext.check_hostname = False
    # sslcontext.load_cert_chain(ssl_certfile, ssl_keyfile)
    sslcontext = None

    loop = asyncio.get_event_loop()
    server = web.Application(loop=loop)

    template_loader = jinja2.FileSystemLoader("/cega")
    aiohttp_jinja2.setup(server, loader=template_loader)

    # Registering the routes
    server.router.add_get('/', index, name='root')
    server.router.add_get('/user/{name}', user, name='user')
    server.router.add_get('/id/{id}', userid, name='id')
    server.router.add_get('/pgp/{id}', pgp_pbk, name='pgp')

    web.run_app(server, host=host, port=8001, shutdown_timeout=0, ssl_context=sslcontext)


if __name__ == '__main__':
    main()
