# GUÍA MAESTRA DE DESPLIEGUE — BITE.co Sprint 3
# Desde clonar el repo hasta app corriendo detrás del ALB
# =========================================================
# ORDEN:
#   1. CloudShell → terraform apply
#   2. EC2 Instance Connect db-primary → fix pg_hba.conf
#   3. EC2 Instance Connect db-replica → streaming replication
#   4. EC2 Instance Connect web-1 → clonar, instalar, migrate, runserver
#   5. EC2 Instance Connect web-2 → clonar, instalar, runserver
#   6. Auth0 Dashboard → registrar callback URL del ALB
# =========================================================


# ==============================================================
# ANTES DE EMPEZAR — valores que necesitas tener a mano
# ==============================================================
# De manage.auth0.com → Applications → tu app → Settings:
#   AUTH0_DOMAIN        ej: dev-igx7tk0bt4exh34d.us.auth0.com
#   AUTH0_CLIENT_ID     string ~32 chars
#   AUTH0_CLIENT_SECRET string largo
#
# De AWS → EC2 → Key Pairs:
#   Nombre de tu Key Pair (ej: vockey o llave-biteco)
#   Si no tienes uno, créalo y descarga el .pem ANTES de continuar
#
# Tu repo GitHub debe tener el código de BiteCo subido con deployment.tf en la raíz


# ==============================================================
# PASO 1 — CLOUDSHELL: clonar repo y lanzar Terraform
# ==============================================================
# Abre AWS CloudShell (ícono terminal en la barra superior de AWS Console)

git clone https://github.com/TU-USUARIO/Sprint3.git
cd Sprint3

# Editar el key_name en deployment.tf si no es "vockey"
# nano deployment.tf  → cambia default = "vockey" por tu Key Pair real

terraform init
terraform apply
# Escribe "yes" cuando lo pida. Tarda ~3-5 minutos.

# Al terminar guarda TODOS los outputs en un bloc de notas:
terraform output
#   alb_url                  = "http://biteco-alb-XXXX.us-east-1.elb.amazonaws.com"
#   auth0_callback_url       = "http://biteco-alb-XXXX.../complete/auth0"
#   accounts_db_private_ip   = "172.31.X.X"
#   db_primary_private_ip    = "172.31.X.X"
#   db_replica_private_ip    = "172.31.X.X"
#   ssh_web1                 = "ssh -i TU_KEY.pem ubuntu@3.X.X.X"
#   ssh_web2                 = "ssh -i TU_KEY.pem ubuntu@3.X.X.X"


# ==============================================================
# PASO 2 — DB-PRIMARY: fix pg_hba.conf para la réplica
# ==============================================================
# AWS Console → EC2 → Instances → biteco-db-primary
# → Connect → EC2 Instance Connect → Connect

# Dentro del primary (reemplaza la IP de la réplica con db_replica_private_ip):
echo "host replication replicator <DB_REPLICA_PRIVATE_IP>/32 md5" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
sudo systemctl restart postgresql

# Verifica que PostgreSQL está corriendo:
sudo systemctl status postgresql | grep Active
# Debe mostrar: Active: active (running)

# Cierra esta terminal


# ==============================================================
# PASO 3 — DB-REPLICA: configurar streaming replication
# ==============================================================
# AWS Console → EC2 → Instances → biteco-db-replica
# → Connect → EC2 Instance Connect → Connect

# Espera ~2 minutos después del terraform apply antes de hacer esto

sudo systemctl stop postgresql

sudo rm -rf /var/lib/postgresql/16/main
sudo mkdir -p /var/lib/postgresql/16/main
sudo chown postgres:postgres /var/lib/postgresql/16/main
sudo chmod 700 /var/lib/postgresql/16/main

# Reemplaza con tu db_primary_private_ip real:
PRIMARY_IP=<DB_PRIMARY_PRIVATE_IP>

sudo -u postgres PGPASSWORD=replicator_pass pg_basebackup \
  -h $PRIMARY_IP -U replicator \
  -D /var/lib/postgresql/16/main \
  -P -R -X stream -C -S replica_slot_1
# Si da error de conexión, espera 30s y repite solo el pg_basebackup

sudo chown -R postgres:postgres /var/lib/postgresql/16/main
sudo chmod 700 /var/lib/postgresql/16/main

echo "listen_addresses='*'" | sudo tee -a /etc/postgresql/16/main/postgresql.conf
echo "host all biteco_user 0.0.0.0/0 md5" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf

# Si falla el start por directorio no vacío, crear standby.signal manualmente:
sudo touch /var/lib/postgresql/16/main/standby.signal
sudo chown postgres:postgres /var/lib/postgresql/16/main/standby.signal

sudo systemctl start postgresql

# Verificar que está en modo réplica (debe retornar "t"):
sudo -u postgres psql -c "SELECT pg_is_in_recovery();"

# Cierra esta terminal


# ==============================================================
# PASO 4 — WEB-1: clonar, instalar, migrate y runserver
# ==============================================================
# AWS Console → EC2 → Instances → biteco-web-1
# → Connect → EC2 Instance Connect → Connect

cd /home/ubuntu
git clone https://github.com/TU-USUARIO/Sprint3.git
cd Sprint3

sudo apt-get update -y
sudo apt-get install -y python3-venv

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Crear el .env con los valores reales de tus outputs y Auth0:
cat > .env <<EOF
DEBUG=False
SECRET_KEY=cambia-esto-por-algo-aleatorio-largo-aqui
ALLOWED_HOSTS=*

