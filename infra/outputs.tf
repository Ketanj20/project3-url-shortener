output "api_url" {
  value       = aws_apigatewayv2_stage.default.invoke_url
  description = "Base URL for the URL shortener API"
}

output "shorten_endpoint" {
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/shorten"
  description = "POST to this endpoint with {\"url\": \"https://example.com\"}"
}

output "dynamodb_table" {
  value = aws_dynamodb_table.urls.name
}

output "lambda_function" {
  value = aws_lambda_function.url_shortener.function_name
}
