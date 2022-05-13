resource "aws_cloudwatch_log_group" "lambda" {
  count = var.create ? 1 : 0

  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = var.cloudwatch_log_group_retention_in_days
  kms_key_id        = var.cloudwatch_log_group_kms_key_id

  tags = merge(var.tags, var.cloudwatch_log_group_tags)
}

resource "aws_sns_topic" "this" {
  count             = var.create_sns_topic && var.create ? 1 : 0
  name              = var.sns_topic_name
  kms_master_key_id = var.sns_topic_kms_key_id
  tags              = merge(var.tags, var.sns_topic_tags)
}

resource "aws_sns_topic_policy" "default" {
  count  = var.create_sns_topic && var.create ? 1 : 0
  arn    = aws_sns_topic.this[0].arn
  policy = data.aws_iam_policy_document.sns_topic_policy.json
}

resource "aws_sns_topic_subscription" "sns_notify_slack" {
  count = var.create ? 1 : 0

  topic_arn     = local.sns_topic_arn
  protocol      = "lambda"
  endpoint      = module.lambda.lambda_function_arn
  filter_policy = var.subscription_filter_policy
}

module "lambda" {
  source        = "terraform-aws-modules/lambda/aws"
  version       = "3.2.0"
  create        = var.create
  function_name = var.lambda_function_name
  description   = var.lambda_description
  handler       = "app.lambda_handler"
  source_path = [
    {
      path             = "${path.module}/functions/"
      pip_requirements = false
    }
  ]
  recreate_missing_package          = var.recreate_missing_package
  runtime                           = "python3.6"
  timeout                           = 30
  kms_key_arn                       = var.kms_key_arn
  reserved_concurrent_executions    = var.reserved_concurrent_executions
  ephemeral_storage_size            = var.lambda_function_ephemeral_storage_size
  publish                           = true
  layers                            = var.lambda_layers
  create_role                       = var.lambda_role == ""
  lambda_role                       = var.lambda_role
  role_name                         = "${var.iam_role_name_prefix}-${var.lambda_function_name}"
  role_permissions_boundary         = var.iam_role_boundary_policy_arn
  role_tags                         = var.iam_role_tags
  role_path                         = var.iam_role_path
  policy_path                       = var.iam_policy_path
  attach_cloudwatch_logs_policy     = false
  attach_policy_json                = true
  policy_json                       = try(data.aws_iam_policy_document.lambda[0].json, "")
  use_existing_cloudwatch_log_group = true
  attach_network_policy             = var.lambda_function_vpc_subnet_ids != null
  environment_variables = {
    WEBHOOK_URL = var.webhook_url
    MESSENGER   = var.messenger
  }
  allowed_triggers = {
    AllowExecutionFromSNS = {
      principal  = "sns.amazonaws.com"
      source_arn = local.sns_topic_arn
    }
  }
  store_on_s3            = var.lambda_function_store_on_s3
  s3_bucket              = var.lambda_function_s3_bucket
  vpc_subnet_ids         = var.lambda_function_vpc_subnet_ids
  vpc_security_group_ids = var.lambda_function_vpc_security_group_ids
  tags                   = merge(var.tags, var.lambda_function_tags)
  depends_on             = [aws_cloudwatch_log_group.lambda]
}
