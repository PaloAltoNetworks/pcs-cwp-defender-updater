variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "namespace" {
  description = "Prisma Cloud Defender namespace"
  type        = string
  default     = "twistlock"
}

variable "compute_api_endpoint" {
  description = "Prisma Cloud Compute API Endpoint"
  type        = string
}

variable "prisma_username" {
  description = "Prisma Cloud Compute username or Access Key"
  type        = string
}

variable "prisma_password" {
  description = "Prisma Cloud Compute user password or Secret Key"
  type        = string
}

variable "job-cronjob_enabled" {
  description = "Defender Auto Updater CronJob enablement"
  type        = bool
  default     = true
}

variable "job-schedule" {
  description = "Defender Auto Updater CronJob schedule"
  type        = string
  default     = "0 0 * * Sun"
}

variable "job-timezone" {
  description = "Defender Auto Updater CronJob timezone"
  type        = string
  default     = "Etc/UTC"
}

variable "job-image_name" {
  description = "Defender Auto Updater job Image Name"
  type        = string
}

variable "job-image_pull_secret" {
  description = "Defender Auto Updater job Image Pull Secret"
  type        = string
}

variable "job-pull_secret_dockerconfigjson" {
  description = "Defender Auto Updater job Image Pull Secret Docker config"
  type        = string
}

variable "job-has_volume" {
  description = "Defender Auto Updater job debug mode"
  type        = bool
  default     = true
}

variable "job-debug" {
  description = "Defender Auto Updater job debug mode"
  type        = bool
  default     = false
}

variable "defender-collect_pod_labels" {
  description = "Enable defender collect pod labels"
  type        = bool
  default     = true
}

variable "defender-monitor_service_accounts" {
  description = "Enable defender service accounts monitoring"
  type        = bool
  default     = true
}