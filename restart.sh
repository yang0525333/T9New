#!/bin/bash

# Heroku app name
APP_NAME="t9live"

HEROKU_API_KEY=$HEROKU_API_KEY

# Heroku API URL
HEROKU_API_URL="https://api.heroku.com/apps/$APP_NAME/dynos"

# Restart the Heroku app
curl -n -X DELETE $HEROKU_API_URL \
-H "Content-Type: application/json" \
-H "Accept: application/vnd.heroku+json; version=3" \
-H "Authorization: Bearer $HEROKU_API_KEY"