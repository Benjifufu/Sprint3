output "alb_url" {
  description = "URL publica del ALB — pegar en Auth0 callback y en el .env.example"
  value       = "http://${aws_lb.main.dns_name}"
}

output "alb_dns" {
  value = aws_lb.main.dns_name
}

output "web1_public_ip" {
  description = "IP publica Web-1 (SSH debug)"
  value       = aws_instance.web1.public_ip
}

output "web2_public_ip" {
  description = "IP publica Web-2 (SSH debug)"
  value       = aws_instance.web2.public_ip
}

output "accounts_db_private_ip" {
  value = aws_instance.accounts_db.private_ip
}

output "db_primary_private_ip" {
  value = aws_instance.db_primary.private_ip
}

output "db_replica_private_ip" {
  value = aws_instance.db_replica.private_ip
}

output "auth0_callback_url" {
  description = "Pegar esto en Auth0 Application → Allowed Callback URLs"
  value       = "http://${aws_lb.main.dns_name}/complete/auth0"
}

output "ssh_web1" {
  value = "ssh -i TU_KEY.pem ubuntu@${aws_instance.web1.public_ip}"
}

output "ssh_web2" {
  value = "ssh -i TU_KEY.pem ubuntu@${aws_instance.web2.public_ip}"
}

output "ssh_db_primary" {
  value = "ssh -i TU_KEY.pem ubuntu@${aws_instance.db_primary.public_ip}"
}
