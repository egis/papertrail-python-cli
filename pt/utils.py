from subprocess import *
import subprocess
from socket import *
import time
import os, os.path
import datetime as dt
import threading
import sys

class Timer:

    def __init__(self):
        self.start = dt.datetime.now()

    def __str__(self):
        return str(dt.datetime.now() - self.start)

    def __repr__(self):
        return str(dt.datetime.now() - self.start)


class bgcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


def print_info(str):
    sys.stderr.write(bgcolors.HEADER + str + bgcolors.ENDC)


def print_ok(str):
    sys.stderr.write(bgcolors.OKGREEN + str + bgcolors.ENDC)

def print_fail(str):
    sys.stderr.write(bgcolors.FAIL + str + bgcolors.ENDC)

def load_site_config(site):
    path = None

    for root, dirs, files in os.walk('.'):
        if site in files:
            path = os.path.join(root, site)

    if path is None:
        return None

    env, error = subprocess.Popen(['/bin/bash', '-c', 'source %s && env -0' % path], stdout=subprocess.PIPE).communicate()
    return {val[0]: val[1] for val in map(lambda line: line.split('=', 1), env.split('\0')) if len(val) == 2}


def download_file(url, local_filename):
    # NOTE the stream=True parameter
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
           if chunk: # filter out keep-alive new chunks
               f.write(chunk)
               #f.flush() commented by recommendation from J.F.Sebastian
    return local_filename


def execute(command, async=False,  env=os.environ):
    print_info("executing ")
    print command

    p = Popen(command, stdout=subprocess.PIPE, shell=True, env=os.environ)
    if async:
        call_async(print_process_result, [p, command])
    else:
        return print_process_result(p, command)

def ansible_playbook(playbook, host,hostname,extra_vars=None,group=None,private_key_file=None,remote_user=None):
    print "running play %s on %s" % (playbook, host)
    stats = callbacks.AggregateStats()
    playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
    runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)
    inventory = ansible.inventory.Inventory([host])
    inventory.get_host(host).set_variable('hostname', hostname)
    inventory.set_playbook_basedir('egis-cloud')
    if group != None:
        print 'adding ' + group
        _group = ansible.inventory.Group(name=group)
        _group.add_host(inventory.get_host(host))
        inventory.add_group(_group)
    pb = ansible.playbook.PlayBook(
        playbook=playbook,
        inventory=inventory,
        callbacks=playbook_cb,
        runner_callbacks=runner_cb,
        stats=stats,
        extra_vars=extra_vars
    )

    if private_key_file != None:
        pb.private_key_file = private_key_file
    if remote_user != None:
        pb.remote_user = remote_user

    pb.run()



def wait(condition, sleep=1):
    result = condition()
    while result == False:
        result = condition()
        time.sleep(sleep)

def async(func, args):
    t = threading.Thread(target=func,args=args)
    t.daemon = True
    t.start()

    def null(args):
        pass

    return null
