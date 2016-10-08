import os
import sh
import click

@click.command('docker')
@click.option('--name', required=True, help="The name of the docker container")
@click.option('--vhost', required=False)
@click.option('--port', required=False, default=8080)
@click.option('--data', required=False, help="The location of the PT Repo and Index, defaults to /opt/Data/<name>")
@click.option('--install', required=False, help="The location of a local instalatioon directory to use")
@click.option('--version', required=False, help="The version of papertrail to deploy, defaults to the the latest stable, e.g. nightly, stable")
@click.option('--mem', required=False, default=128)
@click.option('--image', required=False, help="An optional docker image to use")
@click.option('--debug', is_flag=True, help="Turn off auto restart of a PaperTrail instance after the update")
@click.option('--mysql', is_flag=True, help="Use a mysql database instead of PostgreSQL")
@click.option('--mssql', is_flag=True, help="Use Microsoft SQL Server on linux instead of PostgreSQL")
def run(name, vhost, data, install, version, port, mem, debug, mysql, mssql, image):
    docker = sh.Command("docker")
    IMAGE = image
    if IMAGE is None and mysql:
        IMAGE = "egis/docker-papertrail-mysql"
    elif IMAGE is None and mssql:
        IMAGE = "egis/docker-papertrail-mssql"
    elif IMAGE is None:
        IMAGE = "egis/docker-papertrail-postgres"

    if version is None:
        version = 'stable'

    if data is None:
        data = '/opt/Data/%s' % name

    if install is None and version is None:
        print "Must specify either a version or an install path"

    args = ["run", "-d", "-i", "-e", "MEM=%s" % mem, "-e", "PORT=%s" % port, "-v", "%s:/data" % data, "--name=%s" % name]

    if vhost is None:
        args = args + ["-p", "%s:%s" % (port, port)]
    else:
        args = args + ["-e", "VIRTUAL_HOST=%s" %
         vhost]

    print args

    if install is None:

        docker(args + ["-e", "VERSION=%s" % version, IMAGE])
    else:
        docker(args + ["-v",  "%s:/opt/install" % install, IMAGE])
