import time
import boto3
from botocore.exceptions import ClientError


AWS_REGION = "us-east-1"
ECS_CLUSTER = "medical-rag-cluster"       
ECR_REPO = "medical-rag-repo"             
IAM_USER_NAME = "medical-rag-user"        
CUSTOM_POLICY_NAMES = ["ECS-PassRole-Policy"]
DELETE_ECR_REPO = True                    


def stop_and_delete_ecs_services(ecs_client, cluster_name):
    """Scales all active ECS services to 0, deletes them, and stops running Fargate tasks."""
    print(f"\n[1/4] Stopping and deleting active ECS services in '{cluster_name}'...")
    try:
        # 1. Scale down and delete all ECS services in the cluster
        svc_paginator = ecs_client.get_paginator("list_services")
        services_found = False
        for page in svc_paginator.paginate(cluster=cluster_name):
            for svc_arn in page.get("serviceArns", []):
                services_found = True
                svc_name = svc_arn.split("/")[-1]
                print(f"  -> Scaling service '{svc_name}' to desiredCount=0...")
                ecs_client.update_service(
                    cluster=cluster_name,
                    service=svc_name,
                    desiredCount=0
                )
                print(f"  -> Deleting service '{svc_name}'...")
                ecs_client.delete_service(
                    cluster=cluster_name,
                    service=svc_name,
                    force=True
                )

        if not services_found:
            print("  -> No active ECS services found.")

        # 2. Stop any running or pending Fargate tasks
        for status in ["RUNNING", "PENDING"]:
            task_paginator = ecs_client.get_paginator("list_tasks")
            for page in task_paginator.paginate(cluster=cluster_name, desiredStatus=status):
                for task_arn in page.get("taskArns", []):
                    task_id = task_arn.split("/")[-1]
                    print(f"  -> Stopping {status} Fargate task: {task_id}")
                    ecs_client.stop_task(
                        cluster=cluster_name,
                        task=task_arn,
                        reason="Automated teardown"
                    )

        # 3. Wait until all tasks have fully drained so the cluster can be deleted
        print("  -> Waiting for Fargate tasks to drain...")
        for _ in range(24):  # Up to 2 minutes
            running = ecs_client.list_tasks(cluster=cluster_name, desiredStatus="RUNNING").get("taskArns", [])
            if not running:
                print("  -> All ECS services and Fargate tasks stopped.")
                return
            time.sleep(5)

        print("  -> Warning: Some tasks are still draining; cluster deletion may retry or require a moment.")

    except ClientError as e:
        print(f"  -> ECS services notice: {e}")


def delete_ecs_cluster(ecs_client, cluster_name):
    """Deletes the empty ECS cluster."""
    print(f"\n[2/4] Deleting ECS cluster '{cluster_name}'...")
    try:
        ecs_client.delete_cluster(cluster=cluster_name)
        print(f"  -> Deleted ECS cluster '{cluster_name}'.")
    except ClientError as e:
        print(f"  -> ECS cluster notice: {e}")


def delete_ecr_repository(ecr_client, repo_name):
    """Deletes the ECR repository and all Docker images inside it."""
    print(f"\n[3/4] Deleting ECR repository '{repo_name}'...")
    try:
        ecr_client.delete_repository(repositoryName=repo_name, force=True)
        print(f"  -> Deleted ECR repository '{repo_name}'.")
    except ClientError as e:
        print(f"  -> ECR notice: {e}")


def delete_custom_policy(iam_client, policy_arn):
    """Deletes all non-default versions of a customer-managed policy, then deletes the policy."""
    try:
        versions = iam_client.list_policy_versions(PolicyArn=policy_arn).get("Versions", [])
        for v in versions:
            if not v["IsDefaultVersion"]:
                iam_client.delete_policy_version(
                    PolicyArn=policy_arn,
                    VersionId=v["VersionId"]
                )
        iam_client.delete_policy(PolicyArn=policy_arn)
        print(f"  -> Deleted custom IAM policy: {policy_arn}")
    except ClientError as e:
        print(f"  -> Could not delete policy {policy_arn}: {e}")


