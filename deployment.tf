# ***************** Universidad de los Andes ***********************
# ****** Departamento de Ingeniería de Sistemas y Computación ******
# ********** Arquitectura y diseño de Software - ISIS2503 **********
#
# Infraestructura para el proyecto BITE.co — Sprint 3
#
# Elementos a desplegar en AWS:
# 1. Grupos de seguridad:
#    - biteco-traffic-alb    (puerto 80 público)
#    - biteco-traffic-django (puerto 8000 desde ALB + SSH)
#    - biteco-traffic-db     (puerto 5432 + SSH)
#
# 2. Instancias EC2 Base de Datos:
#    - biteco-accounts-db   (PostgreSQL: accounts_db)
#    - biteco-db-primary    (PostgreSQL: monitoring_db, primary)
#    - biteco-db-replica    (PostgreSQL: monitoring_db, hot standby)
#
# 3. Instancias EC2 Web:
#    - biteco-web-1  (Django runserver puerto 8000, us-east-1c)
#    - biteco-web-2  (Django runserver puerto 8000, us-east-1d)
#
# 4. Application Load Balancer:
#    - biteco-alb → target group puerto 8000 → web-1 y web-2
# ******************************************************************

# Variable. Define la región de AWS donde se desplegará la infraestructura.
variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

# Variable. Define el prefijo usado para nombrar los recursos en AWS.
variable "project_prefix" {
  description = "Prefix used for naming AWS resources"
  type        = string
  default     = "biteco"
}

# Variable. Define el tipo de instancia EC2 para todos los hosts.
variable "instance_type" {
  description = "EC2 instance type for all hosts"
  type        = string
  default     = "t2.micro"
}

# Variable. Par de claves SSH para acceder a las instancias EC2.
# IMPORTANTE: reemplaza "vockey" con el nombre real de tu Key Pair en AWS.
variable "key_name" {
  description = "Name of the EC2 Key Pair for SSH access"
  type        = string
  default     = "vockey"
}

# Proveedor. Define el proveedor de infraestructura (AWS) y la región.
provider "aws" {
  region = var.region
}

# Variables locales usadas en la configuración de Terraform.
locals {
  project_name = "${var.project_prefix}-app"

  common_tags = {
    Project   = local.project_name
    ManagedBy = "Terraform"
  }
}

# Data Source. Busca la AMI más reciente de Ubuntu 24.04 usando los filtros especificados.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Data Source. Obtiene las subnets de la VPC por defecto (multi-AZ para el ALB).
data "aws_subnets" "default" {
  filter {
    name   = "defaultForAz"
    values = ["true"]
  }
}

# Data Source. Obtiene la VPC por defecto.
data "aws_vpc" "default" {
  default = true
}

# ==================== SECURITY GROUPS ====================

# Recurso. Grupo de seguridad para el Application Load Balancer (puerto 80 público).
resource "aws_security_group" "traffic_alb" {
  name        = "${var.project_prefix}-traffic-alb"
  description = "Allow HTTP traffic to ALB from Internet"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP from Internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-traffic-alb"
  })
}

# Recurso. Grupo de seguridad para los servidores web Django (puerto 8000 y SSH).
resource "aws_security_group" "traffic_django" {
  name        = "${var.project_prefix}-traffic-django"
  description = "Allow Django on port 8000 from ALB and SSH"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Django runserver from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.traffic_alb.id]
  }

  ingress {
    description = "SSH access from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-traffic-django"
  })
}

# Recurso. Grupo de seguridad para las bases de datos PostgreSQL (5432 y SSH).
resource "aws_security_group" "traffic_db" {
  name        = "${var.project_prefix}-traffic-db"
  description = "Allow PostgreSQL from Django servers and replication between DBs"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "PostgreSQL from Django servers"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.traffic_django.id]
  }

  ingress {
    description = "Streaming replication between DB instances"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    self        = true
  }

  ingress {
    description = "SSH access from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-traffic-db"
  })
}

# ==================== BASE DE DATOS: accounts-db ====================

# Recurso. Instancia EC2 para la base de datos de cuentas (usuarios y auditoría).
# Instala PostgreSQL y crea accounts_db con biteco_user.
resource "aws_instance" "accounts_db" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  associate_public_ip_address = true
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.traffic_db.id]

  user_data = <<-EOT
              #!/bin/bash
              sudo apt-get update -y
              sudo apt-get install -y postgresql postgresql-contrib

              sudo -u postgres psql -c "CREATE USER biteco_user WITH PASSWORD 'biteco_pass';"
              sudo -u postgres createdb -O biteco_user accounts_db
              sudo -u postgres psql -c "ALTER USER biteco_user WITH SUPERUSER;"

              echo "listen_addresses='*'" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
              echo "host all biteco_user 0.0.0.0/0 md5" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
              sudo service postgresql restart
              EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-accounts-db"
    Role = "database-accounts"
  })
}

# ==================== BASE DE DATOS: monitoring-primary ====================

