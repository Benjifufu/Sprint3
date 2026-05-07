# =============================================================================
# EC2 Servidores web Django (2 instancias, una por AZ)
#
# Ambas instancias corren el mismo userdata que:
#   1. Clona el repo (sprint-3)
#   2. Instala dependencias Python
#   3. Escribe el .env con las IPs privadas de las 3 BDs
#   4. Arranca gunicorn como servicio systemd
#
# NOTA: migrate y seed_demo solo corren en web1 (flag IS_PRIMARY_WEB=true).
# web2 solo instala y arranca; las migraciones ya están aplicadas al compartir
# la misma BD.
# =============================================================================

locals {
  web_common = {
    db_password         = var.db_password
    accounts_db_host    = aws_instance.accounts_db.private_ip
    db_primary_host     = aws_instance.db_primary.private_ip
    db_replica_host     = aws_instance.db_replica.private_ip
    auth0_domain        = var.auth0_domain
    auth0_client_id     = var.auth0_client_id
    auth0_client_secret = var.auth0_client_secret
    github_repo         = var.github_repo
    github_branch       = var.github_branch
  }
}

# --- Web 1  (us-east-1c, corre migrate + seed) ---
resource "aws_instance" "web1" {
  ami                    = var.ami_id
  instance_type          = var.web_instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.public_c.id
  vpc_security_group_ids = [aws_security_group.app.id]

  user_data = base64encode(templatefile(
    "${path.module}/userdata/web.sh",
    merge(local.web_common, { is_primary_web = "true" })
  ))

  # Espera a que las BDs estén provisionadas antes de intentar el migrate
  depends_on = [
    aws_instance.accounts_db,
    aws_instance.db_primary,
    aws_instance.db_replica,
  ]

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "${var.project}-web-1" }
}

# --- Web 2  (us-east-1d, solo instala y arranca) ---
resource "aws_instance" "web2" {
  ami                    = var.ami_id
  instance_type          = var.web_instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.public_d.id
  vpc_security_group_ids = [aws_security_group.app.id]

  user_data = base64encode(templatefile(
    "${path.module}/userdata/web.sh",
    merge(local.web_common, { is_primary_web = "false" })
  ))

  depends_on = [
    aws_instance.accounts_db,
    aws_instance.db_primary,
    aws_instance.db_replica,
  ]

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "${var.project}-web-2" }
}
