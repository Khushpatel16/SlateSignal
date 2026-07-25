variable "project_id" {
  description = "GCP project that owns Cloud Run, Scheduler, GCS, and secrets."
  type        = string
}

variable "region" {
  description = "Primary Cloud Run region."
  type        = string
  default     = "us-west1"
}

variable "api_image" {
  description = "Immutable API image URI, ideally pinned by digest."
  type        = string
}

variable "web_origin" {
  description = "Final Vercel or custom HTTPS origin."
  type        = string
}

variable "database_secret_id" {
  description = "Existing Secret Manager secret containing the Neon SQLAlchemy URL."
  type        = string
  default     = "slatesignal-database-url"
}

variable "tmdb_secret_id" {
  description = "Existing Secret Manager secret containing the TMDB read token."
  type        = string
  default     = "slatesignal-tmdb-token"
}

variable "admin_bootstrap_secret_id" {
  description = "Existing one-time admin bootstrap secret."
  type        = string
  default     = "slatesignal-admin-bootstrap-token"
}

variable "admin_email" {
  description = "Email eligible for one-time admin provisioning."
  type        = string
}
