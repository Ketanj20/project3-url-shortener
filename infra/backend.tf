terraform {
  backend "s3" {
    bucket         = "terraform-state-kjain22-9163"
    key            = "project3/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
