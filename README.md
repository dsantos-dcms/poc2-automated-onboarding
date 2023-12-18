# Important Notes

- Subnets provided to mount target must be in different AZ, otherwise it will fail
- Make sure the gitaction runner is running as a service so it is always available
  -  sudo ./svc.sh install
  -  sudo ./svc.sh start


# Completed
- EFS 100% HANDLING

# Next 
- Decide if gitactions will execute actions through SSM and MGMT instance or a git runner inside the VPC
- Create a way to setup directories and mount EFS

For runners inside AWS.

I would have to:
-  set up a runner in each region
-  setup a git job for each region

I could possibly:
- Use the ec2 MGMT as a runner

# Consideration for moving to Prod
- Add Backups to EFS during creation


