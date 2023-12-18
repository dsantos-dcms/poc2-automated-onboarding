# Important Notes

- Subnets provided to mount target must be in different AZ, otherwise it will fail
- Make sure the gitaction runner is running as a service so it is always available
  -  sudo ./svc.sh install
  -  sudo ./svc.sh start


# Completed
- EFS 100% HANDLING

# Consideration for moving to Prod
- Add Backups to EFS during creation

# Next  
- Create an EC2 MGMT in US Region
- Create a script to re-add onboarded clients to file

