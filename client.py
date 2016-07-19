import json

from pt_lib import *
from utils import *


class Client:

    def __init__(self, url, username='admin', password=os.environ.get('ADMIN_PASS', '')):
        self.url = url.strip()
        self.name = self.url.split(".")[0].split('/')[2]
        self.host = self.name
        r = http_post(self.url + "/party/login",{"login": username, "password":password})
        self.cookie = r.cookies['JSESSIONID']
        self.username = username
        self.password = password

    def post(self, url, data, headers={}):
        headers.update({ 'csrf-token': self.cookie })
        return http_post(self.url + "/" + url, data=data, headers=headers, cookies={'JSESSIONID': self.cookie})

    def get(self, url, data=None):
        return http_get(self.url + "/" + url, data=data, cookies={'JSESSIONID': self.cookie})

    def pql_query(self, query):
        response = self.get('document/pql', { 'query': query, 'includeMetadata': True })
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

        self.update_properties(
            {'db.backup.schedule': '%s %s * * *' % (minute, hour)})
        wait(self.db_has_current_backup, 10)
        print "db backed up in " + str(start)

    def fs_backup(self):
        start = Timer()
        self.fs_sync()
        wait(self.fs_has_current_backup, 10)
        print "fs backed up in " + str(start)

    def db_has_current_backup(self,options):
        start = self.db_last_backup_time()
        if start == None:
            return False
        delta = self.server_time() - \
            dt.datetime.strptime(start, '%Y-%m-%d %H:%M')
        return delta.seconds < 60

    def fs_has_current_backup(self, options):
        start = self.fs_last_sync_time()
        if start == None:
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

    def index_rebuild(self, options):
        self.post("action/execute/index_rebuild", {"node": '*'})

    def task_list(self, options):
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

    def get_properties(self, options):
        props = {}
        for prop in self.get('property/list').json():
            props[prop['name']] = prop['value']
        return props

    def change_mode(self, mode):
        self.post('system/changeMode/%s' % mode, {})

    def new_token(self, url):
        return self.get('token/generate', data={ 'url': url })

    def update_document(self, path, contents):
        return self.post('public/file/{}'.format(path), data=contents,
                         headers={ 'Content-Type': 'application/octet-stream' })

    def upload_script(self, path, script):
        result = self.update_document('System/scripts/{}'.format(path), script)

        if result.status_code >= 200 and result.status_code < 300:
            self.redeploy_workflow()

        return result

    def redeploy_workflow(self):
        return self.post('workflow/redeploy', {},
                         headers={ 'Content-Type': 'application/octet-stream' })

    def execute(self, script):
        result = self.post('script/execute', {'code': script}).text
        print script + "=" + result
        result = result.split("=")[1]
        result = str(result).replace("\\n", "").strip()
        return result

    def sessions(self,  options):
        try:
            r = self.get('dao/listFull/UserSession?filter=%5B%7B%22value%22%3A%22%22%2C%22field%22%3A%22endDate%22%2C%22type%22%3A%22null%22%7D%5D')
            sessions = r.json()
            print "%s %s (%s) %s" % (bgcolors.OKBLUE, self.host, sessions["totalCount"], bgcolors.ENDC)
            for item in sessions["items"]:
                if "lastAccessTime" not in item:
                    continue
                if "Administrator" == item['user'] and '41.160.64.194' == item['host']:
                    continue 
                if "userAgent" not in item:
                    item["userAgent"] = ""
                print "%s (%s - %s) - %s/%s" % (
                    item['user'], item["startDate"], item['lastAccessTime'], item["host"], item["userAgent"])
                # print "{:30s} {:20s} ({:30s}) {:10s}".format(item['user'],
                # item['startDate'], item['lastAccessTime'], item['userAgent'])

        except Exception, e:
            print e

    def log(self, url, options):
        for line in self.get("logReader").json()['log'].split("<br>"):
            if not " INFO " in line:
                print line

    def ansible(self, cmd):
        ansible = Ansible(host=self.name + ".papertrail.co.za")
        return ansible.execute(cmd)

    def shutdown(self):
        self.ansible("shutdown -h now")

    def papertrail(self,  arg):
        print self.ansible('/etc/init.d/papertrail %s' % arg)

    def sql(self, url, options):
        try:
            print check_output(
                "/usr/local/bin/ansible --sudo -i %s  %s -m shell -a \"sudo -i -u postgres psql papertrail -c \\\"%s\\\"\"" %
                (self.inventory, self.host, options.arg), shell=True)
        except Exception, e:
            print self.host + str(e)

    def stop(self):
        self.papertrail("stop")

    def start(self):
        self.papertrail("start")

    def restart(self):
        self.papertrail("restart")

    def status(self):
        self.papertrail("status")

    def reset_password(self, newPassword):
        self.post("action/execute/change_password", {
            "oldPassword": self.password,
            "newPassword": newPassword,
            "confirmPassword": newPassword})

    def index_repair(self, options):
        self.post("action/execute/index_repair", {"cmd": "save"})

    def server_time(self,options):
        return dt.datetime.strptime(self.execute('com.egis.utils.DateUtils.getISO(new Date())'), '%Y-%m-%d %H:%M:%S')

    def get_store(self, name):
        stores = self.get('dao/listFull/FileStore').json()
        if (stores['totalCount'] == 0):
            return
        for store in stores["items"]:
            if store['name'] == name:
                return store

    def fs_list(self,options):
        stores = self.get('dao/list/FileStore').json()
        if (len(stores) == 0):
            return
        for store in stores["items"]:
            print store

    def fs_sync(self, threads=4):
        resp = self.post("action/execute/synchronize_stores",
                  data={"readFrom": 'Local Store', "writeTo": "Cloud Store", "threads": threads,
                        "mode": "partial-sync"})

        if resp != None:
            print(resp.text)
        else: 
            print('no response from sync method')

    def main(self, options):
        getattr(self, options.action)(options.arg)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-i", "--inventory", dest="inventory",
                      help="path to ansible inventory file")
    parser.add_option("-l", "--limit",default="papertrail",
                      dest="limit",
                      help="ansible -l option")
    parser.add_option("-a", "--arg",
                      dest="arg",
                      help="arguments")
    parser.add_option("-p", "--password",
                      dest="pwd",
                      help="PaperTrail admin password")
    parser.add_option("-t", "--action", dest="action",
                      help="an action to invoke: index_rebuild,task_list,fs_list,fs_sync,reset_password,status,restart,stop,start,log,sql,sessions,index_rebuild,index_repair,reset_password,reset_password_sql")
    parser.add_option("-s", "--ssl", action="store_true", dest="ssl")
    parser.add_option("-d", "--debug", action="store_true", dest="debug")
    (options, args) = parser.parse_args()
    if (options.debug):
        httplib.HTTPConnection.debuglevel = 1
        # You must initialize logging, otherwise you'll not see debug output.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    if (options.action == None):
        parser.print_help()
    else:

        if  options.pwd == None and "ADMIN_PASS" in os.environ:
            options.pwd = os.environ['ADMIN_PASS']

        if (options.pwd == None):
            options.pwd = raw_input("Enter Password: ")

        hosts = check_output("/usr/local/bin/ansible -i %s  %s --list-hosts" % (options.inventory, options.limit),
                             shell=True).split("\n")
        for host in hosts:
            if host == None or host == '':
                continue
            options.host = host.strip()
            try: 
                Client("https://%s" % host.strip()).main(options)
            except Exception, e:
                print_fail (host + str(e) + "\n")
        
