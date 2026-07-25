locals {
  required_apis = toset([
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
  ])

  jobs = {
    catalog = {
      args     = ["catalog-sync"]
      schedule = "17 3 * * *"
    }
    actuals = {
      args     = ["actuals-sync", "--limit", "1000"]
      schedule = "47 3 * * *"
    }
    buzz = {
      args     = ["buzz-sync", "--limit", "500"]
      schedule = "12 4 * * *"
    }
    forecasts = {
      args     = ["forecast-snapshot"]
      schedule = "42 4 * * *"
    }
    imdb = {
      args     = ["imdb-sync"]
      schedule = "31 5 * * 1"
    }
  }
}

resource "google_project_service" "required" {
  for_each           = local.required_apis
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "models" {
  name                        = "${var.project_id}-slatesignal-models"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }
}

data "google_secret_manager_secret" "database" {
  secret_id  = var.database_secret_id
  depends_on = [google_project_service.required]
}

data "google_secret_manager_secret" "tmdb" {
  secret_id  = var.tmdb_secret_id
  depends_on = [google_project_service.required]
}

data "google_secret_manager_secret" "admin_bootstrap" {
  secret_id  = var.admin_bootstrap_secret_id
  depends_on = [google_project_service.required]
}

resource "google_service_account" "runtime" {
  account_id   = "slatesignal-runtime"
  display_name = "SlateSignal Cloud Run runtime"
}

resource "google_service_account" "scheduler" {
  account_id   = "slatesignal-scheduler"
  display_name = "SlateSignal Scheduler invoker"
}

resource "google_secret_manager_secret_iam_member" "runtime_database" {
  secret_id = data.google_secret_manager_secret.database.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_tmdb" {
  secret_id = data.google_secret_manager_secret.tmdb.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_admin_bootstrap" {
  secret_id = data.google_secret_manager_secret.admin_bootstrap.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket_iam_member" "runtime_models" {
  bucket = google_storage_bucket.models.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_cloud_run_v2_service" "api" {
  name                = "slatesignal-api"
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.runtime.email
    timeout         = "60s"

    scaling {
      min_instance_count = 0
      max_instance_count = 4
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle = true
      }

      env {
        name  = "WEB_ORIGIN"
        value = var.web_origin
      }
      env {
        name  = "COOKIE_SECURE"
        value = "true"
      }
      env {
        name  = "AUTO_CREATE_SCHEMA"
        value = "false"
      }
      env {
        name  = "ADMIN_EMAIL"
        value = var.admin_email
      }
      env {
        name  = "BERT_ONNX_PATH"
        value = "/models/bert-base-uncased-fp16.onnx"
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.database.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "TMDB_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.tmdb.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "ADMIN_BOOTSTRAP_TOKEN"
        value_source {
          secret_key_ref {
            secret  = data.google_secret_manager_secret.admin_bootstrap.secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "models"
        mount_path = "/models"
      }

      startup_probe {
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 12
        http_get {
          path = "/v1/health"
          port = 8000
        }
      }
    }

    volumes {
      name = "models"
      gcs {
        bucket    = google_storage_bucket.models.name
        read_only = true
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_service_iam_member" "public_api" {
  location = google_cloud_run_v2_service.api.location
  service  = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "scheduled" {
  for_each = local.jobs
  name     = "slatesignal-${each.key}"
  location = var.region

  template {
    template {
      service_account = google_service_account.runtime.email
      timeout         = "3600s"
      max_retries     = 2

      containers {
        image   = var.api_image
        command = ["slatesignal"]
        args    = each.value.args

        resources {
          limits = {
            cpu    = "2"
            memory = each.key == "imdb" ? "4Gi" : "2Gi"
          }
        }

        env {
          name  = "BERT_ONNX_PATH"
          value = "/models/bert-base-uncased-fp16.onnx"
        }
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret.database.secret_id
              version = "latest"
            }
          }
        }
        env {
          name = "TMDB_API_TOKEN"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret.tmdb.secret_id
              version = "latest"
            }
          }
        }

        volume_mounts {
          name       = "models"
          mount_path = "/models"
        }
      }

      volumes {
        name = "models"
        gcs {
          bucket    = google_storage_bucket.models.name
          read_only = true
        }
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "scheduler_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "scheduled" {
  for_each  = local.jobs
  name      = "slatesignal-${each.key}"
  region    = var.region
  schedule  = each.value.schedule
  time_zone = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/slatesignal-${each.key}:run"
    body        = base64encode("{}")

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [
    google_cloud_run_v2_job.scheduled,
    google_project_iam_member.scheduler_invoker,
  ]
}
