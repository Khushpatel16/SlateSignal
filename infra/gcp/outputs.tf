output "api_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "model_bucket" {
  value = google_storage_bucket.models.name
}

output "scheduled_jobs" {
  value = {
    for key, job in google_cloud_run_v2_job.scheduled : key => job.name
  }
}
