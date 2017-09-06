[![CircleCI](https://circleci.com/gh/egis/papertrail-python-cli.svg?style=svg)](https://circleci.com/gh/egis/papertrail-python-cli)

A command line application to interact with a PaperTrail Server

To install:

`pip install papertrail-cli`


```bash
Usage: pt [OPTIONS] COMMAND [ARGS]...

Options:
  --site TEXT      Name of the file with site credentials
  --username TEXT  or use the PT_USER/PT_API_USER environment variable
  --password TEXT  or use the PT_PASS/PT_API_PASS environment variable
  --host TEXT      or use the PT_API environment variable
  --help           Show this message and exit.

Commands:
  build              Provides development tools.
  configure_backups
  deploy             Deploys a package from a local FILE
  deploy_ci          Deploys a package by downloading the latest...
  deploy_url
  docker
  download           Downloads a remote PATH to DEST_FILE
  download_script    Downloads a remote SCRIPT to DEST_FILE
  eval               Evaluates script on the server
  execute            Executes a script FILE on the server
  export             Exports an ENTITY or a list of entities if no...
  form
  get                Performs a generic GET request to a provided...
  get_backup_config
  import             Imports an entity from a provided FILE.
  info               prints the document details
  login              Set the site credentials
  logs
  new_token          Generates and outputs a new token for a...
  post               Performs a generic POST request to a provided...
  pql                Executes a PQL query and outputs the result.
  redeploy           Redeploys workflows
  service            Manages a local Papertrail service.
  sessions           Lists currently active sessions on the...
  tasks
  test               Runs a provided Groovy script as an...
  update_doc         Updates a document located at NODE/FILE from...
  update_script      Uploads and updates the script document from...
  upgrade            Upgrades a local Papertrail installation to...
  upload             Uploads FILE to PATH.
```
