import logging
import time
import boto3
from botocore.exceptions import ClientError
import json
import os
import subprocess
from efs import AwsEfsManager
from rds import setup_rds_for_environment

# print(os.environ)
region = os.environ.get("AWS_REGION")
region_client_env_data = os.environ.get("TO_ONBOARD")

# Initialize the AWS EFS Manager
efs_manager = AwsEfsManager(region)

# Check if region_client_env_data is not None
if region_client_env_data:
    # Parse the JSON string into a Python dictionary
    try:
        client_envs = json.loads(region_client_env_data)

        for client, envs in client_envs.items():
            for env in envs:
                # Create EFS file system for each client and environment
                file_system_id = efs_manager.create_efs(client)

                if file_system_id:
                    # Create access point for the EFS
                    access_point_id = efs_manager.create_access_point(file_system_id, client, env)
                    print(f"Access Point ID: {access_point_id}")
                efs_manager.mount_efs(file_system_id, client)
                efs_manager.efs_folder_setup(client, env)
                setup_rds_for_environment(client, env)
                
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from MY_VAR: {e}")
else:
    print("Environment variable MY_VAR is not set or is empty.")