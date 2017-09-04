import json
import urlparse
from dns import resolver
from commons import *


class Client:

    def __init__(self, url, username='admin', password=None):
        if password is None:
            password = os.environ.get('ADMIN_PASS')
        self.url = url.strip()
        self.name = self.url.split(".")[0].split('/')[2]
        self.host = self.name
        self.username = username
        self.password = password

    def post(self, url, data, headers={}, **kwargs):
        return http_post(self.url + "/" + url, data=data, headers=headers,
                         username=self.username, password=self.password, **kwargs)

    def get(self, url, params=None, **kwargs):
        return http_get(self.url + "/" + url, username=self.username, password=self.password, params=params, **kwargs)

    def pql_query(self, query):
        response = self.get('document/pql', { 'query': query, 'includeMetadata': True })
        if response and response.status_code == 200:
            return response.json()

    def task_list(self, options):
        tasks = json.loads(self.get('tasks'))
        for item in tasks["items"]:
            print "{:15s} {:30s} {:10s}: {:30s} ({:10s})".format(self.name, item['name'],
                                                                 item['state'], item['status'], item['duration'])

    def ping(self, port=443):
        host = urlparse.urlparse(self.url).netloc.split(":")[0]
        records = resolver.query(host, 'A')
        if len(records) is 0:
            return False
        return ping(records[0].address, port)

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

    def get_s3_backup(self,access, secret, bucket, license=None):
        print_info(" Getting last S3 backup ..")
        from boto.s3.connection import S3Connection
        s3 = S3Connection(is_secure=False, aws_access_key_id=access,aws_secret_access_key=secret)
        _bucket = s3.get_bucket(bucket,validate=False)
        max = None
        for key in _bucket.list(prefix='db2'):
            if not ".zip" in key.name:
                continue
            if max is None or max.last_modified < key.last_modified:
                max = key
        return max

    def fs_backup(self):
        start = Timer()
        self.fs_sync()
        wait(self.fs_has_current_backup, 10)
        print "fs backed up in " + str(start)

    def db_backup_age(self):
        start = self.db_last_backup_time()
        if start is None:
            return False
        return self.server_time() - \
            dt.datetime.strptime(start, '%Y-%m-%d %H:%M')

    def db_has_current_backup(self):
        return self.db_backup_age().seconds < 60

    def fs_has_current_backup(self):
        start = self.fs_last_sync_time()
        if start is None:
            return False
        delta = self.server_time() - \
            dt.datetime.strptime(start, '%Y-%m-%d %H:%M')
        return delta.seconds < 60

    def db_last_backup_time(self, options=None):
        return self.last_task_time('DB Backup')

    def fs_last_sync_time(self, options=None):
        return self.last_task_time('Storage process')

    def get_backup_config(self):
        try:
            r = self.get('dao/listFull/FileStore')
            if r is None:
                return (None,None,None)
            stores = r.json()
            if "totalCount" not in stores:
                return (None,None,None)
            if (stores['totalCount'] == 0):
                return (None,None,None)
            for store in stores["items"]:
                if store["type"] == "S3":
                    return store['properties']['accessKey'], store['properties']['secretKey'], store['properties']['bucket']
        except:
            pass
        return (None,None,None)

    def get_server_name(self):
        return self.execute("import com.egis.utils.*; Utils.hostname()")

    def configure_backups(self, bucket, access, secret, schedule):
        print_info("Configuring backups to %s using %s\n" % (bucket, access))
        server = self.get_server_name()
        self.post('dao/create/FileStore', {
            'name': 'Local Store',
            'storeOrder': 0,
            'server': server,
            'type': 'File',
            'properties.async': 'false',
            'properties.dir': '/opt/Data/PT_Repo'
        })

        self.post('dao/create/FileStore', {
            'name': 'Cloud Store',
            'storeOrder': 1,
            'server': server,
            'type': 'S3',
            'properties.secretKey': secret,
            'properties.async': 'true',
            'properties.accessKey': access,
            'properties.bucket': bucket,
            'properties.worm': 'true'
        })
        self.update_properties({'db.backup.schedule': schedule})

    def update_file_store(self, bucket, access, secret, name='Cloud Store'):
        storeId=None
        for store in self.get('dao/listFull/FileStore').json()["items"]:
            if store["name"] == name:
                storeId = store["fileStoreId"]

        if storeId is None:
            print_fail("Could not find file store using: %s" % name)
            return
        print_info("Updating backups to %s using %s .. " % (bucket, access))
        server = self.get_server_name()
        self.post('dao/update/FileStore/%s' % storeId, {
            'name': 'Cloud Store',
            'storeOrder': 1,
            'server': server,
            'type': 'S3',
            'properties.secretKey': secret,
            'properties.async': 'true',
            'properties.accessKey': access,
            'properties.bucket': bucket,
            'properties.worm': 'true'
        })

    def get_last_task(self, task):
        end = None
        tasks = self.get('tasks').json()
        for item in tasks["items"]:
            if item['name'] == task and 'end' in item:
                return self.server_time() - dt.datetime.strptime(item["end"],'%Y-%m-%d %H:%M'), item["status"], item["state"]
        return  (None,None,None)

    def last_task_time(self, task):
        end = None
        tasks = self.get('tasks').json()
        for item in tasks["items"]:
            if item['name'] == task and 'end' in item:
                end = max(end, item['end'])
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
        result = self.post('script/execute', {'code': script},)
        text = result.text
        return text.replace("\\n", "\n").replace('result =' , '').strip()

    def sessions(self):
        try:
            filters = [{'value': '', 'field': 'endDate', 'type': 'null'}]
            r = self.get('dao/listFull/UserSession', data={'filter': json.dumps(filters)})
            return r.json()
        except Exception, e:
            print e

    def logs(self, info=True):
        for line in self.get("logReader").text.split("<br>"):
            if info or not " INFO " in line:
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
