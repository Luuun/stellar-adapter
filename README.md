# Stellar Adapter for Rehive
This adapter plugs into Rehive to provide Stellar transaction support and hotwallet management.

## Notes:

To make use of this adapter:

1) Set the Rehive webhooks for each tx type to match their corresponding endpoints below.

2) Set a secret key for each transaction webhook

3) Ensure the the required ENV variables have been added to the server.

**Required ENV variables:**

In order to use the Stellar adapter you must set the following ENV variables on the server.

`STELLAR_SEND_PRIVATE_KEY` : Private key for adapter sends.

`STELLAR_SEND_ADDRESS` : Address for adapter sends.

'STELLAR_RECEIVE_ADDRESS' : Address for adapter receives.

`STELLAR_NETWORK` : Specifies whether to use the TESTNET or PUBLIC network.

`REHIVE_API_URL` : Platform URL, used to update transactions on Rehive (eg. 'http://localhost:8080').

`REHIVE_API_TOKEN` : Token used for Rehive Admin API endpoint when updating transactions.

`STELLAR_WITHDRAW_SECRET_KEY` : Withdraw Webhook security key (Defaults to 'secret').

`STELLAR_DEPOSIT_SECRET_KEY` : Deposit Webhook security key (Defaults to 'secret').

`STELLAR_SEND_SECRET_KEY` : Send Webhook security key (Defaults to 'secret').

---

## Requirements

Requires [Python](https://www.python.org/), [Docker Toolkit](https://docs.docker.com/), [Anaconda](https://store.continuum.io/cshop/anaconda/) and some other dependancies. Complete, heavy-weight development set up guide for MacOSX can be found [here](https://github.com/jr-minnaar/goeie-hoop).

## Getting started
###Remote Server Set Up:
Rapidly provision and set up a server on AWS, Google Cloud Platform or Digital Ocean for running one or multiple projects.

##### A. Configuration

1. Ensure that you have a `/etc/.server.env` file set up with the project settings. Example:

	```
	HOST_NAME=gcloud-starter
	IMAGE_NAME=zapgo/starter
	
	SSH_USERNAME=root
	SSH_PORT=22
	
	DOCKER_COMPOSE_VERSION=1.5.1
	
	DIGITAL_OCEAN_TOKEN=*digital ocean key*
	AWS_ACCESS_KEY_ID=*AWS key*
	AWS_SECRET_ACCESS_KEY=*AWS secret*
	```

2. Use the commands below to install and activate Fabric in a Python 2.7 virtual environment. Activate the fab environment before running any fab commands.

	```
	make fab
	source activate fab
	```

##### C. Provisioning
	
1. Create the server on Digital Ocean, Google Cloud or AWS:
	```
	fab -f ./etc/server/fabric_tasks.py create_server:provider='digitalocean'
	```
	*When using gcloud, first install gcloud and run gcloud auth login

2. Add the newly created VM to your ssh config file:
	```
	fab -f ./etc/server/fabric_tasks.py create_ssh_config
	```

##### D. Server setup
	
3. Install docker-compose and set up directory structure on server:
	```
	fab -f ./etc/server/fabric_tasks.py install_server_requirements
	```

4. Install the docker-image-factory for updating docker images when python dependancies change:
	```
	fab -f ./etc/server/fabric_tasks.py install_image_factory
	```
	
5. Load nginx and letsencrypt docker containers for automatic reverse proxy and SSL management for all projects running on this VM:
	```
	 fab -f ./etc/server/fabric_tasks.py nginx_ssl_setup
	 ```

###Project Deployment:
This setup is structured so that multiple projects can run alongside each other on the same server in separate docker containers. Here's how to start a new project:

#### Creating Docker Images
Run these steps when you need to create docker images for this project the first time or update the docker image due to changes in `requirements.txt`

1. Deploy before starting:

	```
	fab P deploy
	```

2. Compile the wheels for packages in `requirements.txt`
	
	```
	fab P make_wheels
	```
3. Build the docker image:

	```
	fab P build_docker_image
	```
	
4. Log in to your docker account:

	```
	fab P docker:login
	```
	
4. Push the image to DockerHub:

	```
	fab P push_image
	```

####Configuration
#####A. Settings and API Keys

1. The project config settings and 3rd party API keys are in `.env` files in the project root directory. To start off, create three files, `.production.env`, `.staging.env` and `.local.env` in your root directory with the following format. You can run `fab generate_django_secret` to generate a django secret key for this project.

	```
	PROJECT_NAME=django-starter 
	VIRTUAL_ENV=django-starter 
	HOST_NAME=gcloud-starter
	VIRTUAL_HOST=starter.zapgo.co
	ENV_FILE=.production.env
	
	IMAGE_NAME=zapgo/starter
	
	DJANGO_SECRET=*secret key*
	DEBUG=False
	
	LETSENCRYPT_EMAIL=*your email*
	LETSENCRYPT_HOST=starter.zapgo.co
	```

#####B. Local python virtual environment

2. Update the first line of `etc/environment.yml` to reflect your chosen virtual environment name (e.g. django-starter).
	
3. Create the local virtual environment:
	
	```
	fab L python_env_setup
	```
	
#####C. Local PostgresDB set up

5. When working on MacOSX, you will need to create and activate a docker-machine VM:

	```
	docker-machine start default
	eval $(docker-machine env default)
	```

6. Start a local postgres server:
	
	```
	fab L compose:'up -d postgres'
	```
6. Add the docker server to your `/etc/hosts` for easy local testing with the postgre db:

	```
	fab L add_postgres_host
	```
	
###Commands

####Format
```
Local:			fab L {command}:{parameters}
Staging:		fab S {command}:{parameters}
Production:		fab P {command}:{parameters}
```
####Local
#####Database:
Edit the `prepare()` function in `etc/fabric_tasks` to include the neccessary migrations. Then run:

```
fab L prepare
```
You can also use the `fab L manage:migrate` command for specific migrations.
	
#####Webserver:

```	
fab L manage:runserver
```
####Deployment

#####Upload files to server:
```
fab P deploy
```
#####Run webserver:
```
fab P compose:'up -d'
```
#####Stop webserver:
```
fab P compose:'stop'
```
#####Hard Reset webserver (reload env vars):
```
fab P compose:'stop'
fab P compose:'rm'
fab P compose:'up'
```
#####List running containers:
```
fab P docker:ps
```



