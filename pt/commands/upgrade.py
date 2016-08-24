import os

import click

import pt.version as ver
import pt.service as service


INSTALLER_OUTPUT = '/opt/Papertrail.sh' if os.name == 'posix' else os.getenv('APPDATA') + '\\Papertrail.exe'


@click.command('upgrade')
@click.argument('version', required=False)
@click.option('--norestart', is_flag=True, help="Turn off auto restart of a Papertrail instance after the update")
@click.option('--output', '-o', default=INSTALLER_OUTPUT, help="Destination file for the upgrade package")
def run(version, norestart, output):
    """
    Upgrades a local Papertrail installation to the latest available version.

    Special version identifiers are: stable, nightly, stable-nightly.
    Default version is "stable".
    """
    if version in [None, ver.STABLE, ver.NIGHTLY, ver.STABLE_NIGHTLY]:
        build = ver.get_build(version)
    else:
        build = version

    # Check if the local instance needs to be upgraded
    if build == ver.get_local_version():
        click.echo('You are running the latest version of Papertrail (%s).' % (build))
        return

    # Download the build
    click.echo('Downloading version %s' % (build))
    ver.download(build, output)

    # Unpack and install the downloaded package
    click.echo('Upgrading')
    service.upgrade(output)

    ver.store_local_version(build)

    if not norestart:
        service.start()
