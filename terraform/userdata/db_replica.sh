#!/bin/bash
# monitoring-db-replica: hot standby via streaming replication
# Espera al primary en un bucle (el primary puede tardar 2-3 min en arrancar).
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y postgresql-16 postgresql-contrib-16

PRIMARY_IP="${primary_private_ip}"

systemctl stop postgresql || true

# Limpiar el data dir para recibir el base backup
rm -rf /var/lib/postgresql/16/main/*

# Reintentar pg_basebackup hasta que el primary esté listo (max 20 intentos, 30s c/u)
for i in $(seq 1 20); do
  echo "Intento $i: conectando a primary $PRIMARY_IP ..."
  if PGPASSWORD=replicator_pass pg_basebackup \
      -h "$PRIMARY_IP" -U replicator \
      -D /var/lib/postgresql/16/main \
      -P -R -X stream -C -S replica_slot_1 2>/tmp/basebackup_err.txt; then
    echo "Base backup exitoso en intento $i"
    break
  fi
  cat /tmp/basebackup_err.txt
  sleep 30
done

# Fix permisos (pg_basebackup los deja bien, pero por las dudas)
chown -R postgres:postgres /var/lib/postgresql/16/main
chmod 700 /var/lib/postgresql/16/main

# El flag -R ya creó standby.signal y postgresql.auto.conf con primary_conninfo
# Solo aseguramos que escuche en *
PG_CONF=/etc/postgresql/16/main/postgresql.conf
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" $PG_CONF

# Permitir conexiones de lectura desde la VPC
echo "host  all  biteco_user  10.20.0.0/16  md5" >> /etc/postgresql/16/main/pg_hba.conf

systemctl enable postgresql
systemctl start postgresql
echo "replica-ok" > /tmp/db_replica_ready.txt
