import yaml
import os
import json

def read_yaml_files(directory):
    data = []
    for file in os.listdir(directory):
        if file.endswith(".yaml"):
            full_path = os.path.join(directory, file)
            with open(full_path, 'r') as file:
                yaml_data = yaml.safe_load(file)
                data.append(yaml_data)
    return data

def find_new_customers_or_environments(customers_data, onboarded_file):
    with open(onboarded_file, 'r') as file:
        onboarded_data = yaml.safe_load(file)

    new_customers_or_environments = {}

    for customer, environments in customers_data.items():
        if customer not in onboarded_data:
            new_customers_or_environments[customer] = list(environments.keys())
        else:
            for environment in environments:
                if environment not in onboarded_data[customer]:
                    if customer not in new_customers_or_environments:
                        new_customers_or_environments[customer] = []
                    new_customers_or_environments[customer].append(environment)

    return new_customers_or_environments

# Define regions | MOVE THIS TO GIT ENV VARIABLES
regions = os.environ.get("AWS_REGION")

# Initialize the dictionary to store results
region_results = {}

# Loop over each region
for region in regions:
    directory = f'./customers/{region}/'
    onboarded_file = f'./config/{region}.yaml'

    # Use the existing logic for each region
    obtained_data = read_yaml_files(directory)
    consolidated_customers_data = {k: v for d in obtained_data for k, v in d.items()}
    results = find_new_customers_or_environments(consolidated_customers_data, onboarded_file)

    json_str = json.dumps(results)
    # Store the result in the dictionary
    region_results[region] = json_str

# Print or use the results as needed
print(region_results)