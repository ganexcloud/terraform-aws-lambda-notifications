module "lambda_codepipeline_notifications" {
  source               = "../../"
  lambda_function_name = "codepipeline-notifications"
  sns_topic_name       = "codepipeline-notifications"
  messenger            = "squadcast"
  webhook_url          = "https://api.squadcast.com/v2/incidents/api/xxxxxxxxxxxxxxxxxxxx"
}
