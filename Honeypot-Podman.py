from podman import PodmanClient
import json
import argparse
import time
import os
import threading
# start podman API service with: podman system service -t 0 &
# This is not needed when running the containers standalone 

def main():
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
        "-n", "--number", type=int, default=1, required=False, help="Number of replicas to deploy ONLY for CP option"
    )

    parser.add_argument(
        "-p", "--print", action="store_true", required=False, help="Print command to see logs from containers"
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

        with open(args.deploy) as file:
            config_json = json.load(file)

        containers = []
        type = {"CSMS":"CSMS","CP":"charging","ChargingPoint":"charging"} 
        image = type[config_json.get("type","CP")]
        print(f"Deploying {args.number} {image}")
        for i in range(args.number):
            containers.append(client.containers.run(image,detach=True,name=f"{image}-{i}"))


        for container in containers:
            print("Container IDs:")
            print(f"{container.name}: {container.id}")
            if args.print:
                print(f"podman logs {container.id}")

            time.sleep(30)
            container.kill()
            container.remove()



if __name__ == "__main__":
    main()
