# Prisma Cloud DeamonSet Defender Auto-updater
Kubernetes CronJob to update automatically Prisma Cloud defender DaemonSet in a kubernetes cluster.

## Requirements
1. Prisma Cloud Enterprise or self-hosted version
2. Kubernetes Cluster on a public or private cloud (EKS + Fargate not supported)
3. Access to Kubernetes cluster on current workstation via kubectl or helm
4. Kubernetes storage class (Public cloud providers regularly does have this)
5. Docker Image Registry

## Installation
### 1. Build Image
First you need to create your own Docker image. For that you'll need to download the following files:

* checkDefenderUpdate.py
* requirements.txt
* Dockerfile

You can also clone this repo if needed.

After you've downloaded the files, build the image and push it to you own Image Registry:

```bash
$ docker build -t ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} .
$ docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
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
Substitute the variables for current values.

Once done install the helm chart using the following command:

```bash
$ helm upgrade --install -n twistlock -f values.yaml --create-namespace twistlock-updater https://raw.githubusercontent.com/PaloAltoNetworks/pcs-cwp-defender-updater/main/Chart/twistlock-updater-helm.tar.gz
```

For more parameters that the *values.yaml* file can support, please refer on this repository to the file *Chart/twistlock-updater-helm/values.yaml*.

#### Kubectl Method
As reference you could use the file *twistlock-updater.yaml* found on this repository. Just substitute the values of the variables **PRISMA_USERNAME**, **PRISMA_PASSWORD**, **DOCKER_CONFIG**, **IMAGE_NAME** and **COMPUTE_API_ENDPOINT** found on this file, adjust as needed (like removing the ConfigMap **daemonset-extra-config** from the document and it's mounted volume in the CronJob manifest) and apply such a file.

```bash
$ kubectl apply -f twistlock-updater.yaml
```

The variables **PRISMA_USERNAME**, **PRISMA_PASSWORD** and **DOCKER_CONFIG** must be encoded in base64

> NOTE
> * This process was tested using GCP Artifact Registry.
> <br></br>
