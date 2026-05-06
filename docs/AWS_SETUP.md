# AWS Setup — Despliegue Sprint 3

Guía paso a paso para desplegar la app en AWS exactamente como dice el
`informe_ASR.docx`: 2 EC2 Django detrás de un ALB Multi-AZ, 1 EC2 Auth
service (Auth0), 1 RDS-style EC2 con PostgreSQL Primary y 1 EC2 con
PostgreSQL Replica (Streaming Replication).

**Tiempo estimado**: ~45 min

---

## Arquitectura objetivo

```
                                Auth0 (SaaS)
                                     │
   Internet ─────► ALB Multi-AZ ─────┴──┐
                   (us-east-1c, 1d)     │
                          │             │
              ┌───────────┴──────┐      │
              ▼                  ▼      │
         EC2 Web 1          EC2 Web 2   │
         t2.micro           t2.micro    │
         Django+gunicorn    Django+gunicorn
         us-east-1c         us-east-1d
              │                  │
              ├──── reads ───────┘
              │       │
              ▼       ▼
         RDS Primary   RDS Replica
         monitoring-   monitoring-
         db-primary    db-replica
         t2.micro      t2.micro
              │            ▲
              └─ Streaming ┘
                Replication

         + 1 EC2 accounts-db (auth, RegistroAuditoria)
         + 1 EC2 JMeter (para pruebas)
```

---

## 0. Pre-requisitos

```bash
# AWS CLI configurado
aws configure
aws sts get-caller-identity   # confirmar identity

# Si usas AWS Academy: importar las credenciales LabSession
# Si usas IAM personal: necesitas EC2, RDS, ELB, IAM permissions
```

---

## 1. VPC + Networking

```bash
# Variables que vamos a reusar
export AWS_REGION=us-east-1
export PROJECT=biteco

# 1.1 Crear VPC
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.20.0.0/16 \
  --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$PROJECT-vpc}]" \
  --query 'Vpc.VpcId' --output text)
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# 1.2 Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$PROJECT-igw}]" \
  --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# 1.3 Subnets (2 publicas en us-east-1c y 1d)
SUBNET_C=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.20.1.0/24 \
  --availability-zone us-east-1c \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT-subnet-c}]" \
  --query 'Subnet.SubnetId' --output text)
SUBNET_D=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.20.2.0/24 \
  --availability-zone us-east-1d \
  --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT-subnet-d}]" \
  --query 'Subnet.SubnetId' --output text)
aws ec2 modify-subnet-attribute --subnet-id $SUBNET_C --map-public-ip-on-launch
aws ec2 modify-subnet-attribute --subnet-id $SUBNET_D --map-public-ip-on-launch

# 1.4 Route Table
RT_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $RT_ID \
  --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --subnet-id $SUBNET_C --route-table-id $RT_ID
aws ec2 associate-route-table --subnet-id $SUBNET_D --route-table-id $RT_ID

echo "VPC=$VPC_ID  SUBNET_C=$SUBNET_C  SUBNET_D=$SUBNET_D"
# Guarda estos IDs - los usaras en los pasos siguientes
```

---

## 2. Security Groups

3 SGs encadenados (ALB → APP → DB) — defensa en profundidad para ASR-01.

