#!/bin/sh

# # Initialize the migration environment
# flask db init

# # Generate the migration script
# flask db migrate -m "Initial migration."

# Apply the migration script to the database
flask db upgrade