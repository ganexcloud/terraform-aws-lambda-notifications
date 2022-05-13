module "lambda_notifications" {
  source               = "../../"
  lambda_function_name = "lambda-notifications"
  sns_topic_name       = "lambda-notifications"
  webhook_url          = "https://hooks.slack.com/services/xxxx/xxxxx/xxxxxxxxxxxxxx"
  messenger            = "slack"
}
