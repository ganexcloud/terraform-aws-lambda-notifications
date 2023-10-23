data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}
data "aws_iam_policy_document" "lambda" {
  count = var.create ? 1 : 0

  dynamic "statement" {
    for_each = concat([local.lambda_policy_document], var.kms_key_arn != "" ? [local.lambda_policy_document_kms] : [])
    content {
      sid       = statement.value.sid
      effect    = statement.value.effect
      actions   = statement.value.actions
      resources = statement.value.resources
    }
  }
}

data "aws_iam_policy_document" "sns_topic_policy" {
  policy_id = "__default_policy_ID"

  statement {
    actions = [
      "SNS:Subscribe",
      "SNS:SetTopicAttributes",
      "SNS:RemovePermission",
      "SNS:Receive",
      "SNS:Publish",
      "SNS:ListSubscriptionsByTopic",
      "SNS:GetTopicAttributes",
      "SNS:DeleteTopic",
      "SNS:AddPermission",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceOwner"

      values = [
        data.aws_caller_identity.current.account_id,
      ]
    }

    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    resources = var.create_sns_topic ? [
      aws_sns_topic.this[0].arn,
      ] : [
      local.sns_topic_arn
    ]

    sid = "__default_statement_ID"
  }

  statement {
    actions = [
      "SNS:Publish"
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"

      values = [
        data.aws_caller_identity.current.account_id,
      ]
    }

    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["codestar-notifications.amazonaws.com"]
    }

    resources = var.create_sns_topic ? [
      aws_sns_topic.this[0].arn,
      ] : [
      local.sns_topic_arn
    ]

    sid = "AWSCodeStarNotifications"
  }

  statement {
    actions = [
      "SNS:Publish"
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceAccount"

      values = [
        data.aws_caller_identity.current.account_id,
      ]
    }

    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    resources = var.create_sns_topic ? [
      aws_sns_topic.this[0].arn,
      ] : [
      local.sns_topic_arn
    ]

    sid = "AWSCloudWatchNotifications"
  }


}
