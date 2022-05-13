module "lambda_codepipeline_notifications" {
  source               = "../../"
  lambda_function_name = "codepipeline-notifications"
  sns_topic_name       = "codepipeline-notifications"
  messenger            = "discord"
  webhook_url          = "https://discord.com/api/webhooks/564654654654654/asdasdasdasddasd-asdasdasdasdasdasd"
}
