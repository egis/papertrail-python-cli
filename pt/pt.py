#!/usr/bin/env python

import sys
import webbrowser
from os.path import basename

import click

from client import Client
from pql import print_pql_response, print_pql_csv, print_pql_json, run_pql_repl

@click.group()
@click.option('--username', default='admin', envvar='PT_USER', help='or use the PT_USER environment variable')
@click.option('--password', default='p', envvar='PT_PASS', help='or use the PT_PASS environment variable')
@click.option('--host', default='http://localhost:8080', envvar='PT_API', help='or use the PT_API environment variable')
@click.pass_context
def papertrail(ctx, host, username, password):
    if not host.startswith('http://') and not host.startswith('https://'):
        host = 'http://' + host
    ctx.obj = Client(host, username, password)

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
@click.option('--format', default='user', type=click.Choice(['user', 'csv', 'json', 'column']),
            help='Data output format')
@click.pass_obj
def pql(client, query, format):
    """
    Executes a PQL query and outputs the result.

    Starts an interactive query shell if no query is provided.

    Use FORMAT option to provide an output format.
    "user" outputs human-readable data (it's used by default).
    "column" outputs the first column of each result row (it's useful e.g. for xargs).
    "csv" and "json" outputs data in the respective formats.

    \033[1mExamples\033[0m

    awk selector for CSV output:

      pt pql --format csv "SELECT docId FROM node" | awk -F "," '{ print $1 }'

    with xargs:

      pt pql --format column "SELECT docId FROM node" | xargs

    with the JSON output and jq:

      pt pql --format json "SELECT docId FROM node" | jq '.items[0]'
    """
    if query is None:
        run_pql_repl(client)
    else:
        response = client.pql_query(query)
        sys.stderr.write('\nRunning %s\n\n' % query)
        if response is not None:
            if format == 'user':
                print_pql_response(response)
            elif format == 'csv':
                print_pql_csv(response)
            elif format == 'column':
                for row in response['items']:
                    print(row[0])
            elif format == 'json':
                print_pql_json(response)

@papertrail.command()
@click.argument('code')
@click.pass_obj
def eval(client, code):
    """Evaluates script on the server"""

    prefix = """
    import com.egis.*;
    import com.egis.kernel.*;
    import com.egis.kernel.db.*;
    import com.egis.utils.*;
    import com.egis.data.*;
    import com.egis.data.node.*;
    import com.egis.data.party.*;
    Session s = Kernel.get(Session.class);
    DbManager db = Kernel.get(DbManager.class);
    """

    click.echo(client.execute(prefix + code))

@papertrail.command()
@click.argument('url', nargs=1)
@click.argument('data', nargs=-1)
@click.pass_obj
def form(client, url, data):
    """
    Makes a generic POST form request to a provided URL, optionally passing a DATA set in the 'key=value' format.

    Usage example:
    pt form execute/action key=value
    """
    data = { pair[0]: pair[1] for pair in map(lambda pair: pair.split('='), data) }
    client.post(url, data)

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
@click.argument('path')
@click.argument('dest_file', required=False)
@click.pass_obj
def download(client, path, dest_file):
    """Downloads a remote PATH to DEST_FILE"""
    full_path = 'public/file/{0}/{1}'.format(path, basename(path))
    response = client.get(full_path)

    if response.status_code == 200:
        if dest_file is None:
            dest_file = basename(path)

        with open(dest_file, 'w') as f:
            f.write(response.text)

@papertrail.command()
@click.argument('script')
@click.argument('dest_file', required=False)
@click.pass_obj
def download_script(client, script, dest_file):
    """Downloads a remote SCRIPT to DEST_FILE"""
    path = 'public/file/System/scripts/{0}/{0}'.format(script)

    response = client.get(path)

    if response.status_code == 200:
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

@papertrail.command()
@click.argument('form_name')
@click.pass_obj
def new_classic(client, form_name):
    """Creates a new form from a provided FORM_NAME, using the classic UI"""
    doc_id = client.new_form(form_name)['docId']
    token = client.new_token('/jsForm/edit/')
    webbrowser.open('{}?{}'.format(token, doc_id))

if __name__ == '__main__':
    papertrail()
