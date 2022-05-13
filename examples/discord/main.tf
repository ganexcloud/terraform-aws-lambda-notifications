module "lambda_notifications" {
  source               = "../../"
  lambda_function_name = "lambda-notifications"
  sns_topic_name       = "lambda-notifications"
  webhook_url          = "https://discord.com/api/webhooks/xxxxxx/xxxxxxxx"
  messenger            = "discord"
}
