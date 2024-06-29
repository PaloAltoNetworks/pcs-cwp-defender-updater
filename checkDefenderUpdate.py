#!/bin/ash
import os
import requests
import sys
import re
import yaml
import json
import shutil

from datetime import datetime
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from time import sleep


#Compute API parameters 
COMPUTE_API_ENDPOINT = os.getenv("COMPUTE_API_ENDPOINT", "https://us-east1.cloud.twistlock.com/us-1-23456789")
PRISMA_USERNAME = os.getenv("PRISMA_USERNAME", "")
PRISMA_PASSWORD = os.getenv("PRISMA_PASSWORD", "")
SKIP_VERIFY = os.getenv("SKIP_VERIFY", "false").lower() in ["true", "1", "y"]


#Defender parameters
NAMESPACE = os.getenv("NAMESPACE", "twistlock")
CONSOLE_NAME = os.getenv("CONSOLE_NAME", "")
COMMUNICATION_PORT = os.getenv("COMMUNICATION_PORT", "")
ORCHESTRATOR = os.getenv("ORCHESTRATOR", "kubernetes")
CONTAINER_RUNTIME = os.getenv("CONTAINER_RUNTIME", "containerd")
COLLECT_POD_LABELS = os.getenv("COLLECT_POD_LABELS", "false").lower() in ["true", "1", "y"]
MONITOR_SERVICEACCOUNTS = os.getenv("MONITOR_SERVICEACCOUNTS", "false").lower() in ["true", "1", "y"]
CLUSTER_NAME_RESOLVING_METHOD = os.getenv("CLUSTER_NAME_RESOLVING_METHOD", "")
CLUSTER_NAME = os.getenv("CLUSTER_NAME", "")
RUNTIME_SOCKET_PATH = os.getenv("RUNTIME_SOCKET_PATH", "")
NODE_SELECTOR = os.getenv("NODE_SELECTOR", '')
ROLE_ARN = os.getenv("ROLE_ARN", "")
UNIQUE_HOSTNAME = os.getenv("UNIQUE_HOSTNAME", "false").lower() in ["true", "1", "y"]
MONITOR_ISTIO = os.getenv("MONITOR_ISTIO", "false").lower() in ["true", "1", "y"]
BOTTLEROCKET = os.getenv("BOTTLEROCKET", "false").lower() in ["true", "1", "y"]
GKE_AUTOPILOT = os.getenv("GKE_AUTOPILOT", "false").lower() in ["true", "1", "y"]
TALOS = os.getenv("TALOS", "false").lower() in ["true", "1", "y"]
IMAGE_NAME = os.getenv("IMAGE_NAME", "")
IMAGE_PULL_SECRET = os.getenv("IMAGE_PULL_SECRET", "")
SELINUX = os.getenv("SELINUX", "false").lower() in ["true", "1", "y"]
PRIVILEGED = os.getenv("PRIVILEGED", "false").lower() in ["true", "1", "y"]
CPU_LIMIT = int(os.getenv("CPU_LIMIT", "0"))
MEMORY_LIMIT = int(os.getenv("MEMORY_LIMIT", "0"))
PRIOROTY_CLASS_NAME = os.getenv("PRIOROTY_CLASS_NAME", "")
PROJECT_ID = os.getenv("PROJECT_ID", "")
REGION = os.getenv("REGION", "")
PROXY = {}
TOLERATIONS = []
ANNOTATIONS = {}

# Manifest variables
DAEMONSET_NAME = os.getenv("DAEMONSET_NAME", "twistlock-defender-ds")
CLUSTER_ROLE = os.getenv("CLUSTER_ROLE", "twistlock-view")
CLUSTER_ROLEBINDING = os.getenv("CLUSTER_ROLEBINDING", "twistlock-view-binding")
DAEMONSET_SECRET = os.getenv("DAEMONSET_SECRET", "twistlock-secrets")
DAEMONSET_SERVICEACCOUNT = os.getenv("DAEMONSET_SERVICEACCOUNT", "twistlock-service")
DAEMONSET_SERVICE = os.getenv("DAEMONSET_SERVICE", "defender")
OPENSHIFT_SCC = os.getenv("OPENSHIFT_SCC", "twistlock-scc")

