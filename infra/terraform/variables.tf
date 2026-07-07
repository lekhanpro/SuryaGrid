# ============================================================================
# Variables
# ============================================================================

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1" # Mumbai — closest to Karnataka
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "suryagrid"
}

# ---------- Networking ----------

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# ---------- Database ----------

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro" # Free-tier eligible
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "suryagrid"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "suryagrid"
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

# ---------- Redis ----------

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.micro" # Smallest / cheapest
}

# ---------- ECS ----------

variable "backend_cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU)"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Fargate task memory in MB"
  type        = number
  default     = 1024
}

variable "backend_desired_count" {
  description = "Number of backend ECS tasks"
  type        = number
  default     = 1
}

variable "backend_image" {
  description = "Docker image URI for the backend (ECR repo URI + tag)"
  type        = string
}

# ---------- Domain (optional) ----------

variable "domain_name" {
  description = "Custom domain name (leave empty to use CloudFront/ALB defaults)"
  type        = string
  default     = ""
}
