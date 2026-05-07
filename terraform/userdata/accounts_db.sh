#!/bin/bash
# accounts-db: instala PostgreSQL + crea accounts_db
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y postgresql-16 postgresql-contrib-16

systemctl enable postgresql
systemctl start postgresql

# Crear usuario y BD
sudo -u postgres psql <<SQL
CREATE USER biteco_user WITH PASSWORD '${db_password}';
CREATE DATABASE accounts_db OWNER biteco_user;
ALTER USER biteco_user WITH SUPERUSER;
SQL

# Permitir conexiones desde toda la VPC (10.20.0.0/16)
PG_CONF=/etc/postgresql/16/main/postgresql.conf
PG_HBA=/etc/postgresql/16/main/pg_hba.conf

sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" $PG_CONF
echo "host  all  biteco_user  10.20.0.0/16  md5" >> $PG_HBA

systemctl restart postgresql
echo "accounts-db OK" > /tmp/db_ready.txt
