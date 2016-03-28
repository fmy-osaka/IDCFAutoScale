#!/usr/bin/python
# -*- coding: utf-8 -*-

import os,sys
import time
import paramiko
import ConfigParser
from idcf.compute import Compute

API_CONF_PATH = os.path.join(os.path.expanduser("~"),".idcfrc")

def format_time(unix_time):
    return time.ctime(unix_time)

def safe_option(config, section, option):
    retval = config.get(section, option)
    if retval:
        return retval
    else:
        raise Exception, "Please set [%s] as [%s]. " % (option,section)

def read_config(api_config_path):

    config = ConfigParser.SafeConfigParser()
    config.read(api_config_path)

    try:
        settings = dict(
            mon_host = safe_option(config,"monitoring", "host"),
            user_name = safe_option(config,"monitoring", "user"),
            private_key_path = safe_option(config,"monitoring", "private_key_path"),
            pass_phrase = safe_option(config,"monitoring", "pass_phrase"),
            serviceofferingid = safe_option(config,"launch_config", "serviceofferingid"),
            templateid = safe_option(config,"launch_config", "templateid"),
            zoneid = safe_option(config,"launch_config", "zoneid"),

            min_size = int(safe_option(config,"scalling", "min_size")),
            max_size = int(safe_option(config,"scalling", "max_size")),
            load_balancer = safe_option(config,"scalling", "load_balancer"),

            threshold_out = float(safe_option(config,"scalling_policy_out", "threshold")),

            threshold_in = float(safe_option(config,"scalling_policy_in", "threshold")),
        )
        return settings
    except Exception, e:
        print >> sys.stderr, e
        sys.exit(1)

class Scale(object):
    def __init__(self,compute,settings):
        self.compute = compute
        self.settings = settings

    def time(self):
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def create_ssl_client(self):
        try:
            config = paramiko.config.SSHConfig()
        except Exception:
            raise

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        private_key_path = os.path.expanduser(self.settings['private_key_path'])
        mkey = paramiko.RSAKey.from_private_key_file(private_key_path,self.settings['pass_phrase'])
        client.connect(self.settings['mon_host'], port=22, username=self.settings['user_name'], pkey=mkey)
        return client

    def queryJobStatus(self,jobid):
        retval = self.compute.queryAsyncJobResult(jobid=jobid)
        print "%s query job        : jobid: %s, jobstatus: %s" % (self.time(), jobid,retval.jobstatus)
        if retval.jobstatus == 1:
            return True
        else:
            return False

    def deploy(self):
        vm_count = len(self.compute.listLoadBalancerRuleInstances(id=self.settings['load_balancer']))
        if vm_count >= self.settings['max_size']:
            return
        print "%s vm count         : now %d, max %d" % (self.time(), vm_count, self.settings['max_size'])
        print "%s scale out        : +1" % self.time()

        retval = self.compute.deployVirtualMachine(
            serviceofferingid=self.settings['serviceofferingid'],
            templateid=self.settings['templateid'],
            zoneid=self.settings['zoneid']
            )

        vm_id = retval.id
        jobid = retval.jobid

        self.compute.assignToLoadBalancerRule(id=self.settings['load_balancer'],
                                              virtualmachineids=vm_id)
        while True:
            if self.queryJobStatus(jobid):
                vm_count = len(self.compute.listLoadBalancerRuleInstances(id=self.settings['load_balancer']))
                print "%s now vm count    : %d" % (self.time(), vm_count)
                return vm_id
            time.sleep(10)

    def destroy(self):
        vms = self.compute.listLoadBalancerRuleInstances(id=self.settings['load_balancer'])
        vm_count = len(vms)
        if vm_count <= self.settings['min_size']:
            return None
        print "%s vm count         : now %d, min %d" % (self.time(), vm_count, self.settings['min_size'])
        print "%s scale in         : -1" % self.time()

        vm_ids = [vm.id for vm in vms]
        mon_vm = self.compute.listVirtualMachines(name=self.settings['mon_host'])[0].id
        vm_ids.remove(mon_vm)
        vm_id = vm_ids[-1]
        print "%s vm destorying    : %s" % (self.time(), vm_id)
        retval = self.compute.destroyVirtualMachine(id=vm_id)
        vm_count = len(self.compute.listLoadBalancerRuleInstances(id=self.settings['load_balancer']))
        return vm_id

    def scale_out(self,average):
        print "%s *** scale out check ***" % self.time()
        print "%s la_threshold_out : %d" % (self.time(), self.settings['threshold_out'])
        print "%s now_la           : %d" % (self.time(), average)
        vm_count = len(self.compute.listLoadBalancerRuleInstances(id=self.settings['load_balancer']))
        print "%s now_vm_count     : %d" % (self.time(), vm_count)

        if average > self.settings['threshold_out'] or vm_count < self.settings['min_size']:
            vm_id = self.deploy()
            return vm_id

    def scale_in(self,average):
        print "%s *** scale in check ***" % self.time()
        print "%s la_threshold_in  : %d" % (self.time(), self.settings['threshold_in'])
        print "%s now_la           : %d" % (self.time(), average)
        vm_count = len(self.compute.listLoadBalancerRuleInstances(id=self.settings['load_balancer']))
        print "%s now_vm_count     : %d" % (self.time(), vm_count)

        if average < self.settings['threshold_in']:
            vm_id = self.destroy()
            return vm_id

    def start(self):
        client = self.create_ssl_client()
        transport = client.get_transport()
        transport.set_keepalive(30)

        data = ''
        channel = transport.open_session()
        channel.exec_command('uptime')
        data += channel.recv(1024)
        loadavg = [float(x) for x in data.rsplit('load average: ', 1)[1].split(', ')]
        avg = loadavg[0]
        self.scale_out(avg)

        data = ''
        channel = transport.open_session()
        channel.exec_command('uptime')
        data += channel.recv(1024)
        loadavg = [float(x) for x in data.rsplit('load average: ', 1)[1].split(', ')]
        avg = loadavg[0]
        self.scale_in(avg)

        exit(0)

if __name__ == '__main__':

    settings = read_config(API_CONF_PATH)

    compute = Compute()

    scale = Scale(compute,settings)
    scale.start()

