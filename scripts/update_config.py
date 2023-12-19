import logging
import time
import boto3
from botocore.exceptions import ClientError
import json
import os
import yaml

def update_yaml_with_clients(region, client_env_data_json):
    yaml_file_path = f'./config/{region}.yaml'
    #yaml_file_path = f'../config/{region}.yaml' ## FOR LOCAL TESTING

    # Load existing data from the YAML file
    if os.path.exists(yaml_file_path):
        with open(yaml_file_path, 'r') as file:
            existing_data = yaml.safe_load(file) or {}
    else:
        existing_data = {}

    # Load client environment data from JSON
    client_env_data = json.loads(client_env_data_json)

    # Update YAML data with new clients/environments
    for client, envs in client_env_data.items():
        if client not in existing_data:
            existing_data[client] = envs
        else:
            for env in envs:
                if env not in existing_data[client]:
                    existing_data[client].append(env)

    # Write updated data back to the YAML file
    with open(yaml_file_path, 'w') as file:
        yaml.dump(existing_data, file)

# LOCAL TESTING VARIABLES
# region = 'ca-central-1'
# region_client_env_data = '{"caliber": ["prod"], "brambles": ["prod","dev"]}'

# # GITHUB ACTIONS VARIABLES
region = os.environ.get("AWS_REGION")
region_client_env_data = os.environ.get("TO_ONBOARD")
update_yaml_with_clients(region, region_client_env_data)