#Application parameters
VERSION_REGEX = os.getenv("VERSION_REGEX", "[0-9]{2}_[0-9]{2}_[0-9]{3}")
MAX_ERRORS = int(os.getenv("MAX_ERRORS", "3"))
CHECK_SLEEP = int(os.getenv("CHECK_SLEEP", "15"))
WORKDIR = os.getcwd()
DEAMONSET_CONFIG = f"{WORKDIR}/twistlock/daemonsetConfig.json"
DEAMONSET_FILE = f"{WORKDIR}/twistlock/daemonset.yaml"
NEW_DEAMONSET_FILE = f"{WORKDIR}/twistlock/daemonset.new.yaml"
OLD_DEAMONSET_FILE = f"{WORKDIR}/twistlock/daemonset.old.yaml"
INIT_DEAMONSET_FILE = f"{WORKDIR}/init/daemonset.yaml"
DEAMONSET_EXTRACONFIG_FILE = f"{WORKDIR}/config/daemonset.extraconfig.yaml"
HAS_VOLUME = os.getenv("HAS_VOLUME", "true").lower() in ["true", "1", "y"]
START_NOW = os.getenv("START_NOW", "false").lower() in ["true", "1", "y"]
DEBUG = os.getenv("DEBUG", "false").lower() in ["true", "1", "y"]

def checkConnectivity(api_endpoint, verify=True):
    response = requests.get(f"{api_endpoint}/api/v1/_ping", verify=verify)
    if response.status_code == 200:
        print(f"{datetime.now()} Connection to the endpoint {api_endpoint} succedded.")
    else:
        print(f"{datetime.now()} Connection to the endpoint {api_endpoint} failed.")
        sys.exit(2)


def getToken(username, password, api_endpoint, verify):
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "username": username,
        "password": password
    }

    response = requests.post(f"{api_endpoint}/api/v1/authenticate", json=body, headers=headers, verify=verify)
    if response.status_code == 200:
        return response.json()["token"]
    
    print(f"{datetime.now()} Error while authenticating. Error: {response.json()['err']}")
    sys.exit(5)


def getDaemonsetVersion(apps_v1_api):
    daemonsets_list = apps_v1_api.list_namespaced_daemon_set(NAMESPACE)
    version = ""

    for item in daemonsets_list.items:
        if item.metadata.name == DAEMONSET_NAME:
            for container in item.spec.template.spec.containers:
                image = container.image
                version = re.findall(VERSION_REGEX, image)[0].replace("_", ".")
                break
    
    return version


def getConsoleInfo(api_endpoint, headers, verify=True):
    response = requests.get(f"{api_endpoint}/api/v1/settings/system", headers=headers, verify=verify)
    console_name = CONSOLE_NAME

    if response.status_code == 200:
        version = response.json()["version"]
        if not console_name:
            console_name = response.json()["consoleNames"][0]
        
        return version, console_name

    print(f"{datetime.now()} Error while getting console version. Error: {response.json()['err']}")
    sys.exit(5)


def deleteDeamonSetResources(core_v1_api, apps_v1_api, rbac_v1_api, custom_api):
    deleteK8SResource(rbac_v1_api.delete_cluster_role, CLUSTER_ROLE, "ClusterRole")
    deleteK8SResource(rbac_v1_api.delete_cluster_role_binding, CLUSTER_ROLEBINDING, "ClusterRoleBinding")
    deleteK8SResource(apps_v1_api.delete_namespaced_daemon_set, DAEMONSET_NAME, "DaemonSet", NAMESPACE)
    deleteK8SResource(core_v1_api.delete_namespaced_secret, DAEMONSET_SECRET, "Secret", NAMESPACE)
    deleteK8SResource(core_v1_api.delete_namespaced_service_account, DAEMONSET_SERVICEACCOUNT, "ServiceAccount", NAMESPACE)
    deleteK8SResource(core_v1_api.delete_namespaced_service, DAEMONSET_SERVICE, "Service", NAMESPACE)
    if ORCHESTRATOR == "openshift":
        deleteK8SResource(custom_api.delete_cluster_custom_object, OPENSHIFT_SCC, "SecurityContextConstraints")


def deleteK8SResource(delete_function, resource_name, kind="", namespace=""):
    try:
        if kind == "SecurityContextConstraints":
            if DEBUG: print(f"{datetime.now()} Deleting {kind} resource named {resource_name}")
            delete_function(
                group="security.openshift.io", 
                version="v1", 
                plural="securitycontextconstraints",
                name=resource_name
            )

        elif namespace:
            if DEBUG: print(f"{datetime.now()} Deleting {kind} resource named {resource_name} in namespace {namespace}.")
            delete_function(resource_name, namespace)
            
        else:
            if DEBUG: print(f"{datetime.now()} Deleting {kind} resource named {resource_name}")
            delete_function(resource_name)
            
    except ApiException as error:
        print(f"{datetime.now()} Error: {error}")


