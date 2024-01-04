variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
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

variable "job-schedule" {
  description = "Defender Auto Updater CronJob schedule"
  type        = string
}

variable "job-timezone" {
  description = "Defender Auto Updater CronJob timezone"
  type        = string
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

variable "job-debug" {
  description = "Defender Auto Updater job debug mode"
  type        = bool
}

variable "defender-collect_pod_labels" {
  description = "Enable defender collect pod labels"
  type        = bool
}

variable "defender-monitor_service_accounts" {
  description = "Enable defender service accounts monitoring"
  type        = bool
}