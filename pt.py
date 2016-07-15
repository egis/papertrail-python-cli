#!/usr/bin/env python

import click

from client import Client
from pql import print_pql_response

@click.group()
@click.option('--username', default='admin', envvar='PT_API_USER')
@click.option('--password', default='1', envvar='ADMIN_PASS')
@click.option('--host', default='http://localhost:8080', envvar='PT_API')
@click.pass_context
def papertrail(ctx, host, username, password):
    ctx.obj = Client(host, username, password)

@papertrail.command()
@click.argument('query', default=None)
@click.pass_obj
def pql(client, query):
    click.echo('Running %s' % query)

    response = client.pql_query(query)
    print_pql_response(response)

if __name__ == '__main__':
    papertrail()
