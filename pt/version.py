"""
Gets version information from the Papertrail S3 bucket and
handles downloads of upgrade packages.
"""

import os
from os.path import exists

import requests
import progressbar

S3_BUCKET = "https://s3.amazonaws.com/papertrail"

STABLE = "stable"
NIGHTLY = "nightly"
STABLE_NIGHTLY = "stable_nightly"

LOCAL_VERSION_PATH = "/opt/latestBuildNo" if os.name == "posix" else "%s\\latestBuildNo" % (os.getenv('APPDATA'))
INSTALLER_EXTENSION = "sh" if os.name == "posix" else "exe"

def get_local_version():
    """Returns a version of the local Papertrail instance, if it's installed"""
    if exists(LOCAL_VERSION_PATH):
        return open(LOCAL_VERSION_PATH).read()

def store_local_version(build):
    """Stores a currently installed version"""
    with open(LOCAL_VERSION_PATH, 'w') as f:
        f.write(build)

def download(build, output, extension = INSTALLER_EXTENSION):
    """Downloads a specific version of the Papertrail installation package."""
    url = (S3_BUCKET + "/public/nightly/build/Papertrail_%s.%s") % (build, extension)
    print(url)

    response = requests.get(url, stream=True)
    size = response.headers['content-length']

    with open(output, 'wb') as f:
        progress = progressbar.ProgressBar(max_value=int(size),
                                           widgets = [ progressbar.DataSize(), progressbar.Bar(), ' ',
                                                       progressbar.FileTransferSpeed(), ' | ',
                                                       progressbar.Timer(), ', ',
                                                       progressbar.ETA() ])
        nbytes = 0

        for chunk in response.iter_content(4096):
            if chunk:
                nbytes += len(chunk)

                progress.update(nbytes)
                f.write(chunk)

    response.close()

def get_build(version_identifier):
    """Retrieves a build and version number."""
    if version_identifier is None or version_identifier == STABLE:
        url = S3_BUCKET + "/public/stable_build_no"
    elif version_identifier == NIGHTLY:
        url = S3_BUCKET + "/public/nightly/latestBuildNo"
    elif version_identifier == STABLE_NIGHTLY:
        url = S3_BUCKET + "/public/nightly/latestStableBuildNo"

    response = requests.get(url)

    return response.text.replace("\n", "").replace(" ", "").strip()
