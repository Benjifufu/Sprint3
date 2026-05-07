# =============================================================================
# EC2 Bases de datos (3 instancias)
#
# accounts-db   → accounts_db (usuarios, auditoria)
# db-primary    → monitoring_db primary (writes)
# db-replica    → monitoring_db hot standby (reads, ASR-07)
#
# El userdata de cada instancia instala y configura PostgreSQL automáticamente.
# La replica usa un bucle de reintentos para esperar al primary.
# =============================================================================

# --- accounts-db  (us-east-1c) ---
resource "aws_instance" "accounts_db" {
  ami                    = var.ami_id
  instance_type          = var.db_instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.public_c.id
  vpc_security_group_ids = [aws_security_group.db.id]

  user_data = base64encode(templatefile(
    "${path.module}/userdata/accounts_db.sh",
    { db_password = var.db_password }
  ))

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "${var.project}-accounts-db" }
}

# --- monitoring-primary  (us-east-1c) ---
resource "aws_instance" "db_primary" {
  ami                    = var.ami_id
  instance_type          = var.db_instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.public_c.id
  vpc_security_group_ids = [aws_security_group.db.id]

  user_data = base64encode(templatefile(
    "${path.module}/userdata/db_primary.sh",
    { db_password = var.db_password }
  ))

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = { Name = "${var.project}-db-primary" }
}

# --- monitoring-replica  (us-east-1d) ---
# depends_on garantiza que el primary esté creado antes que la replica
resource "aws_instance" "db_replica" {
  ami                    = var.ami_id
  instance_type          = var.db_instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.public_d.id
  vpc_security_group_ids = [aws_security_group.db.id]

  # Pasa la IP PRIVADA del primary para que pg_basebackup sepa adónde conectar
  user_data = base64encode(templatefile(
    "${path.module}/userdata/db_replica.sh",
    { primary_private_ip = aws_instance.db_primary.private_ip }
  ))

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  depends_on = [aws_instance.db_primary]
  tags       = { Name = "${var.project}-db-replica" }
}
