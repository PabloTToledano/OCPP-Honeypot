from podman import PodmanClient
import json
import argparse
import time
import os
import threading

# start podman API service with: podman system service -t 0 &
# This is not needed when running the containers standalone


def deploy(client, number, image):
    try:
        ocpp_network = client.networks.get("ocpp")

    except Exception as e:
        print(f"Creating network ocpp")
        ocpp_network = client.networks.create("ocpp")

    containers = []
    print(f"Deploying {number} {image}")
    for i in range(1, number + 1):
        try:
            print(f" Trying to remove old {image}-{i}")
            old_container = client.containers.get(f"{image}-{i}")
            # old_container.kill()
            old_container.remove()
        except Exception as e:
            print(f" Not found {image}-{i}: {e}")
        container = client.containers.create(
            image, detach=True, name=f"{image}-{i}", network="ocpp"
        )
        # ocpp_network.connect(container)
        containers.append(container)
        ocpp_network.reload()
        print(ocpp_network.containers)
    return containers


def main():
    uri = "unix:///run/user/1000/podman/podman.sock"
    uri = "unix:///run/user/1000/podman/podman.sock"

    parser = argparse.ArgumentParser(description="OCPP Honeypot")
    parser.add_argument(
        "-d",
        "--deploy",
        type=str,
        required=True,
        help="Path to a config JSON",
    )

    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=1,
        required=False,
        help="Number of replicas to deploy ONLY for CP option",
    )

    parser.add_argument(
        "-p",
        "--print",
        action="store_true",
        required=False,
        help="Print command to see logs from containers",
    )

    parser.add_argument(
        "-w",
        "--web",
        action="store_true",
        required=False,
        help="Deploys the full stack Backend(AIOHtpp and CSMS) and FrontEnd",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.deploy):
        print("Invalid config JSON")
        exit(-1)

    with PodmanClient(base_url=uri) as client:
        version = client.version()
        print("Release: ", version["Version"])
        print("Compatible API: ", version["ApiVersion"])
        print("Podman API: ", version["Components"][0]["Details"]["APIVersion"], "\n")

        containers = []

        if args.web:
            # CSMS and Backend
            try:
                result = client.containers.get("csms1")
                client.container.remove(result)
            except Exception as e:
                pass
            containers.append(
                client.containers.run(
                    "http",
                    detach=True,
                    name=f"csms1",
                )
            )
            # Front
            containers.append(client.containers.run("front", detach=True))
        else:
            with open(args.deploy) as file:
                config_json = json.load(file)

            cp_config = config_json["CP"]
            csms_config = config_json["CSMS"]
            containers = deploy(client, 1, "csms")
            containers = containers + deploy(client, args.number, "charging")

        print("Container IDs:")
        for container in containers:
            print(f"{container.name}: {container.id}")
            if args.print:
                print(f"podman logs {container.id}")

        for container in containers:
            time.sleep(30)
            container.kill()
            container.remove()


if __name__ == "__main__":
    main()
