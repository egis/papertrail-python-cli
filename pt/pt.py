#!/usr/bin/env python

import sys
import webbrowser
import json
import os
import os.path
from os.path import basename

import click
import colorama

from client import Client
from pql import print_pql_response, print_pql_csv, print_pql_json, run_pql_repl
import service
import commands
from utils import bgcolors, load_site_config, download_file
import tempfile
from cookiecutter.main import cookiecutter
import subprocess

from commons import *


@click.group()
@click.option('--site', required=False, envvar='PT_SITE', help='Name of the file with site credentials')
@click.option('--username', default='admin', envvar=['PT_USER', 'PT_API_USER'], help='or use the PT_USER/PT_API_USER environment variable')
@click.option('--password', default='p', envvar=['PT_PASS', 'PT_API_PASS'], help='or use the PT_PASS/PT_API_PASS environment variable')
@click.option('--host', default='http://localhost:8080', envvar='PT_API', help='or use the PT_API environment variable')
@click.pass_context
def papertrail(ctx, host, username, password, site):
    if site is not None:
        if os.name == 'nt':
            raise Exception('--site is not supported on Windows')

        env = load_site_config(site)

        if env is None:
            raise click.BadParameter('site config "%s" not found' % site)

        host = env.get('PT_API', host)
        username = env.get('PT_API_USER', username)
        username = env.get('PT_USER', username)
        password = env.get('PT_API_PASS', password)
        password = env.get('PT_PASS', password)

    if not host.startswith('http://') and not host.startswith('https://'):
        host = 'http://' + host

    ctx.obj = Client(host, username, password)


@papertrail.command()
@click.option('--host', default='http://localhost:8080', envvar='PT_API', help='or use the PT_API environment variable')
@click.option('--username', default='admin', envvar=['PT_USER', 'PT_API_USER'], help='or use the PT_USER/PT_API_USER environment variable')
@click.option('--password', default='p', envvar=['PT_PASS', 'PT_API_PASS'], help='or use the PT_PASS/PT_API_PASS environment variable')
@click.option('--file', required=True, help='file to save site credentials to')
def login(host, username, password, file):
    """Set the site credentials"""
    f = open(file, 'w')
    f.write('PT_API=%s\0' % host)
    f.write('PT_API_USER=%s\0' % username)
    f.write('PT_USER=%s\0' % username)
    f.write('PT_API_PASS=%s\0' % password)
    f.write('PT_PASS=%s\0' % password)


@papertrail.command()
@click.argument('file', type=click.File('rb'))
@click.pass_obj
def deploy(client, file):
    """Deploys a package from a local FILE"""
    client.deploy_package(basename(file.name), file)


@papertrail.command()
@click.argument('name')
@click.pass_obj
def create_project(client, name):
    """Creates a new project for PaperTrail"""
    print("Downloading https://github.com/egis/ProjectBootstrap...")
    path = cookiecutter('https://github.com/egis/ProjectBootstrap.git', no_input=True, output_dir=name)
    gradle_exec = "gradle"

    if os.name == 'nt':
        gradle_exec += ".bat"

    print("Setting up dependencies...")
    subprocess.call([gradle_exec, "setup"], cwd=path)
    print(path + " is ready")


@papertrail.command()
@click.argument('url')
@click.argument('filename')
@click.pass_obj
def deploy_url(client, url, filename):
    temp = tempfile.NamedTemporaryFile()
    download_file(url, temp.name)
    client.deploy_package(filename, temp)
    temp.close()


@papertrail.command()
@click.argument('project')
@click.option('--install', is_flag=True, default=False, help='Deploy the install package instead of the upgrade package')
@click.pass_obj
def deploy_ci(client, project, install):
    """Deploys a package by downloading the latest CircleCI artifact using ci:<user>/<repo>
    Requires the CIRCLECI environment variable be set with an access token
    """
    url = "https://circleci.com/api/v1.1/project/github/%s?circle-token=%s" % (project, os.environ['CIRCLECI']);
    build = http_get(url).json()[0]["build_num"]
    url = "https://circleci.com/api/v1.1/project/github/%s/%s/artifacts?circle-token=%s" % (project,build, os.environ['CIRCLECI']);


    for file in http_get(url).json():
        if install and file["pretty_path"].endswith("-install.zip"):
            url = file["url"]
        elif not install and file["pretty_path"].endswith("-upgrade.zip"):
            url = file["url"]

    temp = tempfile.NamedTemporaryFile(delete=False)
    download_file(url + "?circle-token=%s" % (os.environ['CIRCLECI']), temp.name)
    client.deploy_package(project + ".zip", temp)


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


