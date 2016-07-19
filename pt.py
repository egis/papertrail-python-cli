#!/usr/bin/env python

import sys
import webbrowser

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
@click.argument('filename')
@click.pass_obj
def deploy(client, filename):
    """Deploys a package from a local FILENAME"""
    with open(filename, 'rb') as f:
        client.deploy_package(filename, f)

@papertrail.command()
@click.argument('query', required=False)
@click.pass_obj
def pql(client, query):
    """
    Executes a PQL query and outputs the result.
    Starts an interactive query shell if no query is provided.
    """
    if query is None:
        run_pql_repl(client)
    else:
        click.echo('Running %s' % query)

        response = client.pql_query(query)
        print_pql_response(response)

@papertrail.command()
@click.argument('code')
@click.pass_obj
def eval(client, code):
    """Evaluates script on the server"""
    response = client.post('script/execute', { 'code': code })
    sys.stdout.write(response.text.replace('\\n', '\n'))

@papertrail.command()
@click.argument('script')
@click.argument('dest_file', required=False)
@click.pass_obj
def download_script(client, script, dest_file):
    """Downloads a remote SCRIPT to DEST_FILE"""

    path = 'public/file/System/scripts/{0}/{0}'.format(script)

    response = client.get(path)

    if dest_file is None:
        dest_file = script

    with open(dest_file, 'w') as f:
        f.write(response.text)

@papertrail.command()
@click.argument('node')
@click.argument('name')
@click.pass_obj
def update_doc(client, node, name):
    """Updates a document located at NODE/NAME from a local file with the same NAME."""
    with open(name, 'r') as f:
        client.update_document('{}/{}'.format(node, name), f.read())

@papertrail.command()
@click.argument('filename')
@click.pass_obj
def update_script(client, filename):
    """Uploads and updates the script document from a provided file"""
    with open(filename, 'rt') as f:
        client.upload_script(filename, f.read())

@papertrail.command()
@click.argument('url')
@click.pass_obj
def new_token(client, url):
    """Generates and outputs a new token for a provided URL"""
    result = client.new_token(url)
    click.echo(result.text)

@papertrail.command()
def new_form():
    """Creates a new form from a provided filename"""  
    webbrowser.open('http://')

def new_classic():
    webbrowser.open('http://')

if __name__ == '__main__':
    papertrail()
