import sh
import click
import time

@click.group('docker')
def run():
    pass


@run.command('restore')
@click.option('--name', required=True, help="The name of the docker container")
@click.option('--bucket', required=True, help="Restore bucket")
@click.option('--access', required=True, help="Access key")
@click.option('--secret', required=True, help="Secret key")
@click.option('--lic', required=True, help="Licence")
@click.pass_context
def restore(ctx, name, bucket, access, secret, lic):

    docker = sh.Command("docker")

    print "restoring %s" % name
    state = _get_container_state(name)

    if "Running" in state:
        #stop the container and then start it adding ENV
        print "stopping and removing %s" % name
        try:
            state = docker("stop", name)
            state = docker("rm", name)
        except:
            # Container is not "present"
            print "Something went wrong while stopping and removing %s" % name

    if "Stopped" in state:
        print "removing %s" % name
        try:
            state = docker("rm", name)
        except:
            # Container is not "present"
            print "Something went wrong while removing %s" % name

    print "starting %s in wizard mode" % name
    ctx.invoke(docker_run, name=name, version="nightly", wizard=True)

    json = {
        "restart-type": "FULL",
        "restore.threads": 4,
        "property.data.dir": '/opt/Data/PT_Repo',
        "property.index.dir": '/opt/Data/PT_Index',
        "property.license": lic,
        "type": 'S3',
        "restore.bucket": bucket,
        "restore.accessKey": access,
        "restore.secretKey": secret
    }

    status_code = 0
    while  status_code != 200:
        print "Waiting for app to respond..."
        time.sleep(10)
        try:
            r = ctx.obj.get(url="")
            status_code = r.status_code
        except:
            pass

    r = ctx.obj.post(url="wizard", data=json)
    if r.status_code != 200 and r.status_code != 204:
        raise StandardError(str(r.status_code) + "=" + r.text)


@run.command('run')
@click.option('--name', required=True, help="The name of the docker container")
@click.option('--vhost', required=False)
@click.option('--port', required=False, default=8080)
@click.option('--data', required=False, help="The location of the PT Repo and Index, defaults to /opt/Data/<name>")
@click.option('--install', required=False, help="The location of a local installation directory to use")
@click.option('--version', required=False, help="The version of papertrail to deploy, defaults to the the latest stable, e.g. nightly, stable")
@click.option('--mem', required=False, default=128)
@click.option('--image', required=False, help="An optional docker image to use")
@click.option('--debug', is_flag=True, help="Turn off auto restart of a PaperTrail instance after the update")
@click.option('--mysql', is_flag=True, help="Use a mysql database instead of PostgreSQL")
@click.option('--mssql', is_flag=True, help="Use Microsoft SQL Server on linux instead of PostgreSQL")
@click.option('--wizard', is_flag=True, help="Whether to start the conrainer in WIZARD (restore) mode")
def docker_run(name, vhost, data, install, version, port, mem, debug, mysql, mssql, image, wizard):
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
        args = args + ["-e", "VIRTUAL_HOST=%s" % vhost]

    if wizard:
        args = args + ["-e", "WIZARD=true"]

    print args

    if install is None:

        docker(args + ["-e", "VERSION=%s" % version, IMAGE])
    else:
        docker(args + ["-v",  "%s:/opt/install" % install, IMAGE])



def _get_container_ip(container):
    docker = sh.Command("docker")
    ip = docker("inspect" , "-f", "'{{.NetworkSettings.IPAddress}}'", container)
    return ip.stdout.strip(' \t\n\r\'')


def _get_container_state(container):
    docker = sh.Command("docker")
    try:
        state = docker("inspect", "-f", "'{{.State.Running}}'", container)
    except:
        #Container is not "present"
        return "Missing"
    if state.exit_code == 0 and  'true' in state.stdout :
        return "Running"
    #Container is "present" but is not running
    return "Stopped"

