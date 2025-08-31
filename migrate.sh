#!/bin/sh
# Apply any new migrations

flask db migrate

flask db upgrade

# Start the app
gunicorn -w 4 -b 0.0.0.0:$PORT app:app
