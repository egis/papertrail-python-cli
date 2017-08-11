import os, sys
import atexit
import csv, json

from utils import http_get

def run_pql_repl(client):
    if os.name == 'posix':
        setup_readline()

    while True:
        try :
            query = raw_input('pql> ')
            if not query or query == 'exit':
                break
        except EOFError:
            # User pressed Ctrl+D
            print('')
            break

        response = client.pql_query(query)
        if response is not None:
            print_pql_response(response)

def print_pql_csv(data):
    if 'count' in data and data['count'] == 0:
        return

    if not ('items' in data):
        raise Exception('Invalid data in response:', data)

    csvwriter = csv.writer(sys.stdout)

    # Write header
    csvwriter.writerow(map(lambda meta: meta['label'], data['metadata']))

    # Write data rows
    for row in data['items']:
        csvwriter.writerow(row)

def print_pql_json(data):
    print(json.dumps(data, indent=2))

def print_pql_response(data):
    if 'count' in data and data['count'] == 0:
        return

    """Prints response in a human-readable format"""
    if not ('items' in data):
        raise Exception('Invalid data in response:', data)

    columns = data['metadata']
    items = data['items']

    for item in items:
        for i, column in enumerate(columns):
            print(column['label'] + ": " + item[i])
        print('---')

def setup_readline():
    import readline

    histfile = os.path.join(os.path.expanduser("~"), ".pql_history")
    try:
        readline.read_history_file(histfile)
        readline.set_history_length(100)
    except FileNotFoundError:
        pass

    atexit.register(readline.write_history_file, histfile)
