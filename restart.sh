#!/bin/bash

# Heroku app name
APP_NAME="t9live"

# Heroku API key (to be set as an environment variable in Heroku)
HEROKU_API_KEY=$HEROKU_API_KEY

# Set Heroku CLI authentication
echo "machine api.heroku.com
  login $HEROKU_API_KEY
  password $HEROKU_API_KEY" > ~/.netrc

# Restart the Heroku app
heroku restart --app $APP_NAME
