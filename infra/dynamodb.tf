# DynamoDB table — stores short_code → original_url mappings
# PAY_PER_REQUEST = no provisioned capacity to manage, scales automatically
# Free tier: 25GB storage + 25 read/write capacity units free forever
resource "aws_dynamodb_table" "urls" {
  name         = "${var.project_name}-urls"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "short_code"

  attribute {
    name = "short_code"
    type = "S"
  }

  # Auto-delete items after 90 days (optional, keeps table clean)
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-urls"
  }
}
