import os
import time
import json
from lib.aws import AWS_USER
from .common import (
    AmazonWebServices, run_command
)
from .test_airgap import get_bastion_node
from .test_custom_host_reg import (
    random_test_name, RANCHER_SERVER_VERSION, HOST_NAME, AGENT_REG_CMD
)
BASTION_ID = os.environ.get("RANCHER_HOSTNAME_PREFIX", "")
NUMBER_OF_INSTANCES = int(os.environ.get("RANCHER_AIRGAP_INSTANCE_COUNT", "1"))

PR_HOST_NAME = random_test_name(HOST_NAME)
RANCHER_PR_INTERNAL_HOSTNAME = \
    PR_HOST_NAME + "-internal.qa.rancher.space"
RANCHER_PR_HOSTNAME = PR_HOST_NAME + ".qa.rancher.space"

RESOURCE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'resource')
SSH_KEY_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                           '.ssh')
RANCHER_PR_PORT = os.environ.get("RANCHER_PR_PORT", "3131")
def test_pass():
    x = 4
    assert 1 == 1


def test_deploy_private_registry():
    node_name = PR_HOST_NAME + "-pvt-reg"
    private_registry_node = AmazonWebServices().create_node(node_name)

    # Copy SSH Key to pvt_rgstry + local dir, then give proper permissions
    write_key_command = "cat <<EOT >> {}.pem\n{}\nEOT".format(
        private_registry_node.ssh_key_name, private_registry_node.ssh_key)
    private_registry_node.execute_command(write_key_command)
    local_write_key_command = \
        "mkdir -p {} && cat <<EOT >> {}/{}.pem\n{}\nEOT".format(
            SSH_KEY_DIR, SSH_KEY_DIR,
            private_registry_node.ssh_key_name, private_registry_node.ssh_key)
    run_command(local_write_key_command, log_out=False)

    set_key_permissions_command = "chmod 600 {}.pem".format(
        private_registry_node.ssh_key_name)
    private_registry_node.execute_command(set_key_permissions_command)
    local_set_key_permissions_command = "chmod 600 {}/{}.pem".format(
        SSH_KEY_DIR, private_registry_node.ssh_key_name)
    run_command(local_set_key_permissions_command, log_out=False)

    # Write the private_registry config to the node and run the private_registry
    registry_json={"insecure-registries" : ["{}:{}".format(
    private_registry_node.public_ip_address,RANCHER_PR_PORT)]}

    bypass_insecure_cmd="sudo echo '{}' " \
    "> /etc/docker/daemon.json && " \
    "sudo systemctl daemon-reload && sudo systemctl restart docker".format(
    json.dumps(registry_json)
    )

    pr_cmd="mkdir auth && htpasswd -Bbn testuser " \
    "pass > auth/htpasswd && " \
    "docker run -d   -p {}:5000   --restart=always   --name registry2 " \
    "-v \"$(pwd)\"/auth:/auth   -e \"REGISTRY_AUTH=htpasswd\" " \
    "-e \"REGISTRY_AUTH_HTPASSWD_REALM=Registry Realm\"   -e " \
    "REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd   registry:2".format(
    RANCHER_PR_PORT)
    print("sudo installing apache2")
    print(private_registry_node.execute_command("sudo apt-get install apache2-utils"))
    print("writing bypass cmd")
    print(private_registry_node.execute_command(bypass_insecure_cmd))
    print("docker Running")
    print(private_registry_node.execute_command(pr_cmd))

    download_images_cmd="wget https://github.com/rancher/rancher/releases/download/{0}/rancher-images.txt && " \
    "wget https://github.com/rancher/rancher/releases/download/{0}/rancher-save-images.sh && " \
    "wget https://github.com/rancher/rancher/releases/download/{0}/rancher-load-images.sh".format(RANCHER_SERVER_VERSION)

    apply_images_cmd="sudo sed -i '58d' rancher-save-images.sh && " \
    "sudo sed -i '76d' rancher-load-images.sh && " \
    "chmod +x rancher-save-images.sh && chmod +x rancher-load-images.sh" \
    "./rancher-save-images.sh --image-list ./rancher-images.txt" \
    "./rancher-load-images.sh --image-list ./rancher-images.txt --registry " \
    "{}:{}".format(private_registry_node.public_ip_address,RANCHER_PR_PORT)

    print(private_registry_node.execute_command(download_images_cmd))
    print(private_registry_node.execute_command(apply_images_cmd))
    print("Private Registry Details:\nNAME: {}\nHOST NAME: {}\n"
          "INSTANCE ID: {}\n".format(node_name, private_registry_node.host_name,
                                     private_registry_node.provider_node_id))
    print("public IP: {}:{}".format(private_registry_node.public_ip_address,
    RANCHER_PR_PORT))
    assert int(private_registry_node.ssh_port) == 22
    return private_registry_node
