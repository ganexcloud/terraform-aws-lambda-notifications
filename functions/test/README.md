pip3 install python-lambda-local requests
export WEBHOOK_URL="XX"
export MESSENGER="XXX"
python-lambda-local -f lambda_handler app.py test/cloudwatch-event-ok.json
