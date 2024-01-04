output "cluster_status" {
  description = "EKS Cluster status"
  value       = module.eks.cluster_status
}

output "twistlock_updater_status" {
  description = "Twistlock Updater release chart status"
  value       = helm_release.twistlock-updater.status
}