```bash
# 2.1 SG del ALB (acepta 80/443 desde Internet)
SG_ALB=$(aws ec2 create-security-group --group-name $PROJECT-sg-alb \
  --description "ALB - 80/443 from Internet" --vpc-id $VPC_ID \
  --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_ALB \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

# 2.2 SG de las EC2 Django (solo desde el ALB)
SG_APP=$(aws ec2 create-security-group --group-name $PROJECT-sg-app \
  --description "Django EC2 - solo desde ALB + SSH" --vpc-id $VPC_ID \
  --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_APP \
  --protocol tcp --port 8080 --source-group $SG_ALB
# SSH abierto (cierra cuando hayas terminado debug)
aws ec2 authorize-security-group-ingress --group-id $SG_APP \
  --protocol tcp --port 22 --cidr 0.0.0.0/0

# 2.3 SG de PostgreSQL (solo desde EC2 app + replica desde primary)
SG_DB=$(aws ec2 create-security-group --group-name $PROJECT-sg-db \
  --description "Postgres - solo desde app y replica" --vpc-id $VPC_ID \
  --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_DB \
  --protocol tcp --port 5432 --source-group $SG_APP
aws ec2 authorize-security-group-ingress --group-id $SG_DB \
  --protocol tcp --port 5432 --source-group $SG_DB  # replica → primary
aws ec2 authorize-security-group-ingress --group-id $SG_DB \
  --protocol tcp --port 22 --cidr 0.0.0.0/0  # SSH para configurar replication

echo "SG_ALB=$SG_ALB  SG_APP=$SG_APP  SG_DB=$SG_DB"
```

---

## 3. EC2 PostgreSQL Primary (`monitoring-db-primary`)

> **Nota**: el informe especifica EC2 self-managed (no RDS) porque
> Streaming Replication requiere acceso al `postgresql.conf` y `pg_hba.conf`.

### 3.1 Lanzar instancia

```bash
# AMI Ubuntu 24.04 LTS en us-east-1
AMI=$(aws ec2 describe-images --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
  --query "sort_by(Images, &CreationDate)[-1].ImageId" --output text)
echo "AMI=$AMI"

# Lanzar primary en us-east-1c
PRIMARY_ID=$(aws ec2 run-instances --image-id $AMI \
  --instance-type t2.micro \
  --key-name TU_KEY_PAIR \
  --subnet-id $SUBNET_C \
  --security-group-ids $SG_DB \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$PROJECT-db-primary}]" \
  --query 'Instances[0].InstanceId' --output text)

aws ec2 wait instance-running --instance-ids $PRIMARY_ID
PRIMARY_IP=$(aws ec2 describe-instances --instance-ids $PRIMARY_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
PRIMARY_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids $PRIMARY_ID \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)
echo "Primary public=$PRIMARY_IP  private=$PRIMARY_PRIVATE_IP"
```

### 3.2 Instalar PostgreSQL en el primary

```bash
ssh -i TU_KEY.pem ubuntu@$PRIMARY_IP <<'EOF'
sudo apt-get update -y
sudo apt-get install -y postgresql-16 postgresql-contrib-16

# Crear BD y usuario
sudo -u postgres psql <<SQL
CREATE USER biteco_user WITH PASSWORD 'biteco_pass';
CREATE DATABASE monitoring_db OWNER biteco_user;
ALTER USER biteco_user WITH SUPERUSER;
SQL

# Configurar Streaming Replication
sudo tee -a /etc/postgresql/16/main/postgresql.conf <<CFG
# Streaming Replication
listen_addresses = '*'
wal_level = replica
max_wal_senders = 5
wal_keep_size = 1GB
hot_standby = on
CFG

# Permitir conexiones desde la replica y desde la app
sudo tee -a /etc/postgresql/16/main/pg_hba.conf <<HBA
host    replication    biteco_user    10.20.0.0/16    md5
host    all            biteco_user    10.20.0.0/16    md5
HBA

sudo systemctl restart postgresql

# Crear usuario de replicacion
sudo -u postgres psql -c "CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicator_pass';"
EOF
```

---

## 4. EC2 PostgreSQL Replica (`monitoring-db-replica`)

```bash
# 4.1 Lanzar instancia en us-east-1d
REPLICA_ID=$(aws ec2 run-instances --image-id $AMI \
  --instance-type t2.micro \
  --key-name TU_KEY_PAIR \
  --subnet-id $SUBNET_D \
  --security-group-ids $SG_DB \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$PROJECT-db-replica}]" \
  --query 'Instances[0].InstanceId' --output text)

aws ec2 wait instance-running --instance-ids $REPLICA_ID
REPLICA_IP=$(aws ec2 describe-instances --instance-ids $REPLICA_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
REPLICA_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids $REPLICA_ID \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)
echo "Replica public=$REPLICA_IP  private=$REPLICA_PRIVATE_IP"
```

