# Tool for Deploying Virtual Labs Using Docker

This repository contains a tool to automate the deployment of virtual labs using Docker.  
It was developed as a Bachelor's Thesis (TFG) during the 2022/23 academic year for the Bachelor's Degree in Telecommunication Technologies Engineering at the University of Seville.

## How It Works

Once the repository is downloaded, a YAML-formatted script named `config.yml` must be placed in the same folder as the `dockerlab.py` file. This script should contain the specifications of the virtual lab to be deployed. Currently, the file must follow the structure below:

- `<lab_name>`: name of the lab (e.g., `lab`)
  - `network`: IPv4 address indicating the lab's subnet.
  - `nodes`: list of nodes that make up the lab.
    - `<node_name>`: name of the specific node.
      - `image`: Docker image to be used for the node. Cannot be used together with `build`.
      - `build`: if the node is based on a custom container, include a folder with the necessary deployment files and indicate its name here. Cannot be used together with `image`.
      - `script`: name of a shell script to be executed inside the container when it starts. It must be located in the current directory.
      - `network`: if you want to assign an IP within a subnet of the lab network, specify it here. Cannot be used with `ip`.
      - `ip`: to assign a specific IP within the lab network range, specify it here. Cannot be used with `network` or `replicas`.
      - `replicas`: to deploy multiple containers with similar configurations, specify the number of instances here. It is only incompatible with `ip` if the value is greater than 1. Each replica will have an environment variable `$REPLICA_ID` with an identifier to distinguish it from the others (a value between 0 and the maximum number of replicas - excluding the last one).
      - `needs`: list of dependencies required before deploying the container. This is used to control the deployment order.

## Execution

You can specify the desired execution mode for `dockerlab.py` using flags:

- `-b` or `--build`: Generates the `docker-compose.yml` file. If this option is selected alone, the containers will not be created.
- `-e` or `--execute`: Creates and launches the containers defined in `docker-compose.yml`.
- `-m` or `--monitor`: Monitors packet traffic in the simulated network. Must be used together with `-e`.
- `-u` or `--usage`: Monitors resource usage within the simulation containers. Must be used together with `-e`.

By default, if no flags are provided, it will run with the `-be` options.

Once the `docker-compose.yml` file has been created, you will be given the option to start the simulation by pressing `r`, stop it with `s`, and exit the application by pressing `esc`.

## Dependencies

The following requirements must be met to run this software:

- Docker 23.0.3 or later[^1]  
- Docker Compose 1.29.2 or later[^1]  
- Python 3.10.6 or later[^1]  
- Python libraries listed in the `requirements.txt` file

To install dependencies on a Debian-based Linux distribution (as superuser), follow these steps:

1. Update repositories and installed packages:
```bash
apt update
apt upgrade
```
2. Install required software using the package manager:
```bash
apt install docker
apt install docker-compose
apt install python3
apt install python3-tk
```
3. To install the required Python libraries, navigate to the folder containing `requirements.txt` and run:
```bash
python3 -m pip install -r requirements.txt
```

## Known Issues

- When running the program for the first time, you may encounter the error `Got permission denied while trying to connect to the Docker daemon socket`. This means the user running the application is not part of the `docker` group. To fix this, create the group with `sudo groupadd docker`, then add your user with `sudo usermod -aG docker ${USER}`. After that, re-login with `su - ${USER}`. You can test if it works by running `docker run hello-world`.
- If you get an `Error while Stopping` message and containers do not stop properly, it may be due to AppArmor (a Linux kernel security module that restricts program capabilities). To fix it, open a new terminal and run `sudo aa-remove-unknown`[^2]. Then run `docker compose down`. This should resolve the issue.

[^1]: The repository has been tested with the specified versions. While older versions may work, only the listed versions are guaranteed to avoid unexpected issues.  
[^2]: You may find several "snap.docker.dockerd" processes in the output of `aa-status`. The recommended way to stop Docker containers in this case is to run `aa-remove-unknown`. More info: [https://javahowtos.com/guides/124-docker/414-solved-cannot-kill-docker-container-permission-denied.html](https://javahowtos.com/guides/124-docker/414-solved-cannot-kill-docker-container-permission-denied.html)
