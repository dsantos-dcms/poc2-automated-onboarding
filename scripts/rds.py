import boto3
import random
import string
import json
import os
import logging
import time
import subprocess
from secrets import AWSSecretManager

region = os.environ.get("AWS_REGION")
aws_secret_manager = AWSSecretManager(region)
regions = {
            'ca-central-1': {"rds_endpoint": "rds-dsantos.cfv6lwb0lbi7.ca-central-1.rds.amazonaws.com", "master_password": "master_password"},
            'us-east-1': {"subnet_ids": ["subnet-088928fa05998da0a"], "security_groups":["sg-04e82704b331280ed"]},
            'us-east-2': {"subnet_ids": ["id_a","id_b"], "security_groups":["a","b"]},
            'ap-south-2': {"subnet_ids": ["id_a","id_b"], "security_groups":["a","b"]}
          }

def setup_rds_for_environment(client_name, env):
    
    service = "db"
    # Retrieve master admin RDS secret from Secret Manager
    master_secret_values = aws_secret_manager.get_secret_values(regions.get(region, {}).get('master_password'))
    db_master_user = master_secret_values['username']
    db_master_password = master_secret_values['password']
    
    print(db_master_user, db_master_password)
    # Check for existing client secret | create a new secret and secret values 
    secret_name = aws_secret_manager.create_or_update_secret(client_name, env, service)
    time.sleep(10)  # Wait for the secret to be available
    client_secret_values = aws_secret_manager.get_secret_values(secret_name)
    
    db_name = f'{client_name}_{env}_db'
    role_name = f'{client_name}_{env}_db_user'
    role_password = client_secret_values[role_name]
    rds_endpoint = regions.get(region, {}).get('rds_endpoint')
    
    createdb = f"export PGPASSWORD={db_master_password} && psql -h {rds_endpoint} -U {db_master_user} -c \"CREATE DATABASE {db_name};\""
    createrole = f"export PGPASSWORD={db_master_password} && psql -h {rds_endpoint} -U {db_master_user} -c \"CREATE ROLE {role_name} WITH LOGIN ENCRYPTED PASSWORD '{role_password}';\""
    grantrole = f"export PGPASSWORD={db_master_password} && psql -h {rds_endpoint} -U {db_master_user} -c \"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {role_name};\""
    alterdb = f"export PGPASSWORD={db_master_password} && psql -h {rds_endpoint} -U {db_master_user} -c \"ALTER DATABASE {db_name} OWNER TO {role_name};\" && unset PGPASSWORD"
    checkdb = f"export PGPASSWORD={db_master_password} && psql -h {rds_endpoint} -U {db_master_user} -c \"\\l\" && unset PGPASSWORD"
    
    # Execute the command
    try:
        subprocess.run(createdb, check=True, shell=True)
        subprocess.run(createrole, check=True, shell=True)
        subprocess.run(grantrole, check=True, shell=True)
        subprocess.run(alterdb, check=True, shell=True)
        subprocess.run(checkdb, check=True, shell=True)
        logging.info(f"Database {db_name}, role {role_name}, and permissions have been set up for {client_name} {env}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error setting up RDS for {client_name} {env}: {e}")