def delete_iam_user_and_permissions(iam_client, sts_client, username, extra_custom_policies):
    """Detaches/deletes all IAM permissions, removes user credentials, and deletes the IAM user."""
    print(f"\n[4/4] Removing IAM permissions and deleting user '{username}'...")

    identity = sts_client.get_caller_identity()
    account_id = identity["Account"]
    caller_arn = identity["Arn"]

    if caller_arn.endswith(f":user/{username}"):
        print("  -> WARNING: You are currently authenticated AS the IAM user being deleted.")
        print("     Once policies are detached, deleting the user itself may fail with AccessDenied.")

    custom_policy_arns = {
        f"arn:aws:iam::{account_id}:policy/{name}" for name in extra_custom_policies
    }

    try:
        # 1. Detach all managed policies (AWS-managed and customer-managed)
        attached = iam_client.list_attached_user_policies(UserName=username).get("AttachedPolicies", [])
        for policy in attached:
            p_arn = policy["PolicyArn"]
            print(f"  -> Detaching managed policy: {policy['PolicyName']}")
            iam_client.detach_user_policy(UserName=username, PolicyArn=p_arn)
            # Track customer-managed policies (exclude AWS-managed policies starting with arn:aws:iam::aws:)
            if not p_arn.startswith("arn:aws:iam::aws:"):
                custom_policy_arns.add(p_arn)

        # 2. Delete all inline policies embedded on the user
        inline_policies = iam_client.list_user_policies(UserName=username).get("PolicyNames", [])
        for p_name in inline_policies:
            print(f"  -> Deleting inline policy: {p_name}")
            iam_client.delete_user_policy(UserName=username, PolicyName=p_name)

        # 3. Remove user from any IAM groups
        groups = iam_client.list_groups_for_user(UserName=username).get("Groups", [])
        for grp in groups:
            print(f"  -> Removing user from group: {grp['GroupName']}")
            iam_client.remove_user_from_group(GroupName=grp["GroupName"], UserName=username)

        # 4. Delete programmatic Access Keys
        keys = iam_client.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
        for key in keys:
            print(f"  -> Deleting access key: {key['AccessKeyId']}")
            iam_client.delete_access_key(UserName=username, AccessKeyId=key["AccessKeyId"])

        # 5. Delete console login profile (if password login was enabled)
        try:
            iam_client.delete_login_profile(UserName=username)
            print("  -> Deleted console login profile.")
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchEntity":
                raise

        # 6. Deactivate any MFA devices
        mfas = iam_client.list_mfa_devices(UserName=username).get("MFADevices", [])
        for mfa in mfas:
            print(f"  -> Deactivating MFA device: {mfa['SerialNumber']}")
            iam_client.deactivate_mfa_device(UserName=username, SerialNumber=mfa["SerialNumber"])

        # 7. Delete the IAM user
        iam_client.delete_user(UserName=username)
        print(f"  -> Deleted IAM user '{username}'.")

    except ClientError as e:
        print(f"  -> IAM user notice: {e}")

    # 8. Delete custom (customer-managed) IAM policies
    for p_arn in custom_policy_arns:
        delete_custom_policy(iam_client, p_arn)


def main():
    session = boto3.Session(region_name=AWS_REGION)
    ecs_client = session.client("ecs")
    ecr_client = session.client("ecr")
    iam_client = session.client("iam")
    sts_client = session.client("sts")

    print(f"=== Starting ECS, ECR, and IAM Teardown in {AWS_REGION} ===")
    stop_and_delete_ecs_services(ecs_client, ECS_CLUSTER)
    delete_ecs_cluster(ecs_client, ECS_CLUSTER)

    if DELETE_ECR_REPO:
        delete_ecr_repository(ecr_client, ECR_REPO)

    delete_iam_user_and_permissions(iam_client, sts_client, IAM_USER_NAME, CUSTOM_POLICY_NAMES)
    print("\n=== Teardown Complete ===")


if __name__ == "__main__":
    main()