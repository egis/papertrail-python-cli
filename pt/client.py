import json

from utils import *


class Client:

    def __init__(self, url, username='admin', password=os.environ.get('ADMIN_PASS', '')):
        self.url = url.strip()
        self.name = self.url.split(".")[0].split('/')[2]
        self.host = self.name
        self.username = username
        self.password = password

    def post(self, url, data, headers={}, **kwargs):
        return http_post(self.url + "/" + url, data=data, headers=headers,
                         username=self.username, password=self.password, **kwargs)

    def get(self, url, data=None, **kwargs):
        return http_get(self.url + "/" + url, data=data,
                        username=self.username, password=self.password, **kwargs)

    def pql_query(self, query):
        response = self.get('document/pql', { 'query': query, 'includeMetadata': True })
        if response and response.status_code == 200:
            return response.json()

    def db_backup(self):
        start = Timer()
        now = self.server_time()
        print now
        minute = now.minute + 1
        hour = now.hour
        if minute == 60:
            hour = +1
            minute = 0

        self.update_properties({'db.backup.schedule': '%s %s * * *' % (minute, hour)})
        wait(self.db_has_current_backup, 10)
        print "db backed up in " + str(start)

    def fs_backup(self):
        start = Timer()
        self.fs_sync()
        wait(self.fs_has_current_backup, 10)
        print "fs backed up in " + str(start)

    def db_has_current_backup(self):
        start = self.db_last_backup_time()
        if start is None:
            return False
        delta = self.server_time() - \
            dt.datetime.strptime(start, '%Y-%m-%d %H:%M')
        return delta.seconds < 60

    def fs_has_current_backup(self):
        start = self.fs_last_sync_time()
        if start is None:
            return False
        delta = self.server_time() - \
            dt.datetime.strptime(start, '%Y-%m-%d %H:%M')
        return delta.seconds < 60

    def db_last_backup_time(self, options):
        return self.last_task_time('DB Backup')

    def fs_last_sync_time(self, options):
        return self.last_task_time('Storage process')

    def last_task_time(self, task):
        end = None
        tasks = self.get('tasks').json()
        for item in tasks["items"]:
            if item['name'] == task and 'end' in item:
                end = max(end, item['end'])
        if end is not None:
            print task + "=" + end
        return end

    def index_rebuild(self):
        self.post("action/execute/index_rebuild", {"node": '*'})

    def task_list(self):
        tasks = self.get('tasks').json()
        for item in tasks["items"]:
            print "{:15s} {:30s} {:10s}: {:30s} ({:10s})".format(self.name, item['name'],
                                                                 item['state'], item['status'], item['duration'])

    def update_properties(self, data):
        r = self.post('property/update', data)
        print_response(r)
        props = self.get_properties()
        for key in data:
            if data[key] != props[key]:
                raise BaseException("Property did not update: " + data[key] + "=" + props[key])

    def get_properties(self):
        return {prop['name']: prop['value'] for prop in self.get('property/list').json()}

    def change_mode(self, mode):
        self.post('system/changeMode/%s' % mode, {})

    def new_token(self, url):
        response = self.get('token/generate', data={ 'url': url })
        if response.status_code == 200:
            return response.text

    def new_form(self, form):
        response = self.post('action/execute/new_form', { 'form': form })
        if response.status_code == 200:
            return response.json()

    def update_document(self, path, contents):
        return self.post('public/file/{}'.format(path), data=contents,
                         headers={ 'Content-Type': 'application/octet-stream' })

    def upload_script(self, path, script):
        result = self.update_document('System/scripts/{}'.format(path), script)

        if 200 <= result.status_code < 300:
            self.redeploy_workflow()

        return result

    def deploy_package(self, filename, file_obj):
        """
        Deploys a binary archive package.
        """
        file_description = (filename, file_obj, 'application/octet-stream')
        return self.post('action/execute/deploy_pack', {}, files={'file': file_description})

    def redeploy_workflow(self):
        return self.post('workflow/redeploy', {},
                         headers={'Content-Type': 'application/octet-stream'})

    def export_entity(self, entity, id=None):
        if id is not None:
            params = {'id': id}
        else:
            params = {}

        response = self.get('dao/export/yml/%s' % entity, params)
        if response and response.status_code == 200:
            return response.text

    def import_entities(self, body):
        response = self.post('dao/import/yml', body,
                             headers={'Content-Type': 'text/yaml', 'Accept': '*'})
        if response and response.status_code == 200:
            return response.text

    def execute(self, script):
        result = self.post('script/execute', {'code': script}, stream=True)

        for line in result.iter_lines():

            if 'result =' in line:
                line = line.split("=")[1]
            if result.status_code == 200:
                print str(line).replace("\\n", "\n").strip()
        return ""

    def sessions(self):
        try:
            filters = [{'value': '', 'field': 'endDate', 'type': 'null'}]
            r = self.get('dao/listFull/UserSession', data={'filter': json.dumps(filters)})
            return r.json()
        except Exception, e:
            print e

    def log(self, url, options):
        for line in self.get("logReader").json()['log'].split("<br>"):
            if not " INFO " in line:
                print line

    def reset_password(self, newPassword):
        self.post("action/execute/change_password", {
            "oldPassword": self.password,
            "newPassword": newPassword,
            "confirmPassword": newPassword})

    def index_repair(self):
        self.post("action/execute/index_repair", {"cmd": "save"})

    def server_time(self):
        return dt.datetime.strptime(self.execute('com.egis.utils.DateUtils.getISO(new Date())'), '%Y-%m-%d %H:%M:%S')

    def get_store(self, name):
        stores = self.get('dao/listFull/FileStore').json()
        if stores['totalCount'] == 0:
            return
        for store in stores["items"]:
            if store['name'] == name:
                return store

    def fs_list(self):
        stores = self.get('dao/list/FileStore').json()
        if not stores:
            return
        for store in stores["items"]:
            print store

    def fs_sync(self, threads=4):
        resp = self.post("action/execute/synchronize_stores",
                         data={"readFrom": 'Local Store', "writeTo": "Cloud Store", "threads": threads,
                               "mode": "partial-sync"})

        if resp is not None:
            print(resp.text)
        else:
            print('no response from sync method')
