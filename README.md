# crowdstrike-container-embedded-sensor-tool

## About
This proof of concept tool allows users to inject the CrowdStrike Falcon Container into a new image based on the customers existing images. This currently is designed to only work with containers that are intended to run on ECS Fargate. (SYS_PTRACE capability still needs to be specified within the Task Definition).

The solution will do the following:
 - Inspect the config your source image to determine the default entrypoint/cmd values 
 - Copy CrowdStrike Falcon Container Sensor contents into a new layer
 - Set CrowdStrike as the entrypoint on the final image
 - Load the source images original entrypoint/cmd values into the CMD values of the final image and output a new image.

## PreReqs:
 - Python3 & pip3 configured
 - Virtualenv (best practice and required if you use docker-py instead of docker normally with python)
 - Docker / docker compatible engine already running on the host (Tested with docker-engine on linux, Docker Desktop on Mac, colima on Mac, Rancher Desktop on Mac)
 - Docker is authenticated to any private registries hosting either the image you plan to patch or the Falcon Container image you are pulling contents from the CrowdStrike registry

## Initial Setup:
 - Clone this repository
 - Create a virtualenv `python3 -m virtualenv env-crowdstrike`
 - Activate virtualenv `source env-crowdstrike/bin/activate`
 - Install python requirements `pip3 -r requirements.txt`

## Usage:
The script takes positional arguments to run, the arguments are required in the following order:
`python3 embed.py <source uri to patch> <falcon image uri> <target image uri> <falcon CID value to inject>`  

## Example:
```
python3 embed.py hello-world:latest localhost/falcon-container:latest embedtest:latest ABCDEFGHIJKLMNOPQRSTUVWXYZ123456-78
Successfully built new image embedtest:latest
```

### Inspecting the final image:
```
docker inspect embedtest:latest | jq '.[].Config'
{
  "Hostname": "",
  "Domainname": "",
  "User": "0:0",
  "AttachStdin": false,
  "AttachStdout": false,
  "AttachStderr": false,
  "Tty": false,
  "OpenStdin": false,
  "StdinOnce": false,
  "Env": [
    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "FALCONCTL_OPTS=ABCDEFGHIJKLMNOPQRSTUVWXYZ123456-78"
  ],
  "Cmd": [
    "/hello"
  ],
  "Image": "sha256:07d205caea66f9763dea9f0c0d8ff5bdd5ac1b347e3da9179d7bcc798b3c0770",
  "Volumes": null,
  "WorkingDir": "",
  "Entrypoint": [
    "/tmp/CrowdStrike/rootfs/lib64/ld-linux-x86-64.so.2",
    "--library-path",
    "/tmp/CrowdStrike/rootfs/lib64",
    "/tmp/CrowdStrike/rootfs/bin/bash",
    "/tmp/CrowdStrike/rootfs/entrypoint-ecs.sh"
  ],
  "OnBuild": null,
  "Labels": null
}
```

## Support
This is an open source project and not a CrowdStrike product. As such, it carries no formal support, expressed, or implied.