import boto3
import random
import string
import json
import logging


class AWSSecretManager:
    def __init__(self, region):
        self.secrets_client = boto3.client('secretsmanager', region_name=region)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def log_error(self, e):
        logging.error(e.response['Error']['Message'])

    def generate_random_password(self, length=14):
        """Generate a random password without special symbols."""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def get_secret_values(self, secret_name):
        """ Retrieve all values from a secret stored in AWS Secrets Manager """
        try:
            secret_value_response = self.secrets_client.get_secret_value(SecretId=secret_name)
            return json.loads(secret_value_response['SecretString'])
        except Exception as e:
            logging.error(f"Secret : {secret_name} does not exist")
            return None

    def create_or_update_secret(self, client_name, env, service):
        secret_name = f"{client_name}_secrets"
        new_key = f"{client_name}_{env}_{service}_user"

        try:
            secret = self.get_secret_values(secret_name)
            if secret is None:
                # Secret does not exist, create it
                secret = {new_key: self.generate_random_password(14)}
                self.secrets_client.create_secret(Name=secret_name, SecretString=json.dumps(secret))
                logging.info(f"Created new secret '{secret_name}' with key '{new_key}'.")
            else:
                # Secret exists, update it if necessary
                logging.info(f"AWS Secret '{secret_name}' already exists.")
                if new_key not in secret:
                    secret[new_key] = self.generate_random_password(14)
                    self.secrets_client.update_secret(SecretId=secret_name, SecretString=json.dumps(secret))
                    logging.info(f"Updated secret '{secret_name}' with new key '{new_key}'.")
                else:
                    logging.info(f"Key '{new_key}' already exists in secret '{secret_name}'. No update performed.")

            return secret_name

        except Exception as e:
            logging.error(f"Error handling the secret: {e}")
            return None