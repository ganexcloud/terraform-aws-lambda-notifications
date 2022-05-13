output "sns_topic_arn" {
  description = "The ARN of the SNS topic from which messages will be sent to Slack"
  value       = local.sns_topic_arn
}

output "lambda_iam_role_arn" {
  description = "The ARN of the IAM role used by Lambda function"
  value       = module.lambda.lambda_role_arn
}

output "lambda_iam_role_name" {
  description = "The name of the IAM role used by Lambda function"
  value       = module.lambda.lambda_role_name
}

output "lambda_function_arn" {
  description = "The ARN of the Lambda Function"
  value       = module.lambda.lambda_function_arn
}
