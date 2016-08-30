import re
import os.path
import time

import click
from termcolor import cprint
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


MAIN_METHOD = """
    public static void main(String[] args) {
        new com.egis.test.TestRunner(%s.class).run(%s);
    }
"""
def add_main_method(class_name, test_name, script_source):
    # Check if the main method already exists
    main = re.compile(r'(?:static\s+public|public\s+static)\s+void\s+main', re.IGNORECASE | re.MULTILINE)
    has_main = re.search(main, script_source)

    if has_main:
        return script_source

    i = script_source.rfind("}")
    return script_source[0:i] + MAIN_METHOD % (class_name, test_name) + "\n}"


class Tester(PatternMatchingEventHandler):
    def __init__(self, client, files, observer, test_method):
        paths = set(map(lambda f: f.name, files))
        super(Tester, self).__init__(paths)

        self.client = client
        self.files = files
        self.test_method = None

        if test_method is not None:
            self.test_method = '"%s"' % test_method
        else: 
            self.test_method = "null"

        if observer:
            dirs = set(map(os.path.dirname, paths))
            for d in dirs:
                observer.schedule(self, d)

    def on_modified(self, event):
        with open(event.src_path, 'rt') as f:
            self.run_test(f)

    def run(self):
        """Run the full suite"""
        for file in self.files:
            self.run_test(file)

    def run_test(self, file):
        test_name = os.path.splitext(os.path.basename(file.name))[0]
        cprint('Testing ' + test_name, 'cyan')

        script = file.read()
        script = add_main_method(test_name, self.test_method, script)

        print(self.client.execute(script) + '\n')


@click.command('test')
@click.argument('files', type=click.File('rt'), nargs=-1)
@click.option('--watch', '-w', is_flag=True, default=False)
@click.option('--test', '-t', help="only execute these test methods")
@click.pass_obj
def run(client, files, watch, test):
    """
    Runs a provided Groovy script as an integration test.
    """
    if not watch:
        Tester(client, files, None, test).run()
    else:
        observer = Observer()
        tester = Tester(client, files, observer, test)

        observer.start()
        tester.run()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