### 4.2 Configurar replica desde el primary

```bash
ssh -i TU_KEY.pem ubuntu@$REPLICA_IP <<EOF
sudo apt-get update -y
sudo apt-get install -y postgresql-16

# Detener postgres y limpiar el data dir
sudo systemctl stop postgresql
sudo -u postgres rm -rf /var/lib/postgresql/16/main/*

# Hacer base backup desde el primary
sudo -u postgres PGPASSWORD=replicator_pass pg_basebackup \
  -h $PRIMARY_PRIVATE_IP -U replicator -D /var/lib/postgresql/16/main \
  -P -R -X stream -C -S replica_slot

# El flag -R crea standby.signal y postgresql.auto.conf - no hay que tocarlos
sudo systemctl start postgresql

# Verificar que arranco como hot standby
sudo -u postgres psql -c "SELECT pg_is_in_recovery();"
# Debe retornar: t
EOF
```

### 4.3 Verificar replicacion

```bash
# En el primary
ssh -i TU_KEY.pem ubuntu@$PRIMARY_IP <<EOF
sudo -u postgres psql -c "SELECT * FROM pg_stat_replication;"
# Deberia mostrar 1 fila con replica_slot conectado en estado 'streaming'
EOF
```

---

## 5. EC2 accounts-db

```bash
# 5.1 Lanzar instancia
ACCOUNTS_ID=$(aws ec2 run-instances --image-id $AMI \
  --instance-type t2.micro \
  --key-name TU_KEY_PAIR \
  --subnet-id $SUBNET_C \
  --security-group-ids $SG_DB \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$PROJECT-accounts-db}]" \
  --query 'Instances[0].InstanceId' --output text)
aws ec2 wait instance-running --instance-ids $ACCOUNTS_ID
ACCOUNTS_IP=$(aws ec2 describe-instances --instance-ids $ACCOUNTS_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
ACCOUNTS_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids $ACCOUNTS_ID \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)

# 5.2 Instalar Postgres + crear accounts_db
ssh -i TU_KEY.pem ubuntu@$ACCOUNTS_IP <<'EOF'
sudo apt-get update -y
sudo apt-get install -y postgresql-16 postgresql-contrib-16
sudo -u postgres psql <<SQL
CREATE USER biteco_user WITH PASSWORD 'biteco_pass';
CREATE DATABASE accounts_db OWNER biteco_user;
ALTER USER biteco_user WITH SUPERUSER;
SQL
# Permitir conexiones desde la VPC
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/16/main/postgresql.conf
echo "host all biteco_user 10.20.0.0/16 md5" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
sudo systemctl restart postgresql
EOF
```

---

## 6. EC2 Web 1 y Web 2 (Django)

### 6.1 Crear archivo userdata.sh

