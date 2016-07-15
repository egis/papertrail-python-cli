from utils import http_get

def print_pql_response(data):
    if not ('items' in data):
        raise Exception('Invalid data in response:', data)

    columns = data['metadata']
    items = data['items']

    for item in items:
        for i, column in enumerate(columns):
            print(column['label'] + ": " + item[i])
        print('---')
