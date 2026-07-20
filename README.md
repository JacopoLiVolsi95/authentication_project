# Minimal Third-Party Authentication Service
This project develops a simple Third-Party Authentication Service.
It grants a user access to a centralized authentication.
From here, the user can request temporary credentials to access a protected service.
The protected service does not directly manage user credentials.
It must validate access using the credentials issued by the authentication service.  
More details on the task and the decision taken are detailed into `auth_project_task_and_decisions.txt`.

## Project Structure
The project is organized in the following files:
```
├── authentication_service.py
├── backup
│   └── backup_cronjob.sh
├── credential.env.example
├── database.py
├── dockerfiles
│   ├── authentication.Dockerfile
│   ├── authentication_requirements.txt
│   ├── compose.yaml
│   └── Makefile
├── __init__.py
├── init.sql
├── protected_service.py
├── README.md
└── tests.py
```
We have the directory `dockerfiles` which contains all the necessary components to build and launch the project.  
In the main directory, we have an example of the environment variable file, the `init.sql` file where the database structure is defined and the `database.py` module where we have some auxiliar functionalities.  
Moreover, we have the `backup` directory that will contain the instructions for the database backup.  
Finally, we have the main services, namely `authentication_service.py` and `protected_service.py`, and a `tests.py` suite for unit-testing.

## Prerequisites
On your system, make sure the following packages are installed: **make**, **docker**, **docker compose**.
The project is thought and tested for a Linux environment.

## Build/Install
First of all, you need to build the image on which the services will run. Hence, on your terminal, go in the `dockerfiles` directory  and execute the following command:
```
make authentication
```
Then, remaining in the `dockerfiles` directory, run  the command:
```
docker compose -f compose.yaml pull
```
Finally, copy the `credential.env.example` in a secure location, naming it `credential.env`. For the sake of simplicty of this guide, we assume to copy it in the same location of this repository.  
Once you copied it, modify it changing the secret credentials for Postgres and with the ports where you want to host your services.

## Launch Project
To launch the dockerized input
```
docker compose -f dockerfiles/compose.yaml --env-file credential.env up -d
```
This will launch the Postgres database container, the authorization service and all the protected services defined in the docker compose.

### Install the Backup Cronjob
In order to backup your db, you can install a cronjob that will run the `backup_cronjob.sh` script.  
After prompting the command:
```
crontab -e
```
edit the file adding the following lines and substituting /path/to/your/repo/ with the actual path:
```
mkdir -p /path/to/your/repo/backup/db_backups/
0 2 * * * PATH=${PATH}:/usr/sbin /path/to/your/repo/backup/backup_cronjob.sh >> /path/to/your/repo/backup/db_backups/backup.log 2>&1
```
This will run a backup of the database every day at 2 a.m.. If you want to do it more or less frequently, modify the cronjob parameters accordingly.

### Add a Protected Service
If you want to add a protected service you need to:
* copy the template container `protected_service_0` and add a new one to the `compose.yaml`
* change the name `PROTECTED_SERVICE_NAME` with the new service one
* increment the `PROTECTED_SERVICE_ID` in the environmental variable
* modify the `ipv4_address` with a new unique one
* add the corresponding `PROTECTED_SERVICE_PORT_N` in the `credential.env` file.

## Testing and Debug
In order to perform all the tests, you should, after launching the project with the command stated in the previous section, run the command:
```
docker container run -it --rm  --network dockerfiles_auth-network --env-file credential.env -v .:/work:ro -w /work jlivolsi/authentication python3 tests.py
```

### pgAdmin
If you think a GUI for visualizing the database is helpful, you can launch a pgAdmin container simply adding the debugging profile to the docker compose command, i.e.
```
docker compose -f dockerfiles/compose.yaml --env-file credential.env --profile debug up -d
```

Doing so, after almost 30 seconds needed for startup, you can connect to the pgAdmin via web at port 5050 with the credentials you set in `credential.env` file.  
To configure a new server, you have to:
* click on the add server button
* in the General tab, set the name you desire
* in the Connection tab, set `postgres` (i.e. the service name in the `compose.yaml` file) as Host name/address and the credential you choose in your `credential.env` file

Now, in order to see the tables, you can go to the "Databases" section, click on your ${POSTGRES_DB} (equal to `authentication_service` in our case) and navigate through "Schemas/public/Tables" to see the currently used tables.  
Moreover, with a right click on your database name, you can select the "Query Tool" option to perform the queries you want.


## Uninstall
To remove the whole project, you should tear down the docker compose project with the command
```
docker compose -f dockerfiles/compose.yaml --env-file credential.env down -v
```
**N.B.** the option -v also deletes the volumes, i.e. all the database. Be careful using it!
**N.B.** if you activate a profile, you must remember to put the flag `--profile debug` also when you execute the aforementioned command, otherwise it may result in an incomplete deletion.
