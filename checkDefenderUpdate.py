#!/bin/ash
import os
import re
import yaml
import json

from urllib.parse import urlparse
from datetime import datetime
from kubernetes import config
from kubernetes.client import CoreV1Api, AppsV1Api, RbacAuthorizationV1Api, CustomObjectsApi
from kubernetes.client.exceptions import ApiException
from time import sleep

from prismaapi import PrismaAPI

#Prisma API parameters 
PRISMA_API_ENDPOINT = os.getenv("PRISMA_API_ENDPOINT", "")
COMPUTE_API_ENDPOINT = os.getenv("COMPUTE_API_ENDPOINT", "")
PRISMA_USERNAME = os.getenv("PRISMA_USERNAME", "")
PRISMA_PASSWORD = os.getenv("PRISMA_PASSWORD", "")
VERSION_TAG = os.getenv("VERSION_TAG", "")
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes", "y")
SLEEP = int(os.getenv("SLEEP", "5"))
LIMIT = int(os.getenv("LIMIT", "50"))
CONNECT_TIMEOUT = int(os.getenv("CONNECT_TIMEOUT", "2"))
READ_TIMEOUT = int(os.getenv("READ_TIMEOUT", "7"))
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
DEAMONSET_FILE = f"{WORKDIR}/twistlock/daemonset.yaml"
NEW_DEAMONSET_FILE = f"{WORKDIR}/twistlock/daemonset.new.yaml"
DEAMONSET_EXTRACONFIG_FILE = f"{WORKDIR}/config/daemonset.extraconfig.yaml"
HAS_VOLUME = os.getenv("HAS_VOLUME", "true").lower() in ["true", "1", "y"]
START_NOW = os.getenv("START_NOW", "false").lower() in ["true", "1", "y"]
DEBUG = os.getenv("DEBUG", "false").lower() in ["true", "1", "y"]

IGNORED_DS_FIELDS = ("status", "clusterIPs", "clusterIp", "creationTimestamp", "managedFields", "resourceVersion", "uid", "generation")

