import logging
import time
import boto3
from botocore.exceptions import ClientError
import json
import os

class AwsEfsManager:
    def __init__(self, region):
        self.efs_client = boto3.client('efs', region_name=region)
        self.region = region
        self.regions = {
            'ca-central-1': {"subnet_ids": ["subnet-06f45035183d72a63"], "security_groups":["sg-084bfe2d8728356fe"]}, # AZ MUST BE DIFFERENT FOR EFS MOUNT TARGET
            'us-east-1': {"subnet_ids": ["id_a","id_b"], "security_groups":["a","b"]},
            'us-east-2': {"subnet_ids": ["id_a","id_b"], "security_groups":["a","b"]},
            'ap-south-2': {"subnet_ids": ["id_a","id_b"], "security_groups":["a","b"]}
        }

    def log_error(self, error):
        logging.error(f"An error occurred: {error}")

    def _execute_aws_call(self, func, *args, **kwargs):
        """ Helper function to execute AWS calls with error handling. """
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            self.log_error(e)
            return None

    def _wait_for_status(self, check_status_func, success_status, timeout=300, interval=10):
        """ Generic method to wait for a specific status. """
        elapsed_time = 0
        while elapsed_time < timeout:
            if check_status_func() == success_status:
                return True
            time.sleep(interval)
            elapsed_time += interval
        return False
    
    def create_efs(self, client_name):
        efs_name = f"{client_name}-k8s"
        logging.info(f"Starting the process to create/check EFS for '{efs_name}'.")
        file_system_id = self.efs_exists(efs_name)

        # Get region configuration
        region_config = self.regions.get(self.region)
        if not region_config:
            raise ValueError(f"No configuration found for region {self.region}")

        subnet_ids = region_config['subnet_ids']
        security_groups = region_config['security_groups']

        # Create EFS if it does not exist
        if not file_system_id:
            try:
                logging.info(f"EFS '{efs_name}' not found.")
                logging.info(f"Creating EFS '{efs_name}'...")
                response = self.efs_client.create_file_system(
                    PerformanceMode='generalPurpose', 
                    ThroughputMode='bursting', 
                    Encrypted=True, 
                    Tags=[
                        {'Key': 'Name', 'Value': efs_name},
                        {'Key': 'dotcms.client.name.short', 'Value': client_name}
                    ]
                )
                file_system_id = response['FileSystemId']
                self.wait_for_efs_available(file_system_id)
                logging.info(f"EFS '{efs_name}' created successfully with ID: {file_system_id}")
            except ClientError as e:
                self.log_error(e)
                return None
            except ValueError as e:
                self.log_error(e)
                return None
        else:
            logging.info(f"EFS '{efs_name}' already exists with ID: {file_system_id}. Skipping EFS creation for '{efs_name}'")
            logging.info(f"Starting the process to create/check mount targets for '{efs_name}'...")

        # Create mount targets
        for subnet_id in subnet_ids:
            if not self.mount_target_exists(file_system_id, subnet_id):
               self.create_mount_target(file_system_id, subnet_id, security_groups)
            
        # After creating all mount targets, wait for them to become available
        if not self.wait_for_mount_target_availability(file_system_id):
            logging.warning(f"Not all mount targets for EFS {file_system_id} became available.")
            return None

        return file_system_id

    def efs_exists(self, efs_name):
        response = self._execute_aws_call(self.efs_client.describe_file_systems)
        return next((fs['FileSystemId'] for fs in response.get('FileSystems', []) 
                     if any(tag.get('Value') == efs_name for tag in fs.get('Tags', []))), None)    

    def wait_for_efs_available(self, file_system_id):
        return self._wait_for_status(
            lambda: self._execute_aws_call(self.efs_client.describe_file_systems, FileSystemId=file_system_id).get('FileSystems', [{}])[0].get('LifeCycleState'),
            'available'
        )
     
    def create_mount_target(self, file_system_id, subnet_id, security_groups):
        try:
            logging.info(f"Creating mount target for {file_system_id} in subnet {subnet_id} with security groups {security_groups}.")
            self.efs_client.create_mount_target(FileSystemId=file_system_id, SubnetId=subnet_id, SecurityGroups=security_groups)
            logging.info(f"Mount target created in subnet: {subnet_id} for file system {file_system_id}.")
        except ClientError as e:
            self.log_error(e)
            return False
        
    def mount_target_exists(self, file_system_id, subnet_id):
        try:
            response = self.efs_client.describe_mount_targets(FileSystemId=file_system_id)
            return any(mount['SubnetId'] == subnet_id for mount in response.get('MountTargets', []))
        except ClientError as e:
            self.log_error(e)
            return False
    
    def wait_for_mount_target_availability(self, file_system_id):
        logging.info(f"Waiting for all mount targets of EFS {file_system_id} to become available.")

        def all_mount_targets_available():
            response = self._execute_aws_call(self.efs_client.describe_mount_targets, FileSystemId=file_system_id)
            if not response or 'MountTargets' not in response:
                return False
            return all(mount['LifeCycleState'] == 'available' for mount in response['MountTargets'])

        if self._wait_for_status(all_mount_targets_available, True):
            logging.info(f"All mount targets for EFS {file_system_id} are now available.")
            return True
        else:
            logging.warning(f"Timeout or error occurred waiting for mount targets for EFS {file_system_id}.")
            return False
    
    def access_point_exists(self, file_system_id, access_point_name):
        logging.info(f"Checking if access point '{access_point_name}' exists for file system '{file_system_id}'.")
        try:
            response = self.efs_client.describe_access_points(FileSystemId=file_system_id)
            for ap in response.get('AccessPoints', []):
                for tag in ap.get('Tags', []):
                    if tag.get('Key') == 'Name' and tag.get('Value') == access_point_name:
                        return True
            return False
        except ClientError as e:
            self.log_error(e)
            return False

    def create_access_point(self, file_system_id, client_name, env):
        access_point_name = env
        if self.access_point_exists(file_system_id, access_point_name):
            logging.info(f"Access point '{access_point_name}' already exists. Skipping access point creation for '{access_point_name}'")
            return None

        try:
            access_point_options = {
                'FileSystemId': file_system_id, 
                'PosixUser': {'Uid': 65000, 'Gid': 65000},
                'RootDirectory': {'Path': f"/{env}", 'CreationInfo': {'OwnerUid': 65000, 'OwnerGid': 65000, 'Permissions': '0755'}},
                'Tags': [{'Key': 'Name', 'Value': access_point_name}, {'Key': 'Client', 'Value': client_name}]
            }
            response = self.efs_client.create_access_point(**access_point_options)
            access_point_id = response['AccessPointId']
            logging.info(f"Access point '{access_point_id}' created for {client_name} in {env} environment.")
            return access_point_id
        except ClientError as e:
            self.log_error(e)
            return None
    

################################################################################################################# 

logging.basicConfig(level=logging.INFO)



# region_client_env_data = {
#     'ca-central-1': '{"caliber": ["prod","dev"], "brambles": ["prod"], "new-client": ["prod"]}', 
#     'us-east-1': '{"calvin": ["prod"]}'
# }

#print(os.environ)
region = os.environ.get("AWS_REGION")
region_client_env_data = os.environ.get("CA_CENTRAL_1_ENCODED")

efs_manager = AwsEfsManager(region)  # Initialize with a default region

for region, client_envs_json in region_client_env_data.items():
    # Parse the JSON string to get the client-environment dictionary
    client_envs = json.loads(client_envs_json)

    for client, envs in client_envs.items():
        for env in envs:
            # Create EFS file system for each client and environment
            file_system_id = efs_manager.create_efs(client)

            if file_system_id:
                # Create access point for the EFS
                access_point_id = efs_manager.create_access_point(file_system_id, client, env)
                print(f"Access Point ID: {access_point_id}")