def createK8SResource(create_function, body, namespace=""):
    try:
        if body['kind'] == "SecurityContextConstraints":
            if DEBUG: print(f"{datetime.now()} Creating {body['kind']} resource named {body['metadata']['name']}")
            create_function(
                group="security.openshift.io", 
                version="v1", 
                plural="securitycontextconstraints",
                body=body
            )

        elif namespace:
            if DEBUG: print(f"{datetime.now()} Creating {body['kind']} resource named {body['metadata']['name']} in namespace {namespace}")
            create_function(namespace, body)

        else:
            if DEBUG: print(f"{datetime.now()} Creating {body['kind']} resource named {body['metadata']['name']}")
            create_function(body)
            

    except ApiException as error:
        print(f"{datetime.now()} Error: {error}")


def applyYAML(core_v1_api, apps_v1_api, rbac_v1_api, custom_api, yaml_file):
    with open(yaml_file, 'r') as manifest:
        resources = yaml.safe_load_all(manifest)
    
        for resource in resources:
            if resource:
                if "kind" in resource:
                    kind = resource["kind"]
                    if kind == "ClusterRole": createK8SResource(rbac_v1_api.create_cluster_role, resource)
                    elif kind == "ClusterRoleBinding": createK8SResource(rbac_v1_api.create_cluster_role_binding, resource)
                    elif kind == "Secret": createK8SResource(core_v1_api.create_namespaced_secret, resource, NAMESPACE)
                    elif kind == "ServiceAccount": createK8SResource(core_v1_api.create_namespaced_service_account, resource, NAMESPACE)
                    elif kind == "DaemonSet": createK8SResource(apps_v1_api.create_namespaced_daemon_set, resource, NAMESPACE)
                    elif kind == "Service": createK8SResource(core_v1_api.create_namespaced_service, resource, NAMESPACE)
                    elif kind == "SecurityContextConstraints": createK8SResource(custom_api.create_cluster_custom_object, resource)


def defenderStatusOk(console_name, node_name, api_endpoint, headers, verify=True):
    response = requests.get(f"{api_endpoint}/api/v1/defenders?search={node_name}", headers=headers, verify=verify)
    data = response.json()

    if response.status_code == 200:
        if data:
            for host in response.json():
                if host["connected"]:
                    return host["connected"]
        else:
            print(f"{datetime.now()} Defender for node {node_name} not found in console. Verify you are using the appropriate console name. Console Name: {console_name}")

    return False


def applyDaemonSet(core_v1_api, apps_v1_api, rbac_v1_api, custom_api, defender_config, api_endpoint, headers, verify=True):
    response = requests.post(f"{api_endpoint}/api/v1/defenders/daemonset.yaml", json=defender_config, headers=headers, verify=verify)

    if response.status_code == 200:
        if DEBUG:
            print(f"{datetime.now()} Creating the following deamonset \n{response.text}")
        
        with open(NEW_DEAMONSET_FILE, "w") as daemonset_manifest:
            daemonset_manifest.write(response.text)
            daemonset_manifest.close()
        
        deleteDeamonSetResources(core_v1_api, apps_v1_api, rbac_v1_api, custom_api)
        applyYAML(core_v1_api, apps_v1_api, rbac_v1_api, custom_api, NEW_DEAMONSET_FILE)

    else:
        print(f"{datetime.now()} Error while downloading Defender. Error: {response.json()['err']}")
        sys.exit(5)


def configChanged(new_defender_config):
    if os.path.exists(DEAMONSET_CONFIG):
        with open(DEAMONSET_CONFIG, "r") as config_file:
            defender_config = json.loads(config_file.read())
        
        for feature in new_defender_config:
            if feature in defender_config:
                if defender_config[feature] != new_defender_config[feature]:
                    print(f"{datetime.now()} Change detected in defender configuration.")
                    if DEBUG:
                        print(f"Current defender configuration:\n{defender_config}")
                    
                    return True
            else:
                print(f"{datetime.now()} Change detected in defender configuration.")
                if DEBUG:
                        print(f"{datetime.now()} Current defender configuration:\n{defender_config}")
                    
                return True
            
        print(f"{datetime.now()} Change not found in defender configuration.")
        return False
    
    print(f"{datetime.now()} defender configuration file not found.")
    return True


