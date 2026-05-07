#!/bin/bash
# monitoring-db-primary: PostgreSQL + monitoring_db + streaming replication
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y postgresql-16 postgresql-contrib-16

systemctl enable postgresql
systemctl start postgresql

# Crear usuario de app + BD + usuario de replicacion
sudo -u postgres psql <<SQL
CREATE USER biteco_user WITH PASSWORD '${db_password}';
CREATE DATABASE monitoring_db OWNER biteco_user;
ALTER USER biteco_user WITH SUPERUSER;
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicator_pass';
SQL

PG_CONF=/etc/postgresql/16/main/postgresql.conf
PG_HBA=/etc/postgresql/16/main/pg_hba.conf

# Habilitar streaming replication
cat >> $PG_CONF <<EOF

# Streaming Replication (ASR-07)
listen_addresses = '*'
wal_level = replica
max_wal_senders = 5
wal_keep_size = 1GB
hot_standby = on
EOF

# Permitir conexiones de app (VPC) + replica (VPC)
cat >> $PG_HBA <<EOF
host  replication  replicator   10.20.0.0/16  md5
host  all          biteco_user  10.20.0.0/16  md5
EOF

systemctl restart postgresql
echo "primary-ok" > /tmp/db_primary_ready.txt