```bash
cat > /tmp/userdata.sh <<EOFUSERDATA
#!/bin/bash
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y python3-pip python3-venv git postgresql-client

# Clonar el repo (REEMPLAZA por tu URL real)
mkdir -p /opt/biteco
cd /opt/biteco
git clone https://github.com/TU-USUARIO/biteco.git app
cd app

# Virtualenv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# Variables de entorno
cat > /opt/biteco/app/.env <<ENV
DEBUG=False
ALLOWED_HOSTS=*
SECRET_KEY=$(openssl rand -hex 32)

DB_NAME_DEFAULT=accounts_db
DB_USER=biteco_user
DB_PASSWORD=biteco_pass
DB_HOST_DEFAULT=$ACCOUNTS_PRIVATE_IP
DB_NAME_MONITORING=monitoring_db
DB_HOST_MONITORING_PRIMARY=$PRIMARY_PRIVATE_IP
DB_HOST_MONITORING_REPLICA=$REPLICA_PRIVATE_IP
DB_PORT=5432

AUTH0_DOMAIN=PEGAR_AQUI
AUTH0_CLIENT_ID=PEGAR_AQUI
AUTH0_CLIENT_SECRET=PEGAR_AQUI
ENV

# Migraciones (solo en una de las dos EC2 — cualquiera)
set -a && source /opt/biteco/app/.env && set +a
python manage.py migrate
python manage.py migrate --database=monitoring
python manage.py seed_demo
python manage.py collectstatic --noinput

# Service systemd
cat > /etc/systemd/system/biteco.service <<SVC
[Unit]
Description=BITE.co Django App
After=network.target

[Service]
WorkingDirectory=/opt/biteco/app
EnvironmentFile=/opt/biteco/app/.env
ExecStart=/opt/biteco/app/.venv/bin/gunicorn bitecoapp.wsgi:application --bind 0.0.0.0:8080 --workers 3
Restart=always
User=root

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable biteco
systemctl start biteco
EOFUSERDATA

# Reemplazar las variables en el userdata
sed -i "s|\$ACCOUNTS_PRIVATE_IP|$ACCOUNTS_PRIVATE_IP|g" /tmp/userdata.sh
sed -i "s|\$PRIMARY_PRIVATE_IP|$PRIMARY_PRIVATE_IP|g" /tmp/userdata.sh
sed -i "s|\$REPLICA_PRIVATE_IP|$REPLICA_PRIVATE_IP|g" /tmp/userdata.sh
```

### 6.2 Lanzar 2 EC2 Web

```bash
# Web 1 en us-east-1c
WEB1_ID=$(aws ec2 run-instances --image-id $AMI \
  --instance-type t2.micro \
  --key-name TU_KEY_PAIR \
  --subnet-id $SUBNET_C \
  --security-group-ids $SG_APP \
  --user-data file:///tmp/userdata.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$PROJECT-web-1}]" \
  --query 'Instances[0].InstanceId' --output text)

# Web 2 en us-east-1d
WEB2_ID=$(aws ec2 run-instances --image-id $AMI \
  --instance-type t2.micro \
  --key-name TU_KEY_PAIR \
  --subnet-id $SUBNET_D \
  --security-group-ids $SG_APP \
  --user-data file:///tmp/userdata.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$PROJECT-web-2}]" \
  --query 'Instances[0].InstanceId' --output text)

aws ec2 wait instance-running --instance-ids $WEB1_ID $WEB2_ID

# Esperar a que el userdata termine (tarda ~3-5 min)
WEB1_IP=$(aws ec2 describe-instances --instance-ids $WEB1_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "Web1 public IP: $WEB1_IP"
echo "Web2 public IP: $(aws ec2 describe-instances --instance-ids $WEB2_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"

# Polling al endpoint hasta que responda
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -m 5 http://$WEB1_IP:8080/health-check/ || echo "000")
  echo "$(date +%H:%M:%S) Web1 health: $STATUS"
  [ "$STATUS" = "200" ] && break
  sleep 15
done
```

---

## 7. Application Load Balancer

```bash
# 7.1 Crear ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name $PROJECT-alb \
  --subnets $SUBNET_C $SUBNET_D \
  --security-groups $SG_ALB \
  --type application \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' --output text)
echo "ALB DNS: $ALB_DNS"

# 7.2 Target Group
TG_ARN=$(aws elbv2 create-target-group \
  --name $PROJECT-tg \
  --protocol HTTP --port 8080 \
  --vpc-id $VPC_ID \
  --health-check-path /health-check/ \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 2 \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# 7.3 Registrar las 2 EC2 Web en el TG
aws elbv2 register-targets --target-group-arn $TG_ARN \
  --targets Id=$WEB1_ID Id=$WEB2_ID

# 7.4 Listener
aws elbv2 create-listener --load-balancer-arn $ALB_ARN \
  --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

echo "App publicada en: http://$ALB_DNS"
```