def main():
    config.load_incluster_config()
    core_v1_api = client.CoreV1Api()
    apps_v1_api = client.AppsV1Api()
    rbac_v1_api = client.RbacAuthorizationV1Api()
    custom_api = client.CustomObjectsApi()

    checkConnectivity(COMPUTE_API_ENDPOINT, not SKIP_VERIFY)
    token = getToken(PRISMA_USERNAME, PRISMA_PASSWORD, COMPUTE_API_ENDPOINT, not SKIP_VERIFY)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    console_version, console_name = getConsoleInfo(COMPUTE_API_ENDPOINT, headers, not SKIP_VERIFY)
    daemonset_version = getDaemonsetVersion(apps_v1_api)

    if COMMUNICATION_PORT:
        console_name = f"{console_name}:{COMMUNICATION_PORT}"

    new_defender_config = {
        "version": console_version,
        "annotations": ANNOTATIONS,
        "bottlerocket": BOTTLEROCKET,
        "clusterNameResolvingMethod": CLUSTER_NAME_RESOLVING_METHOD,
        "cluster": CLUSTER_NAME,
        "collectPodLabels": COLLECT_POD_LABELS,
        "consoleAddr": console_name,
        "containerRuntime": CONTAINER_RUNTIME,
        "cpuLimit": CPU_LIMIT,
        "dockerSocketPath": RUNTIME_SOCKET_PATH,
        "gkeAutopilot": GKE_AUTOPILOT,
        "image": IMAGE_NAME,
        "istio": MONITOR_ISTIO,
        "memoryLimit": MEMORY_LIMIT,
        "namespace": NAMESPACE,
        "nodeSelector": NODE_SELECTOR,
        "orchestration": ORCHESTRATOR,
        "priorityClassName": PRIOROTY_CLASS_NAME,
        "privileged": PRIVILEGED,
        "projectID": PROJECT_ID,
        "proxy": PROXY,
        "region": REGION,
        "secretsname": IMAGE_PULL_SECRET,
        "selinux": SELINUX,
        "serviceAccounts": MONITOR_SERVICEACCOUNTS,
        "talos": TALOS,
        "tolerations": TOLERATIONS,
        "uniqueHostname": UNIQUE_HOSTNAME
    }

    if os.path.exists(DEAMONSET_EXTRACONFIG_FILE):
        with open(DEAMONSET_EXTRACONFIG_FILE) as extra_config_file:
            extra_config = yaml.safe_load(extra_config_file)
            new_defender_config.update(extra_config)


    if not HAS_VOLUME:
        if not START_NOW:
            if console_version == daemonset_version:
                print(f"{datetime.now()} Console and Defender version match. Version {console_version}")
                return 0

    if os.path.exists(DEAMONSET_FILE) and not configChanged(new_defender_config):
        if console_version == daemonset_version:
            print(f"{datetime.now()} Console and Defender version match. Version {console_version}")
            return 0
        
        if not daemonset_version:
            print(f"{datetime.now()} Defender not installed.")
        else:
            print(f"{datetime.now()} Console and Defender version doesn't match. Console version: {console_version}; Defender version: {daemonset_version}")
    
    elif os.path.exists(INIT_DEAMONSET_FILE):
        shutil.copyfile(INIT_DEAMONSET_FILE, DEAMONSET_FILE)

    if DEBUG: print(f"New defender configuration:\n{new_defender_config}")

    print(f"{datetime.now()} Installing defender version {console_version}")


    applyDaemonSet(core_v1_api, apps_v1_api, rbac_v1_api, custom_api, new_defender_config, COMPUTE_API_ENDPOINT, headers, not SKIP_VERIFY)

    # Checking defender Status for possible rollback
    node_name = core_v1_api.list_node().items[0].metadata.name
    error_count = 0
    status_ok = False

    while error_count <= MAX_ERRORS:
        sleep(CHECK_SLEEP)
        status_ok = defenderStatusOk(console_name, node_name, COMPUTE_API_ENDPOINT, headers, not SKIP_VERIFY)
        if status_ok:
            break
        error_count += 1
    
    if status_ok:
        print(f"{datetime.now()} Defender version {console_version} in correct status!!")
        with open(DEAMONSET_CONFIG, "w") as config_file:
            config_file.write(json.dumps(new_defender_config))

        if os.path.exists(DEAMONSET_FILE):
            os.rename(DEAMONSET_FILE, OLD_DEAMONSET_FILE)

        os.rename(NEW_DEAMONSET_FILE, DEAMONSET_FILE)

    else:
        if os.path.exists(DEAMONSET_FILE):
            print(f"{datetime.now()} Defender in incorrect status. Rolling back to previous version.")
            if DEBUG:
                with open(DEAMONSET_CONFIG, "r") as config_file:
                    print(f"Previous defender configuration:\n{config_file.read()}")
                    config_file.close()

            deleteDeamonSetResources(core_v1_api, apps_v1_api, rbac_v1_api, custom_api)
            applyYAML(core_v1_api, apps_v1_api, rbac_v1_api, custom_api, DEAMONSET_FILE)
        else:
            print(f"{datetime.now()} Defender in incorrect status. Cannot rollback due to theres no previous version")  


if __name__ == "__main__":
    main()