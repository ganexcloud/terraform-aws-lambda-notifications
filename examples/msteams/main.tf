module "lambda_notifications" {
  source               = "../../"
  lambda_function_name = "lambda-notifications"
  sns_topic_name       = "lambda-notifications"
  webhook_url          = "https://poligraph.webhook.office.com/webhookb2/XXXXXXXXXXX/IncomingWebhook/XXXXXXXXX/XXXXXXXXX"
  messenger            = "msteams"
}
