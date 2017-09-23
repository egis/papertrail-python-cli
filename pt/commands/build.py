"""
Provides development tools.
"""

import sys
from os.path import basename
import os
import os.path
import datetime
import time

if os.name == 'nt':
    # Build command is not supported on Windows
    raise Exception('Warning: build command is not supported on Windows')

import click
import sh
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from termcolor import colored, cprint


quick = True
gradle = sh.Command("gradle")
ant = sh.Command("ant")
npm = sh.Command("npm")
npm_dev = npm.bake("run", "dev")

def notify(msg):
    print(msg)


class Builder(FileSystemEventHandler):
    def __init__(self, path, observer, watch):
        self.project = path
        self.path = path
        self.cwd = path
        self.cmd = None
        self.cmdp = None
        self.observer = observer

        def out(line):
            sys.stdout.write(colored(self.project, 'blue') + " " + line)
        self.out = out

        if watch:
            cprint('\nWatching ' + type(self).__name__ + " " + path, 'cyan')
            self.watch()
        else:
            cprint('\nBuilding ' + type(self).__name__ + " " + path, 'cyan')
            self.full()

    def build(self, path):
        if self.cmd is not None:
            self.cmd(_out=self.out, _cwd=self.cwd)
        if self.cmdp is not None:
            self.cmdp(path, _out=self.out, _cwd=self.cwd)

    def on_any_event(self, event):
        path = event.src_path
        if event.event_type == "deleted" or not os.path.isfile(path):
            return
        print(event.event_type + " " + path)
        start = datetime.datetime.now().replace(microsecond=0)
        try:
            self.build(path)
            cprint("Completed in %s " %
                   (datetime.datetime.now().replace(microsecond=0) - start), 'green')
        except Exception, e:
            cprint(e.stderr, 'red')
            print(notify(e.stderr))

class Gulp(Builder):
    def full(self):
        npm("run", "build", _cwd=self.cwd, _bg=True, _out=self.out)
        return self

    def watch(self):
        npm_dev(_cwd=self.cwd, _bg=True, _out=self.out)
        return self


class Java(Builder):
    def __init__(self, path, observer, watch):
        super(Java, self).__init__(path, observer, watch)

        if os.path.isdir(path + "/api"):
            observer.schedule(self, path + "/api", recursive=True)
        if os.path.isdir(path + "/src"):
            observer.schedule(self, path + "/src", recursive=True)
        if os.path.isdir(path + "/test"):
            observer.schedule(self, path + "/test", recursive=True)

    def full(self):
        pass


class Gradle(Java):
    def watch(self):
        self.cmd = gradle.bake("classes", "apiClasses", "testClasses", "--info")

    def full(self):
        gradle("jar", _out=self.out, _cwd=self.cwd)


class Ant(Java):
    def watch(self):
        self.cmd = ant.bake("compile")

    def full(self):
        if "jar" in ant("-p", _cwd=self.cwd):
            ant("jar", _out=self.out, _cwd=self.cwd)


class PaperTrail(Builder):
    def __init__(self, client, path, observer, watch):
        super(PaperTrail, self).__init__(path, observer, watch)
        self.client = client

    def build(self, path):
        print path
        with open(path, 'rt') as script:
            self.client.upload_script(basename(path), script.read())

    def watch(self):
        path = self.path + "/System/scripts"
        if os.path.isdir(path):
            self.out("Watching %s" % path)
            self.observer.schedule(self, path, recursive=True)

    def full(self):
        if os.path.isdir(self.path + "/System/scripts"):
            for p in os.listdir(self.path + "/System/scripts"):
                self.cmd(p, _cwd=self.cwd)


@click.command('build')
@click.option('--watch', '-w', is_flag=True, default=False)
@click.argument('dirs', nargs=-1, required=False)
@click.pass_obj
def run(client, watch, dirs):
    """
    Provides development tools.

    Watches the source code directory for changes and automatically rebuilds the project.
    """
    observer = Observer()

    if not dirs:
        dirs = os.listdir('.')

    dirs.append(os.getcwd())
    for path in dirs:
        if not os.path.isdir(path):
            continue

        path = os.path.realpath(path)

        for p in ["/resources", "/configs"]:
            if os.path.isdir(path + p):
                builder = PaperTrail(client, path + p, observer, watch)

        if os.path.isfile(path + "/package.json"):
            builder = Gulp(path, observer, watch)

        if os.path.isfile(path + "/build.xml"):
            builder = Ant(path, observer, watch)
        elif os.path.isfile(path + "/build.gradle"):
            builder = Gradle(path, observer, watch)


    observer.start()
    notify("Started")
    cprint('Startup complete', 'green')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
