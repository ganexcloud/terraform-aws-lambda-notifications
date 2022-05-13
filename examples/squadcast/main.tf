module "lambda_notifications" {
  source               = "../../"
  lambda_function_name = "lambda-notifications"
  sns_topic_name       = "lambda-notifications"
  webhook_url          = "https://api.squadcast.com/v2/incidents/api/xxxxxxxxxxx"
  messenger            = "squadcast"
}
