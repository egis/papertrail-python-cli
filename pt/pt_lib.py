import hashlib
import random
import string

from utils import *


class Instance:

    def __init__(self, name, ip):
        self.name = name.split(".")[0]
        self.ip = ip

        if ip.startswith('10.'):
            self.public_ip = "197.97.77.%s" % ip.split(".")[3]
            self.ansible = Ansible(host=self.public_ip, hostname=self.name)
        else:
            self.public_ip = ip
            self.ansible = Ansible(host=self.public_ip, hostname=self.name, remote_user='ubuntu', private_key_file=os.environ['AWS_SSH_KEY'])
        self.bucket = "%s.papertrail" % name
        self.dns = "%s.papertrail.co.za" % name
        self.access_key = None
        self.secret_key = None
        self.encrypt_key = None
        print "%s -> %s " % (name, self.public_ip)


    def generate_license(self, users='5', edition='Standard'):
        self.license = License().generate(
            self.name, users=users, edition=edition)

    def generate_keys(self, iam):
        (self.access_key, self.secret_key) = iam.create_keys(
            self.bucket, self.bucket)

    def add_dns(self, dns):
        dns.create_entry(self.public_ip, self.name)

    def resize(self, size):
        sectors = int(self.ansible.execute('cat /sys/block/sda/size'))
        block_size = int(
            self.ansible.execute('cat /sys/block/sda/queue/logical_block_size'))
        bytes = sectors * block_size / 1024 / 1024
        swap = 4 * 1024
        root = bytes - swap

        self.ansible.execute(
            "parted -s -a optimal /dev/sda rm 1 rm 2 mkpart primary 1 %s mkpart primart 2 %s %s" % (root,swap))
        fstab = """
# <file system> <mount point>   <type>  <options>       <dump>  <pass>

/dev/sda1 		/               ext4    errors=remount-ro 0       1
/dev/sda2 		none            swap    sw              0       0
"""

        self.ansible.execute(" echo '%s' > /etc/fstab" % fstab)
        self.ansible.execute("shutdown -r now")
        self.wait_for(22)
        self.ansible.execute("resize2fs /dev/sda1")
        self.ansible.execute("df -h")

    def get_ansible_host_config(self):
        return "%s hostname=%s.papertrail.co.za\n" % (self.public_ip, self.name)

    def wait_for(self, port=80):
        while True:
            if ping(self.public_ip, port):
                break
            time.sleep(5)

    def deploy(self, version=None, async=False):
    	self.ansible.deploy(version,async)


    def install_encryption_key(self):
        print_info("[%s] installing encryption key\n" % self.name)
        length = 13
        chars = string.ascii_letters + string.digits + '!@#$%^&*()'
        random.seed()

        self.encrypt_key = ''.join(random.choice(chars) for i in range(length))
        text = """
keystore.password=%s
storage.encrypt=true
keystore.backup=true
""" % self.encrypt_key
        self.ansible.execute("mkdir -p /opt/Papertrail/conf")
        self.ansible.copy(text, "/opt/Papertrail/conf/encrypt.properties")

    def get_json(self):
        return {
            "restart-type": "FULL",
            "backup-type": "S3",
            "restore.threads": 4,
            "property.data.dir": '/opt/Data/PT_Repo',
            "property.index.dir": '/opt/Data/PT_Index',
            "property.license": self.license,
            "type": 'S3',
            "bucket": self.bucket,
            "accessKey": self.access_key,
            "secretKey": self.secret_key
        }

    def restore(self):
        start = Timer()
        json = {
            "restart-type": "FULL",
            "restore.threads": 4,
            "property.data.dir": '/opt/Data/PT_Repo',
            "property.index.dir": '/opt/Data/PT_Index',
            "property.license": self.license,
            "type": 'S3',
            "restore.bucket": self.bucket,
            "restore.accessKey": self.access_key,
            "restore.secretKey": self.secret_key
        }
        print "restoring %s" % self.name
        self.wizard(json)
        print "restored %s in %s" % (self.name, start)

    def wizard(self, json):
        r = http_post("http://%s/wizard" % self.public_ip, data=json)
        
        if (r.status_code != 200 and r.status_code != 204):
            raise StandardError(str(r.status_code) + "=" + r.text)


    def install(self):
        start = Timer()
        json = {
            "restart-type": "FULL",
            "property.data.dir": '/opt/Data/PT_Repo',
            "property.index.dir": '/opt/Data/PT_Index',
            "property.license": self.license
        }

        if self.access_key != None:
            json.update({
                "backup-type": "S3",
                "properties.bucket": self.bucket,
                "properties.accessKey": self.access_key,
                "properties.secretKey": self.secret_key
            })

            print "installing prod instance: %s" % self.name
        else:
            print "installing test instance %s" % self.name
        self.wizard(json)
        print "installed %s in %s" % (self.name, start)


class License:

    def generate(self, host, edition='Standard', users='5'):
        md5 = hashlib.md5("%s.papertrail.co.za%s%s%sBev1k2Sh3" %
                          (host, 'PaperTrail Cloud', users, edition)).hexdigest()
        return "%s.papertrail.co.za#%s#%s#%s#%s" % (host, 'PaperTrail Cloud', users, edition, md5[0:8])


class Ansible:

    def __init__(self, host=None, hostname=None, cloud='egis-cloud', remote_user=None, private_key_file=None):
        self.cloud = cloud
        self.host = host
        self.hostname = hostname
        self.remote_user=remote_user
        self.private_key_file=private_key_file
        print "%s hostname=%s" % (host, hostname)


    def copy(self, text, to):
        args = {

            "dest": to,
            "content": text
        }
        runner = ansible.runner.Runner(
            module_name='copy',
            sudo=True,
            complex_args=args,
            inventory=ansible.inventory.Inventory([self.host]))

        results = runner.run()
        for (hostname, result) in results['contacted'].items():
            if not 'failed' in result:
                print_ok(hostname + "= " + str(result['changed']) + "\n")
            else:
                print_fail(hostname + "= " + str(result) + "\n")

    def execute(self, command):
        print_info("[%s] ssh %s " % (self.host, command))
        runner = ansible.runner.Runner(
            module_name='shell',
            pattern='*',
            sudo=True,
            module_args=command,
            inventory=ansible.inventory.Inventory([self.host]))
        results = runner.run()
        for (hostname, result) in results['contacted'].items():
            if not 'failed' in result:
            	print_ok ("= " + result['stdout'] + "\n")
            else:
            	print_fail ("= " +result['stdout'] + "\n")
            return result['stdout']

    def base(self):        
         ansible_playbook('playbooks/base.yml', self.host, self.hostname, remote_user=self.remote_user, private_key_file=self.private_key_file)

    def deploy(self, version='stable', async=False): 
        self.base()
        if version == None:
            version = 'stable'
        print "installing papertrail %s" % version
        ansible_playbook('playbooks/papertrail.yml', self.host, self.hostname, {'papertrail_version': version}, 'papertrail',remote_user=self.remote_user, private_key_file=self.private_key_file)