# Recurso. Instancia EC2 para la base de datos de monitoreo primaria (writes).
# Habilita streaming replication para que db-replica pueda conectarse.
resource "aws_instance" "db_primary" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  associate_public_ip_address = true
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.traffic_db.id]

  user_data = <<-EOT
              #!/bin/bash
              sudo apt-get update -y
              sudo apt-get install -y postgresql postgresql-contrib

              sudo -u postgres psql -c "CREATE USER biteco_user WITH PASSWORD 'biteco_pass';"
              sudo -u postgres createdb -O biteco_user monitoring_db
              sudo -u postgres psql -c "ALTER USER biteco_user WITH SUPERUSER;"
              sudo -u postgres psql -c "CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicator_pass';"

              echo "listen_addresses='*'" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
              echo "wal_level=replica" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
              echo "max_wal_senders=5" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
              echo "wal_keep_size=1GB" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
              echo "host all biteco_user 0.0.0.0/0 md5" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
              echo "host replication replicator 0.0.0.0/0 md5" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
              sudo service postgresql restart
              EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-db-primary"
    Role = "database-primary"
  })
}

# ==================== BASE DE DATOS: monitoring-replica ====================

# Recurso. Instancia EC2 para la base de datos de monitoreo réplica (reads).
# Instala herramientas base; la configuración de replicación se completa
# manualmente vía SSH (ver Guía de Comandos — Paso 4).
resource "aws_instance" "db_replica" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  associate_public_ip_address = true
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.traffic_db.id]

  user_data = <<-EOT
              #!/bin/bash
              sudo apt-get update -y
              sudo apt-get install -y postgresql postgresql-contrib python3-pip git build-essential libpq-dev python3-dev
              EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-db-replica"
    Role = "database-replica"
  })

  depends_on = [aws_instance.db_primary]
}

# ==================== SERVIDORES WEB ====================

# Recurso. Instancia EC2 Web-1 para la aplicación Django BiteCo.
# Instala herramientas base; la app se clona y arranca manualmente vía SSH.
resource "aws_instance" "web1" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  associate_public_ip_address = true
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.traffic_django.id]

  user_data = <<-EOT
              #!/bin/bash
              sudo apt-get update -y
              sudo apt-get install -y python3-pip git build-essential libpq-dev python3-dev
              EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-web-1"
    Role = "web-server"
  })

  depends_on = [aws_instance.accounts_db, aws_instance.db_primary]
}

# Recurso. Instancia EC2 Web-2 para la aplicación Django BiteCo.
# Instala herramientas base; la app se clona y arranca manualmente vía SSH.
resource "aws_instance" "web2" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  associate_public_ip_address = true
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.traffic_django.id]

  user_data = <<-EOT
              #!/bin/bash
              sudo apt-get update -y
              sudo apt-get install -y python3-pip git build-essential libpq-dev python3-dev
              EOT

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-web-2"
    Role = "web-server"
  })

  depends_on = [aws_instance.accounts_db, aws_instance.db_primary]
}

# ==================== APPLICATION LOAD BALANCER ====================

# Recurso. Application Load Balancer que distribuye tráfico entre Web-1 y Web-2.
resource "aws_lb" "main" {
  name               = "${var.project_prefix}-alb"
  load_balancer_type = "application"
  security_groups    = [aws_security_group.traffic_alb.id]
  subnets            = data.aws_subnets.default.ids

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-alb"
  })
}

# Recurso. Target Group del ALB apuntando al puerto 8000 de Django.
# El health check usa el endpoint /health-check/ de BiteCo.
resource "aws_lb_target_group" "app" {
  name     = "${var.project_prefix}-tg"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    path                = "/health-check/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
    matcher             = "200"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_prefix}-tg"
  })
}

# Recurso. Listener HTTP del ALB en puerto 80 con forward al target group.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# Recurso. Registrar Web-1 en el target group del ALB (puerto 8000).
resource "aws_lb_target_group_attachment" "web1" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.web1.id
  port             = 8000
}

# Recurso. Registrar Web-2 en el target group del ALB (puerto 8000).
resource "aws_lb_target_group_attachment" "web2" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.web2.id
  port             = 8000
}

# ==================== OUTPUTS ====================

# Salida. URL pública del ALB — usar en Auth0 callback y en el .env.
output "alb_url" {
  description = "URL publica del ALB — pegar en Auth0 Allowed Callback URLs y en ALLOWED_HOSTS"
  value       = "http://${aws_lb.main.dns_name}"
}

# Salida. URL exacta de callback para Auth0 Dashboard.
output "auth0_callback_url" {
  description = "Pegar en Auth0 → Application → Allowed Callback URLs"
  value       = "http://${aws_lb.main.dns_name}/complete/auth0"
}

# Salida. Comando SSH para conectarse a Web-1.
output "ssh_web1" {
  description = "SSH a Web-1"
  value       = "ssh -i TU_KEY.pem ubuntu@${aws_instance.web1.public_ip}"
}

# Salida. Comando SSH para conectarse a Web-2.
output "ssh_web2" {
  description = "SSH a Web-2"
  value       = "ssh -i TU_KEY.pem ubuntu@${aws_instance.web2.public_ip}"
}

# Salida. IP privada de accounts-db (valor para DB_HOST_DEFAULT en el .env).
output "accounts_db_private_ip" {
  description = "IP privada accounts-db → DB_HOST_DEFAULT en .env"
  value       = aws_instance.accounts_db.private_ip
}

# Salida. IP privada del monitoring primary (valor para DB_HOST_MONITORING_PRIMARY en el .env).
output "db_primary_private_ip" {
  description = "IP privada monitoring-primary → DB_HOST_MONITORING_PRIMARY en .env"
  value       = aws_instance.db_primary.private_ip
}

# Salida. IP privada de la réplica (valor para DB_HOST_MONITORING_REPLICA en el .env).
output "db_replica_private_ip" {
  description = "IP privada monitoring-replica → DB_HOST_MONITORING_REPLICA en .env"
  value       = aws_instance.db_replica.private_ip
}