@papertrail.command(name="eval")
@click.argument('code')
@click.pass_obj
def _eval(client, code):
    """Evaluates script on the server"""

    prefix = """
    import com.egis.*;
    import com.egis.kernel.*;
    import com.egis.kernel.db.*;
    import com.egis.kernel.service.*;
    import com.egis.utils.*;
    import com.egis.model.*;
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
def get(client, url, data):
    """
    Performs a generic GET request to a provided URL, optionally passing a DATA set in the 'key=value' format.

    Usage example:
    pt get dao/listFull/Group limit=1
    """
    data = {pair[0]: pair[1] for pair in map(lambda pair: pair.split('=', 1), data)}
    response = client.get(url, data)

    if response and (response.status_code >= 200 and response.status_code < 300):
        print(response.text)


@papertrail.command()
@click.argument('url', nargs=1)
@click.argument('data', nargs=-1)
@click.pass_obj
def post(client, url, data):
    """
    Performs a generic POST request to a provided URL, optionally passing a DATA set in the 'key=value' format.
    Data is encoded as application/x-www-form-urlencoded.

    Usage example:
    pt post execute/action key=value

    or to upload a file:
    pt post "action/execute/bulk_import" file=@path/to/Clients.csv node=System/clients delimiter=";" qualifier="\""
    """
    files = {}
    data = {pair[0]: pair[1] for pair in map(lambda pair: pair.split('=', 1), data)}
    for key in data:
        if data[key].startswith('@'):
            path = data[key][1:len(data[key])]
            files[key] = (path, open(path, 'rb'))



    if len(files) > 0:
        response = client.post(url, data,files=files)
    else:
        response = client.post(url, data)

    if response and (response.status_code >= 200 and response.status_code < 300):
        print(response.text)


@papertrail.command(name="service")
@click.argument('action', type=click.Choice(['start', 'stop', 'restart', 'status']))
def _service(action):
    """
    Manages a local Papertrail service.

    Use the PT_ROOT environment variable to override the default installation path.
    """
    if action == 'start':
        if service.get_status() is not None:
            click.echo("PaperTrail already started")
        else:
            if service.start():
                click.echo('\nStarted PaperTrail')
    elif action == 'stop':
        if service.stop():
            click.echo('\nStopped PaperTrail')
        else:
            click.echo('PaperTrail is not running')
    elif action == 'restart':
        service.stop()
        service.start()
    elif action == 'status':
        status = service.get_status()
        if status is not None:
            click.echo("PaperTrail started (%s)" % str(status))
        else:
            click.echo("PaperTrail not started")


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
    click.echo(client.update_document(path, file).text)


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
    click.echo(client.update_document('{}/{}'.format(node, basename(file.name)), file).text)


@papertrail.command()
@click.argument('file', type=click.File('rt'))
@click.pass_obj
def update_script(client, file):
    """Uploads and updates the script document from a provided FILE"""
    client.upload_script(basename(file.name), file)


@papertrail.command()
@click.argument('docid')
@click.option('--history', required=False, is_flag=True)
@click.pass_obj
def info(client,docid, history):
    """prints the document details"""
    if history:
        click.echo(client.get('document/history/' + docid).text)
    else:
        click.echo(client.get('document/details/' + docid).text)


@papertrail.command()
@click.argument('url')
@click.option('--open', required=False, is_flag=True, help="Open the form in a webbrowser")
@click.pass_obj
def new_token(client, url, **kwargs):
    """Generates and outputs a new token for a provided URL"""
    token=client.new_token(url)
    click.echo(token)
    if kwargs['open']:
        webbrowser.open(token);


@click.group()
def form():
    pass


papertrail.add_command(form)


@form.command()
@click.argument('form_name')
@click.option('--open', required=False, is_flag=True, help="Open the form in a webbrowser")
@click.pass_obj
def new(client, form_name, **kwargs):
    """Creates a new form from a provided FORM_NAME"""
    doc_id = client.new_form(form_name)['docId']
    token = client.new_token('/web/eSign')
    click.echo(doc_id)
    if kwargs['open']:
       webbrowser.open('{}?{}'.format(token, doc_id))


@form.command(name="export")
@click.argument('docid')
@click.pass_obj
def form_export(client, docid):
    """Creates a new form from a provided FORM_NAME"""
    click.echo(client.get('public/file/%s/saved.json?path=saved.json' % docid).text)


@form.command(name="list")
@click.pass_obj
def form_list(client):
    """Creates a new form from a provided FORM_NAME"""
    for form in json.loads(str(client.get('dao/list/Form').text)):
        click.echo(form)


@form.command()
@click.argument('form_name')
@click.option('--open', required=False, is_flag=True, help="Open the form in a browser")
@click.pass_obj
def new_classic(client, form_name, **kwargs):
    """Creates a new form from a provided FORM_NAME, using the classic UI"""
    doc_id = client.new_form(form_name)['docId']
    click.echo(doc_id)
    token = client.new_token('/jsForm/edit/')
    if kwargs['open']:
       webbrowser.open('{}?{}'.format(token, doc_id))


@papertrail.command()
@click.option('--count-only', is_flag=True, default=False)
@click.option('--since', required=False)
@click.pass_obj
def sessions(client, count_only, since):
    """Lists currently active sessions on the server."""
    sessions = client.sessions()

    if sessions is None:
        return

    if count_only:
        print(sessions['totalCount'])
        return

    print("%s %s (%s) %s" % (bgcolors.OKBLUE, client.host, sessions['totalCount'], bgcolors.ENDC))

    for item in sessions["items"]:
        if "lastAccessTime" not in item:
            continue
        if "Administrator" == item['user'] and '41.160.64.194' == item['host']:
            continue
        if "userAgent" not in item:
            item["userAgent"] = ""
        print("%s (%s - %s) - %s/%s" % (
            item['user'], item["startDate"], item['lastAccessTime'], item["host"], item["userAgent"]))
        # print "{:30s} {:20s} ({:30s}) {:10s}".format(item['user'],
        # item['startDate'], item['lastAccessTime'], item['userAgent'])


@papertrail.command()
@click.pass_obj
def tasks(client):
    client.task_list()


@papertrail.command()
@click.option('--info', is_flag=True, default=False)
@click.pass_obj
def logs(client, info):
    client.logs(info)


@papertrail.command()
@click.pass_obj
def get_backup_config(client):
    access, secret, bucket = client.get_backup_config()
    if access is not None:
        print """AWS_ACCESS_KEY_ID=%s
