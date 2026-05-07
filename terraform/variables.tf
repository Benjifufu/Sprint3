variable "aws_region" {
  default = "us-east-1"
}

variable "project" {
  default = "biteco"
}

# Ubuntu 24.04 LTS en us-east-1. Verifica con:
# aws ec2 describe-images --owners 099720109477 --region us-east-1 \
#   --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
#   --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text
variable "ami_id" {
  default = "ami-04b4f1a9cf54c11d0"
}

variable "key_name" {
  description = "Nombre del Key Pair existente en AWS (para SSH de debug)"
  type        = string
}

# Instancias web usan t2.medium segun el informe ASR
variable "web_instance_type" {
  default = "t2.micro"   # cambiar a t2.medium cuando tengas presupuesto
}

variable "db_instance_type" {
  default = "t2.micro"
}

variable "db_password" {
  description = "Password de biteco_user en PostgreSQL"
  type        = string
  sensitive   = true
}

variable "auth0_domain" {
  type = string
}

variable "auth0_client_id" {
  type = string
}

variable "auth0_client_secret" {
  type      = string
  sensitive = true
}

# URL de tu repo GitHub (rama sprint-3)
variable "github_repo" {
  description = "URL del repo a clonar. Ej: https://github.com/tu-user/App_Biteco.git"
  type        = string
}

variable "github_branch" {
  default = "sprint-3"
}
