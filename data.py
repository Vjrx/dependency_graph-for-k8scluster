import json
import kubernetes
import subprocess
import re
from kubernetes import client, config

dict_total = {}

def pull_data(namespace):
    dict_app = {}
    dict_app[namespace] = []
    dict_depl = {}
    dict_rs = {}
    dict_ds = {}
    dict_pod = {}
    dict_ds_ser = {}
    dict_ds_pod = {}
    dict_dep_ser = {}
    deployment_list = subprocess.getoutput("kubectl get deployments -n {0}|cut -d ' ' -f 1".format(namespace))
    deployment_list = deployment_list.split('\n')[1:]
    for deploy in deployment_list:
        req_data = {}
        deployment_data = subprocess.getoutput("kubectl get deployments {0} -n {1} -o json".format(deploy, namespace))
        deployment_data = json.loads(deployment_data)
       
        try:
            dict_app[namespace].append(deployment_data.get('spec').get('template').get('metadata').get('labels').get('application'))
            application = deployment_data.get('spec').get('template').get('metadata').get('labels').get('application')
        except:
            dict_app[namespace].append(deployment_data.get('metadata').get('labels').get('application'))
            application = deployment_data.get('metadata').get('labels').get('application')
        
        name = deployment_data.get('metadata').get('name')

        if application in dict_depl.keys():
            dict_depl[application].append(name)
        else:
            dict_depl[application] = [name]

        try:
            dep_services = deployment_data.get('spec').get('template').get('spec').get('initContainers')[0].get('env')
            if dep_services == None:
                dep_services = []
        except Exception as var:
            dep_services = []

        for item in dep_services:
            if item.get("name") == "DEPENDENCY_SERVICE":
                dep_services = item.get("value").split(',') if item.get("value") else None
                dict_dep_ser[name] = dep_services
            elif item.get("name") == "DEPENDENCY_JOBS":
                dep_jobs = item.get("value").split(',') if item.get("value") else None

        replicaset = subprocess.getoutput("kubectl get rs -n {1} | grep {0} | cut -d ' ' -f 1".format(name, namespace)).split('\n')
        replicaset = [x for x in replicaset if x]
        dict_rs[name] = replicaset
        for rset in replicaset:
            pods = subprocess.getoutput("kubectl get po -n {1} | grep {0} | cut -d ' ' -f 1".format(rset, namespace)).split('\n')
            pods = [x for x in pods if x]
            dict_pod[rset] = pods

    ds_list = subprocess.getoutput("kubectl get ds -n {0}|cut -d ' ' -f 1".format(namespace))
    ds_list = ds_list.split('\n')[1:]

    for ds in ds_list:
       ds_data = subprocess.getoutput("kubectl get ds {0} -n {1} -o json".format(ds, namespace))
       ds_data = json.loads(ds_data)

       try:
           application = ds_data.get('spec').get('template').get('metadata').get('labels').get('application')
       except:
           application = ds_data.get('metadata').get('labels').get('application')

       name = ds_data.get('metadata').get('name')

       if application in dict_ds.keys():
           dict_ds[application].append(name)
       else:
           dict_ds[application] = [name]

       try:
           dependency_services = ds_data.get('spec').get('template').get('spec').get('initContainers')[0].get('env')
           if dependency_services == None:
                dependency_services = []
       except:
           dependency_services = []

       for item in dependency_services:
           if item.get("name") == "DEPENDENCY_SERVICE":
               dependency_services = item.get("value").split(',') if item.get("value") else None
               dict_ds_ser[name] = dependency_services

       pod = subprocess.getoutput("kubectl get po -n {1} | grep {0} | cut -d ' ' -f 1".format(ds, namespace)).split('\n')
       pods = [x for x in pod if x]
       dict_ds_pod[ds] = pods
    dict_total[namespace] = {"dict_app":dict_app, "dict_depl":dict_depl, "dict_dep_ser":dict_dep_ser, "dict_rs":dict_rs, "dict_pod":dict_pod, "dict_ds":dict_ds, "dict_ds_ser":dict_ds_ser, "dict_ds_pod":dict_ds_pod}
    with open("total_dict.txt", "w") as wf:
        wf.write(str(dict_total))


def d3_grap_dependency(ns_list):
    dict_ns = {}
    di = {}
    dict_ns['name'] = 'K8S-Cluster'
    dict_ns['children'] = []
    dict_ns['namespace'] = ''
    for ns in ns_list:
        dict_app = dict_total.get(ns).get("dict_app")
        #if dict_app[ns] in [[None], []]:
            #continue
        dict_app[ns] = list(set(dict_total.get(ns).get("dict_app").get(ns)))
        dict_depl = dict_total.get(ns).get("dict_depl")
        dict_dep_ser = dict_total.get(ns).get("dict_dep_ser")
        dict_ds_ser = dict_total.get(ns).get("dict_ds_ser")
        dict_opn = {}
        dict_opn['name'] = ns
        dict_opn['children'] = []
        dict_opn['namespace'] = ns
        di = {}
        for k, v in dict_dep_ser.items():

            if v:
                for item in v:
                    if item in di.keys():
                        di[item].append(k)
                    else:
                        di[item] = []
                        di[item].append(k)

        for ser in di:
            dict_ser = {}
            dict_ser['name'] = ser
            dict_ser['children'] = []
            dict_ser['namespace'] = ns

            for item in di[ser]:
                dict_com = {}
                dict_com['name'] = item
                dict_com['namespace'] = ns
                dict_ser['children'].append(dict_com)

            dict_opn['children'].append(dict_ser)

        dict_ns['children'].append(dict_opn)

    with open("namespace.json", "w") as wf:
        wf.write(json.dumps(dict_ns))


if __name__ == '__main__':
    ns_list = subprocess.getoutput("kubectl get ns | cut -d ' ' -f 1").split('\n')[1:]
    ns_list = ['openstack', 'osh-infra', 'ceph', 'kube-system', 'tenant-ceph', 'ucp', 'utility']
    for ns in ns_list:
        pull_data(ns)
    d3_grap_dependency(ns_list)
    print('json data is ready')
