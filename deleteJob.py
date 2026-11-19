#!/bin/ash
from kubernetes import client, config
from checkDefenderUpdate import deleteDeamonSetResources

def main():
    config.load_incluster_config()
    core_v1_api = client.CoreV1Api()
    apps_v1_api = client.AppsV1Api()
    rbac_v1_api = client.RbacAuthorizationV1Api()
    custom_api = client.CustomObjectsApi()

    deleteDeamonSetResources(core_v1_api, apps_v1_api, rbac_v1_api, custom_api)

if __name__ == "__main__":
    main()