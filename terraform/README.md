## Defender Auto Updater Integration with Terraform

This folder gives some samples to integrate Terraform using AWS EKS Cluster and Helm to install Defender Auto Updater and DaemonSet Defender in such cluster.

Assign values to the variables found in *variables.tf* file by creating a **.tfvars* file, using environment varibles, or using Terraform Cloud.

Also create the environment variables of **AWS_ACCESS_KEY_ID** and **AWS_SECRET_ACCESS_KEY** to be able to connect to AWS.

Commands:
```bash
terraform init
terraform validate
terraform plan
terraform apply --auto-approve
```