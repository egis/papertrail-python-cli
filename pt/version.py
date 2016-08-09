"""
Gets version information from the Papertrail S3 bucket and
handles downloads of upgrade packages.
"""

import requests
import progressbar

S3_BUCKET = "https://s3.amazonaws.com/papertrail"

STABLE = "stable"
NIGHTLY = "nightly"
STABLE_NIGHTLY = "stable_nightly"

def download(build, output):
    """Downloads a specific version of the Papertrail installation package."""
    url = (S3_BUCKET + "/public/nightly/build/Papertrail_%s.sh") % (build)

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

    r.close()

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
