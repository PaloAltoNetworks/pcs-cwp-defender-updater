data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_name
  depends_on = [
    module.eks
  ]
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    token                  = data.aws_eks_cluster_auth.cluster.token
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  }
}

resource "helm_release" "twistlock-updater" {
  name = "twistlock-updater"

  repository       = "https://paloaltonetworks.github.io/pcs-cwp-defender-updater"
  chart            = "twistlock-updater"
  namespace        = var.namespace
  create_namespace = true
  version          = "1.0.0"
  wait             = false

  set {
    name  = "compute.api_endpoint"
    value = var.compute_api_endpoint
  }

  set {
    name  = "compute.username"
    value = var.prisma_username
  }

  set {
    name  = "compute.password"
    value = var.prisma_password
  }

  set {
    name  = "job.schedule"
    value = var.job-schedule
  }


  set {
    name  = "job.timezone"
    value = var.job-timezone
  }

  set {
    name  = "job.image_name"
    value = var.job-image_name
  }

  set {
    name  = "job.image_pull_secret"
    value = var.job-image_pull_secret
  }

  set {
    name  = "job.pull_secret_dockerconfigjson"
    value = var.job-pull_secret_dockerconfigjson
  }

  set {
    name  = "job.debug"
    value = var.job-debug
  }

  set {
    name  = "defender.collect_pod_labels"
    value = var.defender-collect_pod_labels
  }

  set {
    name  = "defender.monitor_service_accounts"
    value = var.defender-monitor_service_accounts
  }

  depends_on = [
    aws_eks_addon.ebs-csi,
    module.eks,
    module.vpc
  ]
}