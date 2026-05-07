# Renombrar a terraform.tfvars y completar TODOS los valores

aws_region = "us-east-1"
project    = "biteco"

# Key Pair existente en AWS (crea uno en EC2 → Key Pairs si no tienes)
key_name = "llave-biteco"

# Tipos de instancia (t2.micro para demo / t2.medium para carga real)
web_instance_type = "t2.micro"
db_instance_type  = "t2.micro"

# PostgreSQL
db_password = "BiteCo2026Seguro!"

# Auth0 (obtenerlos de manage.auth0.com → Applications → tu app → Settings)
auth0_domain        = "biteco-dev.us.auth0.com"
auth0_client_id     = "PEGAR_CLIENT_ID"
auth0_client_secret = "PEGAR_CLIENT_SECRET"

# GitHub (tu fork con la rama sprint-3)
github_repo   = "https://github.com/TU-USUARIO/App_Biteco.git"
github_branch = "sprint-3"

# AMI Ubuntu 24.04 LTS us-east-1 (verificar si cambió con el comando del README)
ami_id = "ami-04b4f1a9cf54c11d0"
