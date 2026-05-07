# =============================================================================
# BITE.co Sprint 3 — Infraestructura completa en AWS
#
# Arquitectura (fiel al informe_ASR.docx):
#   Internet → ALB (us-east-1c, us-east-1d)
#                ├── EC2 Web-1 (Django, us-east-1c)
#                └── EC2 Web-2 (Django, us-east-1d)
#                         │
#              ┌──────────┼──────────────┐
#              ▼                         ▼
#   EC2 accounts-db         EC2 monitoring-primary
#   (accounts_db)              (monitoring_db)
#                                    │ streaming replication
#                              EC2 monitoring-replica
#                               (hot standby, reads)
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project   = "BITE.co"
      Sprint    = "3"
      ManagedBy = "Terraform"
    }
  }
}

# =============================================================================
# NETWORKING
# =============================================================================

resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "${var.project}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project}-igw" }
}

# Dos subnets públicas (mismas AZs que el diagrama del informe)
resource "aws_subnet" "public_c" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.1.0/24"
  availability_zone       = "${var.aws_region}c"
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project}-subnet-c" }
}

resource "aws_subnet" "public_d" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.2.0/24"
  availability_zone       = "${var.aws_region}d"
  map_public_ip_on_launch = true
  tags                    = { Name = "${var.project}-subnet-d" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${var.project}-rt" }
}

resource "aws_route_table_association" "c" {
  subnet_id      = aws_subnet.public_c.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "d" {
  subnet_id      = aws_subnet.public_d.id
  route_table_id = aws_route_table.public.id
}

# =============================================================================
# SECURITY GROUPS
# Cadena: Internet → sg_alb → sg_app → sg_db  (ASR-01)
# =============================================================================

# ALB: acepta tráfico web desde Internet
resource "aws_security_group" "alb" {
  name        = "${var.project}-sg-alb"
  description = "ALB - HTTP desde Internet"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.project}-sg-alb" }
}

# App: solo acepta tráfico desde el ALB + SSH para debug
resource "aws_security_group" "app" {
  name        = "${var.project}-sg-app"
  description = "Django EC2 - solo desde ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Gunicorn desde ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  ingress {
    description = "SSH debug"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.project}-sg-app" }
}

# DB: acepta Postgres desde app + desde otras DBs (replicación)
resource "aws_security_group" "db" {
  name        = "${var.project}-sg-db"
  description = "PostgreSQL - desde app y replicacion"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Postgres desde Django"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
  ingress {
    description = "Streaming replication entre DBs"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.20.0.0/16"]
  }
  ingress {
    description = "SSH debug"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${var.project}-sg-db" }
}

# =============================================================================
# APPLICATION LOAD BALANCER  (ASR-07 - disponibilidad Multi-AZ)
# =============================================================================

resource "aws_lb" "main" {
  name               = "${var.project}-alb"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_c.id, aws_subnet.public_d.id]
  tags               = { Name = "${var.project}-alb" }
}

resource "aws_lb_target_group" "app" {
  name     = "${var.project}-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/health-check/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
    matcher             = "200"
  }
  tags = { Name = "${var.project}-tg" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# Registrar las 2 EC2 web en el target group
resource "aws_lb_target_group_attachment" "web1" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.web1.id
  port             = 8080
}

resource "aws_lb_target_group_attachment" "web2" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.web2.id
  port             = 8080
}
