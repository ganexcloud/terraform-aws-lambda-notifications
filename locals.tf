locals {
  sns_topic_arn = try(
    aws_sns_topic.this[0].arn,
    "arn:${data.aws_partition.current.id}:sns:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.sns_topic_name}",
    ""
  )

  lambda_policy_document = {
    sid       = "AllowWriteToCloudwatchLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [replace("${try(aws_cloudwatch_log_group.lambda[0].arn, "")}:*", ":*:*", ":*")]
  }

  lambda_policy_document_kms = {
    sid       = "AllowKMSDecrypt"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [var.kms_key_arn]
  }
}
