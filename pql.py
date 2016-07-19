import os
import atexit
import readline

from utils import http_get

def run_pql_repl(client):
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

def print_pql_response(data):
    if not ('items' in data):
        raise Exception('Invalid data in response:', data)

    columns = data['metadata']
    items = data['items']

    for item in items:
        for i, column in enumerate(columns):
            print(column['label'] + ": " + item[i])
        print('---')

def setup_readline():
    histfile = os.path.join(os.path.expanduser("~"), ".pql_history")
    try:
        readline.read_history_file(histfile)
        readline.set_history_length(100)
    except FileNotFoundError:
        pass

    atexit.register(readline.write_history_file, histfile)
