
import sys
import pkgutil
import importlib

import click

def init_plugins(group):
    """Imports extra commands from modules to a provided click command group."""
    package = sys.modules[__name__]

    for (importer, module_name, ispkg) in pkgutil.iter_modules(package.__path__):
        if not ispkg:
            module = importlib.import_module(package.__name__ + '.' + module_name)

            if 'run' not in module.__dict__:
                print('Plugin command %s doesn\'t provide "run" method. Aborting.' % (module_name))
                sys.exit(-1)

            cmd = click.Command(name=module_name, help=module.__doc__, callback=module.run)

            group.add_command(cmd)