DB_NAME_DEFAULT=accounts_db
DB_USER=biteco_user
DB_PASSWORD=biteco_pass
DB_HOST_DEFAULT=<ACCOUNTS_DB_PRIVATE_IP>
DB_PORT=5432

DB_NAME_MONITORING=monitoring_db
DB_HOST_MONITORING_PRIMARY=<DB_PRIMARY_PRIVATE_IP>
DB_HOST_MONITORING_REPLICA=<DB_REPLICA_PRIVATE_IP>

AUTH0_DOMAIN=<TU_AUTH0_DOMAIN>
AUTH0_CLIENT_ID=<TU_AUTH0_CLIENT_ID>
AUTH0_CLIENT_SECRET=<TU_AUTH0_CLIENT_SECRET>
EOF

export $(grep -v '^#' .env | xargs)

# Aplicar migraciones (solo en web-1, NO repetir en web-2)
python manage.py migrate
python manage.py migrate --database=monitoring

# Cargar datos de demo (opcional)
python manage.py seed_demo

# Arrancar el servidor
nohup python manage.py runserver 0.0.0.0:8000 &> /tmp/django.log &

sleep 5

# Verificar que está corriendo:
curl http://localhost:8000/health-check/
# Debe retornar: OK

# Cierra esta terminal


# ==============================================================
# PASO 5 — WEB-2: clonar, instalar y runserver (sin migrate)
# ==============================================================
# AWS Console → EC2 → Instances → biteco-web-2
# → Connect → EC2 Instance Connect → Connect

cd /home/ubuntu
git clone https://github.com/TU-USUARIO/Sprint3.git
cd Sprint3

sudo apt-get update -y
sudo apt-get install -y python3-venv

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Mismo .env que web-1 (mismos valores exactos):
cat > .env <<EOF
DEBUG=False
SECRET_KEY=cambia-esto-por-algo-aleatorio-largo-aqui
ALLOWED_HOSTS=*

DB_NAME_DEFAULT=accounts_db
DB_USER=biteco_user
DB_PASSWORD=biteco_pass
DB_HOST_DEFAULT=<ACCOUNTS_DB_PRIVATE_IP>
DB_PORT=5432

DB_NAME_MONITORING=monitoring_db
DB_HOST_MONITORING_PRIMARY=<DB_PRIMARY_PRIVATE_IP>
DB_HOST_MONITORING_REPLICA=<DB_REPLICA_PRIVATE_IP>

AUTH0_DOMAIN=<TU_AUTH0_DOMAIN>
AUTH0_CLIENT_ID=<TU_AUTH0_CLIENT_ID>
AUTH0_CLIENT_SECRET=<TU_AUTH0_CLIENT_SECRET>
EOF

export $(grep -v '^#' .env | xargs)

# NO hacer migrate — ya fue aplicado desde web-1
# Arrancar directamente:
nohup python manage.py runserver 0.0.0.0:8000 &> /tmp/django.log &

sleep 5

# Verificar:
curl http://localhost:8000/health-check/
# Debe retornar: OK

# Cierra esta terminal


# ==============================================================
# PASO 6 — AUTH0 DASHBOARD: registrar la URL del ALB
# ==============================================================
# 1. manage.auth0.com → Applications → tu app → Settings
#
# 2. Allowed Callback URLs → agrega:
#    http://biteco-alb-XXXX.us-east-1.elb.amazonaws.com/complete/auth0
#
# 3. Allowed Logout URLs → agrega:
#    http://biteco-alb-XXXX.us-east-1.elb.amazonaws.com/
#
# 4. Allowed Web Origins → agrega:
#    http://biteco-alb-XXXX.us-east-1.elb.amazonaws.com
#
# 5. Save Changes (botón al final de la página)
#
# Para crear un usuario de prueba:
#   manage.auth0.com → User Management → Users → Create User
#   Email + Password → Create
#   Luego úsalo para hacer login en la app


# ==============================================================
# PASO 7 — VERIFICACIÓN FINAL
# ==============================================================

# Health check del ALB (desde cualquier terminal o navegador):
curl http://biteco-alb-XXXX.us-east-1.elb.amazonaws.com/health-check/
# Debe retornar: OK

# Abrir en el navegador:
# http://biteco-alb-XXXX.us-east-1.elb.amazonaws.com/
# → Landing page con botón "Ingresar con Auth0"
# → Login con tu usuario Auth0
# → Dashboard de BiteCo con Reportes y ASR Hub


# ==============================================================
# REFERENCIA RÁPIDA — Comandos útiles
# ==============================================================

# Ver logs del servidor Django (en web-1 o web-2):
tail -f /tmp/django.log

# Reiniciar el servidor si se cayó:
source venv/bin/activate
pkill -f "manage.py runserver"
export $(grep -v '^#' .env | xargs)
nohup python manage.py runserver 0.0.0.0:8000 &> /tmp/django.log &

# Verificar que el puerto 8000 está escuchando:
ss -tlnp | grep 8000

# Ver el .env actual:
cat .env

# Verificar replicación en db-primary:
sudo -u postgres psql -c "SELECT client_addr, state FROM pg_stat_replication;"

# Verificar que db-replica está en standby:
sudo -u postgres psql -c "SELECT pg_is_in_recovery();"
# Debe retornar: t


# ==============================================================
# NOTA IMPORTANTE — Si reinicias las instancias EC2
# ==============================================================
# El runserver NO persiste entre reinicios. Si apagas y prendes
# las instancias web, debes volver a correr:
#
#   cd /home/ubuntu/Sprint3
#   source venv/bin/activate
#   export $(grep -v '^#' .env | xargs)
#   nohup python manage.py runserver 0.0.0.0:8000 &> /tmp/django.log &
