
import sys
import pkgutil
import importlib

import click
from commons import *

def init_plugins(group):
    """Imports extra commands from modules to a provided click command group."""
    package = sys.modules[__name__]

    for (importer, module_name, ispkg) in pkgutil.iter_modules(package.__path__):
        if not ispkg:
            try:
                module = importlib.import_module(package.__name__ + '.' + module_name)

                if 'run' not in module.__dict__:
                    print_fail('Plugin command "%s" doesn\'t provide a "run" method. Aborting.' % (module_name))
                    # sys.exit(-1)
                else:
                    group.add_command(module.run)
            except Exception, e:
                print_fail('[%s] %s' % (module_name, str(e) + str(type(e))))
