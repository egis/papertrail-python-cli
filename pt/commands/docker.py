import sh
import click
import time


@click.group('docker')
def run():
    pass


@run.command('restore')
@click.option('--name', required=True, help="The name of the Docker container")
@click.option('--bucket', required=True, help="Restore bucket")
@click.option('--access', envvar=['S3_ACCESS_KEY'], help="S3 access key or use S3_ACCESS_KEY environment variable")
@click.option('--secret', envvar=['S3_SECRET_KEY'], help="S3 secret key or use S3_SECRET_KEY environment variable")
@click.option('--lic', required=True, help="Licence")
@click.option('--swarm', is_flag=True, help="Whether to restore the container on Docker swarm cluster")
@click.pass_context
def restore(ctx, name, bucket, access, secret, lic, swarm):

    print "restoring %s" % name
    if swarm:
        state = _get_swarm_service_state(name)
        if "Running" in state:
            print "removing service %s" % name
            _delete_swarm_service(name)
    else:
        state = _get_container_state(name)
        if "Running" in state:
            # stop the container and then start it adding ENV
            print "stopping and removing %s" % name
            _stop_docker_container(name)
            _delete_docker_container(name)
        if "Stopped" in state:
            print "removing %s" % name
            _delete_docker_container(name)

    print "starting %s in wizard mode" % name
    ctx.invoke(docker_run, name=name, version="nightly", wizard=True, swarm=swarm)

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

    if swarm:
        ctx.obj.url = 'http://' + name
    response = ""
    while "Wizard" not in response:
        print "Waiting for app to respond..."
        time.sleep(10)
        try:
            r = ctx.obj.get(url="")
            response = r.text
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
@click.option('--mem', required=False, default=256)
@click.option('--image', required=False, help="An optional docker image to use")
@click.option('--debug', is_flag=True, help="Turn off auto restart of a PaperTrail instance after the update")
@click.option('--mysql', is_flag=True, help="Use a mysql database instead of PostgreSQL")
@click.option('--mssql', is_flag=True, help="Use Microsoft SQL Server on linux instead of PostgreSQL")
@click.option('--wizard', is_flag=True, help="Whether to start the conrainer in WIZARD (restore) mode")
@click.option('--swarm', is_flag=True, help="Whether to start the conrainer on Docker swarm cluster")
def docker_run(name, vhost, data, install, version, port, mem, debug, mysql, mssql, image, wizard, swarm):
    image = image
    if image is None and mysql:
        image = "egis/docker-papertrail-mysql"
    elif image is None and mssql:
        image = "egis/docker-papertrail-mssql"
    elif image is None:
        image = "egis/docker-papertrail-postgres"

    if version is None:
        version = 'stable'

    if data is None:
        data = '/opt/Data/%s' % name

    if install is None and version is None:
        print "Must specify either a version or an install path"

    if swarm:
        args = ["service", "create", "--with-registry-auth", "--network", "frontends", "--label", "ingress=true",
                "--name", name, "-e", "PORT=%s" % port, "--label", "ingress.targetport=%s" % port, "-e", "MEM=%s" % mem,
                "--mount", "type=bind,source=/opt/Data/%s,destination=/data" % name]
    else:
        args = ["run", "-d", "-i", "-e", "MEM=%s" % mem, "-e", "PORT=%s" % port, "-v",
                "%s:/data" % data, "--name=%s" % name]

    if debug:
        args = args + ["-e", "DEBUG=true"]

    if vhost is None:
        if swarm:
            args = args + ["--label", "ingress.dnsname=%s" % name]
        else:
            args = args + ["-p", "%s:%s" % (port, port)]
    else:
        if swarm:
            args = args + ["--label", "ingress.dnsname=%s" % vhost]
        args = args + ["-e", "VIRTUAL_HOST=%s" % vhost]

    if wizard:
        args = args + ["-e", "WIZARD=true"]

    if install is None:
        args = args + ["-e", "VERSION=%s" % version, image]
    else:
        if swarm:   
            args = args + ["--mount", "type=bind,source=%s,destination=/opt/install" % install, image]
        else:
            args = args + ["-v",  "%s:/opt/install" % install, image]

    _execute_docker_cmd(args, name)


def _execute_docker_cmd(args, container_name):
    docker = sh.Command("docker")
    print args
    docker(args)
    if args[0] == "service":
        print "Swarm node IP: %s" % _get_swarm_node_ip(container_name)
    else:
        print "Container IP: %s" % _get_container_ip(container_name)


def _delete_swarm_service(service_name):
    docker = sh.Command("docker")
    try:
        docker(["service", "rm", service_name])
        print "Giving docker some time to clean up"
        time.sleep(30)
    except:
        print "Something went wrong while removing %s" % service_name


def _stop_docker_container(container_name):
    docker = sh.Command("docker")
    try:
        docker("stop", container_name)
    except:
        # Container is not "present"
        print "Something went wrong while stopping %s" % container_name


def _delete_docker_container(container_name):
    docker = sh.Command("docker")
    try:
        docker("rm", container_name)
    except:
        # Container is not "present"
        print "Something went wrong while removing %s" % container_name


def _get_swarm_node_ip(container_name):
    docker = sh.Command("docker")
    state = "unknown"
    count = 0
    while state != "Running":
        print "Waiting for container deployment..."
        time.sleep(5)
        state = _get_swarm_service_state(container_name)
        count += 1
        if count == 12:
            print "Error: could not get swarm node IP"
            exit(1)
    ip = sh.awk(sh.xargs(sh.awk(sh.tail(sh.head(docker(["service", "ps", container_name]), "-2"), "-1"), "{print $4}"),
                         "host"), "{print $NF}").strip(' \t\n\r\'')
    return ip


def _get_container_ip(container_name):
    docker = sh.Command("docker")
    ip = docker("inspect", "-f", "'{{.NetworkSettings.IPAddress}}'", container_name)
    return ip.stdout.strip(' \t\n\r\'')


def _get_swarm_service_state(service_name):
    docker = sh.Command("docker")
    try:
        state = sh.awk(sh.tail(sh.head(docker(["service", "ps", service_name]), "-2"), "-1"), "{print $6}").strip(' \t\n\r\'')
    except:
        state = "Not present"
    return state


def _get_container_state(container_name):
    docker = sh.Command("docker")
    try:
        state = docker("inspect", "-f", "'{{.State.Running}}'", container_name)
    except:
        # Container is not "present"
        return "Missing"
    if state.exit_code == 0 and 'true' in state.stdout:
        return "Running"
    # Container is "present" but is not running
    return "Stopped"

