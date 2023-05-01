import argparse
import docker
import json
from io import BytesIO

# Define the directories to copy from the copy image
copy_dirs = ["/bin", "/etc", "/lib64", "/usr", "/entrypoint-ecs.sh"]

# Define the target paths in the target image to copy to
target_paths = [
    "/build/tmp/CrowdStrike/rootfs/bin/",
    "/build/tmp/CrowdStrike/rootfs/etc/",
    "/build/tmp/CrowdStrike/rootfs/lib64/",
    "/build/tmp/CrowdStrike/rootfs/usr/",
    "/build/tmp/CrowdStrike/rootfs/entrypoint-ecs.sh",
]

# Define the CrowdStrike Falcon entrypoint to be used in the target image
entrypoint = [
    "/tmp/CrowdStrike/rootfs/lib64/ld-linux-x86-64.so.2",
    "--library-path",
    "/tmp/CrowdStrike/rootfs/lib64",
    "/tmp/CrowdStrike/rootfs/bin/bash",
    "/tmp/CrowdStrike/rootfs/entrypoint-ecs.sh",
]

# Define the multi-stage Dockerfile
DOCKERFILE = """\
# Stage 1: Set a Falcon container image as a copy source
FROM {falcon_image} AS falcon

# Stage 2: Copy files and directories from Falcon Container image to a build stage using Alpine (intermediate container minimizes additional layers and using Alpine ensure binaries available for RUN statement to work if final image is a minimal image like scratch)
FROM alpine:latest as build
RUN mkdir -p /build/tmp/CrowdStrike/rootfs && mkdir -p /build/tmp/CrowdStrike-private/ && chmod -R a=rX /build/tmp/CrowdStrike && chmod -R a=rwX /build/tmp/CrowdStrike-private
{copy_directives}

# Stage 3: Copy CrowdStrike Content from build stage and setup entrypoints to load crowdstrike before the applications normal entrypoint/cmd values, set the FALCON CID value as a default ENV value
FROM {source_image}
COPY --from=build /build/tmp/ /tmp/
ENTRYPOINT {entrypoint}
CMD {cmd}
ENV FALCONCTL_OPTS={env}
USER 0:0
"""


def main():
    # Create the argument parser
    parser = argparse.ArgumentParser(
        description="Modify an existing Docker image to copy files and directories from another image."
    )

    # Add the arguments
    parser.add_argument(
        "source_image_tag", type=str, help="The tag of the existing image to modify."
    )
    parser.add_argument(
        "falcon_image_tag",
        type=str,
        help="The tag of the falcon image to copy files and directories from.",
    )
    parser.add_argument(
        "target_image_tag", type=str, help="The tag of the modified image to create."
    )
    parser.add_argument(
        "cid", type=str, help="The Falcon CID value to embed in final image"
    )
    args = parser.parse_args()

    # Connect to the Docker daemon
    client = docker.from_env()

    # Get the existing image object
    try:
        source_image = client.images.get(args.source_image_tag)
    except docker.errors.ImageNotFound:
        try:
            print(f"Source image {args.source_image_tag} is not present locally pulling")
            client.images.pull(args.source_image_tag)
            source_image = client.images.get(args.source_image_tag)
        except docker.errors.APIError as e:
            print(f"Error occured while pulling the source image: {e}")
    except docker.errors.APIError as e:
        print(f"Error occured while getting the source image: {e}")
        return

    # Name of the container image to copy files from
    falcon_image_name = args.falcon_image_tag

    # Get the existing image's entrypoint and cmd values
    existing_entrypoint = source_image.attrs["Config"]["Entrypoint"]
    existing_cmd = source_image.attrs["Config"]["Cmd"]

    # Combine existing_entrypoint and existing_cmd into a single value for cmd
    cmd = []
    if existing_entrypoint is not None and len(existing_entrypoint) > 0:
        if isinstance(existing_entrypoint, list):
            cmd += existing_entrypoint
        else:
            cmd += [existing_entrypoint]
    if existing_cmd is not None and len(existing_cmd) > 0:
        if isinstance(existing_cmd, list):
            cmd += existing_cmd
        else:
            cmd += [existing_cmd]

    # Build the copy directives
    copy_directives = ""
    for i in range(len(copy_dirs)):
        copy_directives += (
            "COPY --from=falcon " + copy_dirs[i] + " " + target_paths[i] + "\n"
        )

    # Build the new image using a multi-stage Dockerfile
    dockerfile = DOCKERFILE.format(
        falcon_image=falcon_image_name,
        copy_directives=copy_directives,
        source_image=args.source_image_tag,
        entrypoint=json.dumps(entrypoint),
        cmd=json.dumps(cmd),
        env=args.cid,
    )

    print(f"Resulting dockerfile:\n\n{dockerfile}\n")
    try:
        target_image = client.images.build(
            fileobj=BytesIO(dockerfile.encode("UTF-8")),
            rm=True,
            encoding="gzip",
            tag=args.target_image_tag,
        )
    except docker.errors.BuildError as e:
        print(f"Error occurred during image build: {e}")
        return

    print(f"Successfully built new image {args.target_image_tag}")


if __name__ == "__main__":
    main()
