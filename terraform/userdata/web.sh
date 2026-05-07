#!/bin/bash
# EC2 Django: clona el repo, instala deps, escribe .env, arranca gunicorn.
# Si IS_PRIMARY_WEB=true también corre migrate + seed_demo.
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y python3-pip python3-venv git postgresql-client

# ---- Clonar repo ----
git clone "${github_repo}" -b "${github_branch}" /opt/biteco
cd /opt/biteco

# ---- Virtualenv ----
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt gunicorn

# ---- .env ----
cat > /opt/biteco/.env <<EOF
DEBUG=False
ALLOWED_HOSTS=*
SECRET_KEY=$(openssl rand -hex 32)

DB_NAME_DEFAULT=accounts_db
DB_USER=biteco_user
DB_PASSWORD=${db_password}
DB_HOST_DEFAULT=${accounts_db_host}
DB_PORT=5432

DB_NAME_MONITORING=monitoring_db
DB_HOST_MONITORING_PRIMARY=${db_primary_host}
DB_HOST_MONITORING_REPLICA=${db_replica_host}

AUTH0_DOMAIN=${auth0_domain}
AUTH0_CLIENT_ID=${auth0_client_id}
AUTH0_CLIENT_SECRET=${auth0_client_secret}
EOF

# ---- Migraciones (solo en web1) ----
if [ "${is_primary_web}" = "true" ]; then
  # Esperar a que las BDs acepten conexiones
  for i in $(seq 1 15); do
    if pg_isready -h "${accounts_db_host}" -U biteco_user -d accounts_db -q; then
      break
    fi
    echo "Esperando accounts_db... intento $i"
    sleep 20
  done
  for i in $(seq 1 15); do
    if pg_isready -h "${db_primary_host}" -U biteco_user -d monitoring_db -q; then
      break
    fi
    echo "Esperando monitoring_db... intento $i"
    sleep 20
  done

  set -a && source /opt/biteco/.env && set +a
  python manage.py migrate
  python manage.py migrate --database=monitoring
  python manage.py seed_demo
  python manage.py collectstatic --noinput
fi

# ---- Servicio systemd ----
cat > /etc/systemd/system/biteco.service <<EOF
[Unit]
Description=BITE.co Django
After=network.target

[Service]
WorkingDirectory=/opt/biteco
EnvironmentFile=/opt/biteco/.env
ExecStart=/opt/biteco/.venv/bin/gunicorn bitecoapp.wsgi:application \
  --bind 0.0.0.0:8080 \
  --workers 3 \
  --timeout 60 \
  --access-logfile /var/log/biteco.log \
  --error-logfile /var/log/biteco.log
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable biteco
systemctl start biteco
echo "web-ok" > /tmp/web_ready.txt