def snake_to_camel(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_dict_to_camel_case(data):
    if isinstance(data, dict):
        new_dict = {}

        for key, value in data.items():
            if value != None:
                if key.lower() == "host_pid":
                    new_key = "hostPID"
                else:
                    new_key = snake_to_camel(key)

                if not new_key in IGNORED_DS_FIELDS:
                    new_dict[new_key] = convert_dict_to_camel_case(value)
        return new_dict
    
    elif isinstance(data, list):
        return [convert_dict_to_camel_case(item) for item in data]
    
    elif isinstance(data, str):
        return data.replace("'","\"")
    
    else:
        return data


def getConsoleInfo(prismaAPI: PrismaAPI):
    version = ""
    console_name = CONSOLE_NAME
    
    if VERSION_TAG:
        response = json.loads(prismaAPI.compute_request("/api/v1/tags", method="GET", skip_error=True))
        if response:
            for tag in response:
                if tag["name"] == VERSION_TAG:
                    if "description" in tag:
                        if re.search(VERSION_REGEX.replace("_", "."), tag["description"]):
                            print(f"{datetime.now()} using tag {VERSION_TAG} as the console version")
                            version = tag["description"]
                    break

    # Get version
    if not version: version = prismaAPI.compute_request("/api/v1/version", method="GET").decode().replace('"','')

    # Get console name
    if not console_name:
        response = json.loads(prismaAPI.compute_request("/api/v1/settings/system", method="GET", skip_error=True))

        if not response: 
            console_name = urlparse(COMPUTE_API_ENDPOINT).netloc
        else:
            console_name = response["consoleNames"][0]
    
    return version, console_name


def deleteDeamonSetResources(core_v1_api: CoreV1Api, apps_v1_api: AppsV1Api, rbac_v1_api: RbacAuthorizationV1Api, custom_api: CustomObjectsApi):
    deleteK8SResource(rbac_v1_api.delete_cluster_role, CLUSTER_ROLE, "ClusterRole")
    deleteK8SResource(rbac_v1_api.delete_cluster_role_binding, CLUSTER_ROLEBINDING, "ClusterRoleBinding")
    deleteK8SResource(apps_v1_api.delete_namespaced_daemon_set, DAEMONSET_NAME, "DaemonSet", NAMESPACE)
    deleteK8SResource(core_v1_api.delete_namespaced_secret, DAEMONSET_SECRET, "Secret", NAMESPACE)
    deleteK8SResource(core_v1_api.delete_namespaced_service_account, DAEMONSET_SERVICEACCOUNT, "ServiceAccount", NAMESPACE)
    deleteK8SResource(core_v1_api.delete_namespaced_service, DAEMONSET_SERVICE, "Service", NAMESPACE)
    if ORCHESTRATOR == "openshift":
        deleteK8SResource(custom_api.delete_cluster_custom_object, OPENSHIFT_SCC, "SecurityContextConstraints")


def deleteK8SResource(delete_function, resource_name: str, kind="", namespace=""):
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


def readK8SResource(read_function, name, namespace="", kind=""):
    data = None
    try:
        if kind == "SecurityContextConstraints":
            read_function(
                group="security.openshift.io", 
                version="v1", 
                plural="securitycontextconstraints",
                name=name
            )

        elif namespace:
            data = convert_dict_to_camel_case(read_function(name, namespace).to_dict())

        else:
            data = convert_dict_to_camel_case(read_function(name).to_dict())

    except ApiException as error:
        print(f"{datetime.now()} Error: {error}")
    
    return data

def createK8SResource(create_function, body, namespace=""):
    try:
        if body['kind'] == "SecurityContextConstraints":
            if DEBUG: print(f"{datetime.now()} Creating {body['kind']} resource named {body['metadata']['name']}\n{yaml.dump(body)}")
            create_function(
                group="security.openshift.io", 
                version="v1", 
                plural="securitycontextconstraints",
                body=body
            )

        elif namespace:
            if DEBUG: print(f"{datetime.now()} Creating {body['kind']} resource named {body['metadata']['name']} in namespace {namespace}\n{yaml.dump(body)}")
            create_function(namespace, body)

        else:
            if DEBUG: print(f"{datetime.now()} Creating {body['kind']} resource named {body['metadata']['name']}\n{yaml.dump(body)}")
            create_function(body)
            
    except ApiException as error:
        print(f"{datetime.now()} Error: {error}")


def applyYAML(core_v1_api: CoreV1Api, apps_v1_api: AppsV1Api, rbac_v1_api: RbacAuthorizationV1Api, custom_api: CustomObjectsApi, yaml_file: str, version=""):
    with open(yaml_file, 'r') as manifest:
        resources = list(yaml.safe_load_all(manifest))
        
    for resource in resources:
        if resource:
            if "kind" in resource:
                kind = resource["kind"]
                if kind == "ClusterRole": createK8SResource(rbac_v1_api.create_cluster_role, resource)
                elif kind == "ClusterRoleBinding": createK8SResource(rbac_v1_api.create_cluster_role_binding, resource)
                elif kind == "Secret": createK8SResource(core_v1_api.create_namespaced_secret, resource, NAMESPACE)
                elif kind == "ServiceAccount": createK8SResource(core_v1_api.create_namespaced_service_account, resource, NAMESPACE)
                elif kind == "DaemonSet": 
                    # Deploy the defender using a particular image version
                    if version and not IMAGE_NAME:
                        image = re.sub(VERSION_REGEX, version.replace(".", "_"), resource["spec"]["template"]["spec"]["containers"][0]["image"])
                        resource["spec"]["template"]["spec"]["containers"][0]["image"] = image

                    createK8SResource(apps_v1_api.create_namespaced_daemon_set, resource, NAMESPACE)
                elif kind == "Service": createK8SResource(core_v1_api.create_namespaced_service, resource, NAMESPACE)
                elif kind == "SecurityContextConstraints": createK8SResource(custom_api.create_cluster_custom_object, resource)


def defenderStatusOk(console_name: str, node_name: str, prismaAPI: PrismaAPI):
    response = json.loads(prismaAPI.compute_request(f"/api/v1/defenders?search={node_name}", method="GET"))
    if response:
        for host in response:
            if host["connected"]:
                return host["connected"]
    else:
        print(f"{datetime.now()} Defender for node {node_name} not found in console. Verify you are using the appropriate console name. Console Name: {console_name}")

    return False


def applyDaemonSet(core_v1_api: CoreV1Api, apps_v1_api: AppsV1Api, rbac_v1_api: RbacAuthorizationV1Api, custom_api: CustomObjectsApi, defender_config: dict, prismaAPI: PrismaAPI, version = ""):
    response = prismaAPI.compute_request("/api/v1/defenders/daemonset.yaml", body=defender_config).decode()
    
    with open(NEW_DEAMONSET_FILE, "w") as daemonset_manifest:
        daemonset_manifest.write(response)
        daemonset_manifest.close()
        
        deleteDeamonSetResources(core_v1_api, apps_v1_api, rbac_v1_api, custom_api)
        applyYAML(core_v1_api, apps_v1_api, rbac_v1_api, custom_api, NEW_DEAMONSET_FILE, version)


def main():
    config.load_incluster_config()
    core_v1_api = CoreV1Api()
    apps_v1_api = AppsV1Api()
    rbac_v1_api = RbacAuthorizationV1Api()
    custom_api = CustomObjectsApi()
    current_version = ""

    prismaAPI = PrismaAPI(
        PRISMA_API_ENDPOINT, 
        COMPUTE_API_ENDPOINT, 
        PRISMA_USERNAME, 
        PRISMA_PASSWORD, 
        LIMIT, 
        SLEEP, 
        CONNECT_TIMEOUT, 
        READ_TIMEOUT, 
        DEBUG
    )
    
    console_version, console_name = getConsoleInfo(prismaAPI)

    # Set defender configuration parameters
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

    # backup manifests
    resources = []

    # Backup the resources belonging to the deployment
    resources.append(readK8SResource(rbac_v1_api.read_cluster_role, CLUSTER_ROLE))
    resources.append(readK8SResource(rbac_v1_api.read_cluster_role_binding, CLUSTER_ROLEBINDING))
    resources.append(readK8SResource(core_v1_api.read_namespaced_secret, DAEMONSET_SECRET, NAMESPACE))
    resources.append(readK8SResource(core_v1_api.read_namespaced_service_account, DAEMONSET_SERVICEACCOUNT, NAMESPACE))
    defender_resource = readK8SResource(apps_v1_api.read_namespaced_daemon_set, DAEMONSET_NAME, NAMESPACE)
    resources.append(defender_resource)
    resources.append(readK8SResource(core_v1_api.read_namespaced_service, DAEMONSET_SERVICE, NAMESPACE))

    if ORCHESTRATOR == "openshift":
        resources.append(readK8SResource(custom_api.get_cluster_custom_object, OPENSHIFT_SCC, kind="SecurityContextConstraints"))

    # Backup resources
    with open(DEAMONSET_FILE, "w") as daemonset_file:
        for resource in resources:
            if resource:
                yaml.safe_dump(resource, daemonset_file, default_flow_style=False)
                daemonset_file.write("---\n")
    
    # Get current defender version
    if defender_resource:
        image = defender_resource["spec"]["template"]["spec"]["containers"][0]["image"]
        current_version = re.findall(VERSION_REGEX, image)[0].replace("_", ".")


    if os.path.exists(DEAMONSET_EXTRACONFIG_FILE):
        with open(DEAMONSET_EXTRACONFIG_FILE) as extra_config_file:
            extra_config = yaml.safe_load(extra_config_file)
            new_defender_config.update(extra_config)


    if not START_NOW:
        if console_version == current_version:
            print(f"{datetime.now()} Console and Defender version match. Version {console_version}")
            return 0
        
        if not current_version:
            print(f"{datetime.now()} Defender not installed.")
        else:
            print(f"{datetime.now()} Console and Defender version doesn't match. Console version: {console_version}; Defender version: {current_version}")

    else:
        print(f"{datetime.now()} Executing initial installation")


    print(f"{datetime.now()} Installing defender version {console_version}")
    if DEBUG: 
        print_config = {"Configuration": new_defender_config}
        print(f"{yaml.dump(print_config)}")

    applyDaemonSet(core_v1_api, apps_v1_api, rbac_v1_api, custom_api, new_defender_config, prismaAPI, console_version)

    # Checking defender Status for possible rollback
    node_name = os.getenv("NODE_NAME")
    error_count = 0
    status_ok = False
    print(f"{datetime.now()} Instalation of defender version {console_version} completed. Checking for the defender status...")

    while error_count <= MAX_ERRORS:
        sleep(CHECK_SLEEP)
        status_ok = defenderStatusOk(console_name, node_name, prismaAPI)
        if status_ok:
            break
        error_count += 1
    
    if status_ok:
        print(f"{datetime.now()} Defender version {console_version} in correct status!!")

    else:
        if current_version:
            print(f"{datetime.now()} Defender in incorrect status. Rolling back to previous version {current_version}.")

            # Execute rollback
            deleteDeamonSetResources(core_v1_api, apps_v1_api, rbac_v1_api, custom_api)
            applyYAML(core_v1_api, apps_v1_api, rbac_v1_api, custom_api, DEAMONSET_FILE)
            print(f"{datetime.now()} Rollback completed. Defender version {current_version}.")
        else:
            print(f"{datetime.now()} No previous defender version. Cannot Rollback")


if __name__ == "__main__":
    main()