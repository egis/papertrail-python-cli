#!/usr/bin/env python

import sys
import webbrowser
from os.path import basename

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
@click.argument('file', type=click.File('rb'))
@click.pass_obj
def deploy(client, file):
    """Deploys a package from a local FILE"""
    client.deploy_package(basename(file.name), file)

@papertrail.command()
@click.pass_obj
def redeploy(client):
    """Redeploys workflows"""
    client.redeploy_workflow()

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
    click.echo(client.execute(code))

@papertrail.command()
@click.argument('file', type=click.File('rt'))
@click.pass_obj
def execute(client, file):
    """Executes a script FILE on the server"""
    click.echo(client.execute(file.read()))

@papertrail.command()
@click.argument('path')
@click.argument('file', type=click.File('rb'))
@click.pass_obj
def upload(client, path, file):
    """
    Uploads FILE to PATH.

    E.g. upload System/scripts/TEST.groovy build/libTest.groovy
    """
    client.update_document(path, file)

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
@click.argument('file', type=click.File('rb'))
@click.pass_obj
def update_doc(client, node, file):
    """Updates a document located at NODE/FILE from a local FILE."""
    client.update_document('{}/{}'.format(node, basename(file.name)), file)

@papertrail.command()
@click.argument('file', type=click.File('rt'))
@click.pass_obj
def update_script(client, file):
    """Uploads and updates the script document from a provided FILE"""
    client.upload_script(basename(file.name), file)

@papertrail.command()
@click.argument('url')
@click.pass_obj
def new_token(client, url):
    """Generates and outputs a new token for a provided URL"""
    click.echo(client.new_token(url))

@papertrail.command()
@click.argument('form_name')
@click.pass_obj
def new_form(client, form_name):
    """Creates a new form from a provided FORM_NAME"""
    doc_id = client.new_form(form_name)['docId']
    token = client.new_token('/web/eSign')
    webbrowser.open('{}?{}'.format(token, doc_id))

def new_classic():
    webbrowser.open('http://')

if __name__ == '__main__':
    papertrail()