AWS_SECRET_ACCESS_KEY=%s
S3_BUCKET=%s""" % (access, secret, bucket)


@papertrail.command()
@click.option('--bucket', envvar=['S3_BUCKET'], required=True, help="S3 bucket nameto place backups in or use S3_BUCKET environment variable")
@click.option('--access', envvar=['AWS_ACCESS_KEY_ID'], help="S3 access key or use S3_ACCESS_KEY environment variable")
@click.option('--secret', envvar=['AWS_SECRET_ACCESS_KEY'], help="S3 secret key or use S3_SECRET_KEY environment variable")
@click.option('--schedule', default="0 20 * * * ", help="The database backup schedule to use, defaults to 8pm daily")
@click.pass_obj
def configure_backups(client, bucket, access, secret, schedule):
    client.config_backups(bucket, access, secret, schedule)


@papertrail.command()
@click.argument('entity')
@click.argument('id', required=False)
@click.pass_obj
def export(client, entity, id):
    """Exports an ENTITY or a list of entities if no ID is provided."""
    response = client.export_entity(entity, id)
    if response is not None:
        print(response)


@papertrail.command(name='import')
@click.argument('file', type=click.File('rt'))
@click.pass_obj
def _import(client, file):
    """Imports an entity from a provided FILE."""
    response = client.import_entities(file.read())
    if response is not None:
        print(response)


@papertrail.command()
@click.pass_obj
def version(client):
    import pkg_resources
    print pkg_resources.require("papertrail-cli")[0].version


def main():
   commands.init_plugins(papertrail)
   papertrail()


if __name__ == '__main__':
    papertrail()
