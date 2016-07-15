#!/usr/bin/env python

import sys

import click

from client import Client
from pql import print_pql_response, run_pql_repl

@click.group()
@click.option('--username', default='admin', envvar='PT_API_USER')
@click.option('--password', default='1', envvar='ADMIN_PASS')
@click.option('--host', default='http://localhost:8080', envvar='PT_API')
@click.pass_context
def papertrail(ctx, host, username, password):
    ctx.obj = Client(host, username, password)

@papertrail.command()
@click.pass_obj
def status(client):
    client.status()

@papertrail.command()
@click.argument('query', default='')
@click.pass_obj
def pql(client, query):
    if query == '':
        run_pql_repl(client)
    else:
        click.echo('Running %s' % query)

        response = client.pql_query(query)
        print_pql_response(response)

@papertrail.command()
@click.argument('script')
@click.pass_obj
def download_script(client, script):
    path = 'public/file/System/scripts/{0}/{0}'.format(script)

    response = client.get(path)
    sys.stdout.write(response.text)

def update_doc():
    pass

def update_script():
    pass

def new_token():
    pass

def new_form():
    pass

def new_classic():
    pass

if __name__ == '__main__':
    papertrail()
