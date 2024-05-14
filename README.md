# Prisma Cloud DeamonSet Defender Auto Updater (Beta)
Kubernetes CronJob to update automatically Prisma Cloud defender DaemonSet in a Kubernetes cluster or OpenShift cluster.

## Requirements
1. Prisma Cloud Enterprise or self-hosted version
2. Kubernetes or OpenShift Cluster on a public or private cloud (EKS + Fargate not supported)
3. Access to Kubernetes cluster on current workstation via kubectl or helm
4. Kubernetes storage class (Public cloud providers regularly does have this)
5. Docker Image Registry

> NOTE
> * This process was tested on GCP Artifact Registry and Azure Container Registry.
> <br></br>

## Installation
### 1. Build Image
First you need to create your own Docker image. For that you'll need to download the following files:

* deleteJob.py
* checkDefenderUpdate.py
* requirements.txt
* Dockerfile

You can also clone this repo if needed.

After you've downloaded the files, build the image and push it to you own Image Registry:

```bash
$ docker build -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} .
$ docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
```

For MacOS is recommended to add the flag *--platform=linux/amd64* to the build command as follows:

```bash
$ docker build --platform=linux/amd64 -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} .
```

### 2. Install CronJob
You can install either via helm or kubectl. Helm is recommended.

#### Helm Method
To install the CronJob via helm, first create a *values.yaml* file like the following:

```yaml
compute:
  api_endpoint: https://us-east1.cloud.twistlock.com/us-1-123456789
  username: ${PRISMA_USERNAME}
  password: ${PRISMA_PASSWORD}
 
job:
  schedule: "0 0 * * Sun"
  timezone: "America/Los_Angeles"
  image_name: ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
  image_pull_secret: twistlock-updater-pull-secret
  pull_secret_dockerconfigjson: ${DOCKER_CONFIG}

defender:
  collect_pod_labels: true
  monitor_service_accounts: true
```
Substitute the variables for current values. The values of *compute.username* and *compute.password* are in plain text and the value *job.pull_secret_dockerconfigjson* in encoded in base 64 which is use to authenticate with the image registry.

Instead of using the value *job.pull_secret_dockerconfigjson* for authentication, you can use the following values:
```yaml
job:
  registry:
    name: REGISTRY
    username: REGISTRY_USERNAME
    password: REGISTRY_PASSWORD
```
All these values in plain text.

Once done install the helm chart using the following command:

```bash
$ helm upgrade --install -n twistlock -f values.yaml --create-namespace --repo https://paloaltonetworks.github.io/pcs-cwp-defender-updater twistlock-updater twistlock-updater
```
**Use Cases**
* **OpenShift**<br>
For OpenShift cluster please add the following values:
```yaml
defender:
  orchestrator: openshift
  container_runtime: crio
  selinux: true
```
* **StartJob**<br>
By default it creates a Job to install the defender when executing a `helm install` or `helm upgrade`. If you want to disable this behavior, set the value *job.start_now* to *false* as follows:

```yaml
job:
  start_now: false
```
* **DeleteJob**<br>
By default it creates a Job to uninstall the defender when executing a `helm uninstall`. If you want to disable this behavior, set the value *job.delete_all* to *false* as follows:

```yaml
job:
  delete_all: false
```
* **Disable CronJob**<br>
If you want to disable the CronJob creation, then set the value *job.cronjob_enabled* to *false* as follows:
```yaml
job:
  cronjob_enabled: false
```
* **Remove Persistant Volume**<br>
The Persistant Volume is used to store state information and rollback capabilities. This is being used by the CronJob and StartJob.<br></br>
By removing the Persistant Volume, it won't have the capability to rollback to the previous version, the StartJob will execute the defender installation at the beginning, and the CronJob will be checking if any update in the console version. <br></br>
To remove the Persistant Volume used for the CronJob and start Job, set the value *job.has_volume* to *false* as follows:
```yaml
job:
  has_volume: false
```

**Troubleshooting**<br>
In case if the ```helm uninstall``` fails, run the next commands to delete chart:
```bash
$ helm uninstall twistlock-updater -n twistlock --no-hooks
$ kubectl delete job twistlock-updater-delete -n twistlock
```

For more parameters that the *values.yaml* file can support, please refer on this repository to the file *Chart/twistlock-updater-helm/values.yaml*.


#### Kubectl Method
As reference you could use the file *twistlock-updater.yaml* found on this repository. Just substitute the values of the variables **PRISMA_USERNAME**, **PRISMA_PASSWORD**, **DOCKER_CONFIG**, **IMAGE_NAME** and **COMPUTE_API_ENDPOINT** found on this file, adjust as needed (like removing the ConfigMap **daemonset-extra-config** from the document and it's mounted volume in the CronJob manifest) and apply such a file.

```bash
$ kubectl apply -f twistlock-updater.yaml
```

The variables **PRISMA_USERNAME**, **PRISMA_PASSWORD** and **DOCKER_CONFIG** must be encoded in base64.


## Least privilege permissions
### Prisma Cloud SaaS version
In order to grant the least privileges to a user or service account in the SaaS version of Prisma Cloud, you must create a Permissions Group with View and Update for the Defenders Management permission and View for System permission. While you are creating a Permissions Group, the Defenders Management and System permissions can be found under **Assing Permissions** > **Compute** > **Manage** as in the following image:

![Least Privileges Permissions Group - Prisma Cloud SaaS version](./images/saas-least-privileges.png)

Once created this permissions group, you must create a role and then the belonging user or service account.

>**NOTE**
> * You must assing an account group to the role. Be sure to add the account groups of the accounts you need to modify. 
> * Is recommended to use a service account and access key.
> <br/><br/>

### Prisma Cloud self-hosted version
In order to grant the least privileges to a user in the self-hosted version of Prisma Cloud, you must create a role with Read and Write for the Defenders Management permission, Read for System permission and no access to the Console IU. While you are creating a Role, the Collections and Tags permission can be found under the Manage tab as in the following image:

![Least Privileges Role - Prisma Cloud self-hosted version](./images/self-hosted-least-privileges.png)

Once created this role, you must create the belonging user.

