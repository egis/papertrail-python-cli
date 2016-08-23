"""
Papertrail service management functions.
Unifies Linux & Windows services control.
"""

import re
import os
import sys
import subprocess
from os.path import exists

# Detect current platform
if os.name == 'posix':
    import signal
    import time
    PLATFORM = "posix"
    PT_ROOT = os.getenv("PT_ROOT", "/opt/Papertrail") # Default installation root on *nix
    PID_FILE = "%s/pid" % PT_ROOT
else:
    PLATFORM = "nt"
    PT_ROOT = os.getenv("PT_ROOT", '%s\\Papertrail' % os.getenv('ProgramFiles'))
    SERVICE_EXE = "sc.exe" # service control program on Windows
    SERVICE_NAME = "Papertrail" # from service.exe4j

def get_status():
    """
    Returns None if the service is not running and the service status depending on
    the platform (PID on POSIX and service status on Windows)
    """
    if PLATFORM == 'nt':
        query, err = subprocess.Popen([SERVICE_EXE, "query", SERVICE_NAME], stdout=subprocess.PIPE).communicate()

        state_regexp = re.compile(ur'^\s+STATE\s*:\s*(?P<num_code>\d+)\s+(?P<state>\w+)', re.MULTILINE)
        state = re.search(state_regexp, query)

        if state.group('state') == 'STOPPED':
            return None
        else:
            return '%s [%s]' % (state.group('state'), state.group('num_code'))
    else:
        return get_pid()

def get_pid():
    """Returns a PID of the currently running service or None if there's none."""
    if exists(PID_FILE):
        with open(PID_FILE, "rt") as f:
            pid = int(f.read())
            try:
                os.kill(pid, 0)
                return pid
            except OSError:
                return None
    else:
        return None

def stop():
    """Stop the running service."""
    if PLATFORM == "nt":
        return subprocess.call([SERVICE_EXE, "stop", SERVICE_NAME])
    else:
        pid = get_pid()

        if pid is None:
            return False

        try:
            os.kill(pid, signal.SIGTERM)
            sys.stdout.write('Stopping PaperTrail (%d)' % (pid))

            # Waiting for the process to stop
            while True:
                try:
                    os.kill(pid, 0)
                    break
                except OSError:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    time.sleep(1)

            os.remove(PID_FILE)

            return True
        except OSError, e:
            print(e)
            return False

def start():
    """Starts a local Papertrail service."""
    if PLATFORM == "nt":
        return subprocess.call([SERVICE_EXE, "start", SERVICE_NAME])
    else:
        if exists(PID_FILE):
            os.remove(PID_FILE)

        if not exists(PT_ROOT):
            print("No local PaperTrail installation found at %s" % (PT_ROOT))
            return False

        # Runs equivalent of a shell command `nohup ./run.sh > nohup.out 2>&1&`
        proc = subprocess.Popen(["nohup", "./run.sh"],
                                stdout=open("%s/nohup.out" % (PT_ROOT), "wt"),
                                stderr=subprocess.STDOUT,
                                cwd=PT_ROOT)

        # Wait for the process to get up
        sys.stdout.write('Starting PaperTrail')
        while True:
            if proc.poll() is not None:
                print("\nError starting PaperTrail (return code: %d).\nPlease check nohup.out for details." % (proc.returncode))
                return False
            if exists(PID_FILE):
                break
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(1)

        sys.stdout.write('\n')

        return get_pid()

def uninstall():
    """Uninstalls the local Papertrail instance"""
    stop()
    if PLATFORM == "nt":
        uninstaller = "%s\\uninstall.exe" % PT_ROOT
        if exists(uninstaller):
            subprocess.Popen([uninstaller, "-q"], stdout=subprocess.PIPE).communicate()
    else:
        uninstaller = "%s/uninstall" % PT_ROOT
        if exists(uninstaller):
            subprocess.Popen(["sh", uninstaller, "-q"], stdout=subprocess.PIPE).communicate()

def install(package):
    """Installs a new local Papertrail instance from the provided package (exe/sh)"""
    if PLATFORM == "nt":
        subprocess.Popen([package, "-q"]).communicate()
    else:
        subprocess.Popen(["sh", package, "-q"], stdout=subprocess.PIPE).communicate()

def upgrade(package):
    """Upgrades the local Papertrail instance using the provided package (exe/sh)"""
    uninstall()
    install(package)