---

## 8. Configurar Auth0 con la URL del ALB

Ahora que tienes `$ALB_DNS`, vuelve a Auth0 (`docs/AUTH0_SETUP.md`) y
agrega `http://$ALB_DNS/complete/auth0` como callback URL.

Luego actualiza el `.env` en cada EC2 Web con las credenciales reales de
Auth0 y reinicia gunicorn:

```bash
ssh -i TU_KEY.pem ubuntu@$WEB1_IP "
sudo sed -i 's|AUTH0_DOMAIN=PEGAR_AQUI|AUTH0_DOMAIN=biteco-dev.us.auth0.com|' /opt/biteco/app/.env
sudo sed -i 's|AUTH0_CLIENT_ID=PEGAR_AQUI|AUTH0_CLIENT_ID=tu-id|' /opt/biteco/app/.env
sudo sed -i 's|AUTH0_CLIENT_SECRET=PEGAR_AQUI|AUTH0_CLIENT_SECRET=tu-secret|' /opt/biteco/app/.env
sudo systemctl restart biteco
"
# Repetir en WEB2_IP
```

---

## 9. Verificación

```bash
# Health check via ALB
curl -i http://$ALB_DNS/health-check/
# → HTTP/1.1 200 OK    OK

# Home publica
curl -sI http://$ALB_DNS/
# → 200 OK

# Endpoint protegido sin auth
curl -sI http://$ALB_DNS/api/reportes/mensual?empresa_id=1
# → 401 Unauthorized

# Verificar que el AuditMiddleware registro el 401
ssh -i TU_KEY.pem ubuntu@$ACCOUNTS_IP <<'EOF'
sudo -u postgres psql accounts_db -c "
SELECT id, accion, usuario, ipOrigen, resultado
FROM registroauditoria_registroauditoria
ORDER BY id DESC LIMIT 5;
"
EOF
```

---

## 10. Cleanup (cuando termines la demo)

```bash
# Terminar instancias
aws ec2 terminate-instances --instance-ids $WEB1_ID $WEB2_ID $PRIMARY_ID $REPLICA_ID $ACCOUNTS_ID

# Borrar ALB y TG
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN
aws elbv2 delete-target-group --target-group-arn $TG_ARN

# Borrar SGs (despues de que las EC2 esten 'terminated')
aws ec2 delete-security-group --group-id $SG_ALB
aws ec2 delete-security-group --group-id $SG_APP
aws ec2 delete-security-group --group-id $SG_DB

# Borrar VPC (esto borra IGW, route tables, subnets en cascada)
aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
aws ec2 delete-vpc --vpc-id $VPC_ID
```

---

## Troubleshooting

| Sintoma | Causa | Fix |
|---|---|---|
| `502 Bad Gateway` en el ALB | gunicorn no arrancó | `ssh ubuntu@WEB_IP; journalctl -u biteco -f` |
| `connection refused` desde Django a Postgres | SG_DB no permite SG_APP | Revisar que `--source-group` esté correcto |
| `pg_basebackup: error: connection timed out` | El SG_DB no permite replica → primary | Agregar regla SG_DB ← SG_DB en 5432 |
| 401 en `/api/reportes/...` con token Auth0 valido | Falta el callback URL en Auth0 | Agregar `http://$ALB_DNS/complete/auth0` |
| Replication slot conflict al re-crear | `replica_slot` ya existe en primary | `SELECT pg_drop_replication_slot('replica_slot');` en primary |
| Las EC2 web no levantan despues de 10min | userdata.sh tiene un bug | `ssh; sudo cat /var/log/cloud-init-output.log` |
