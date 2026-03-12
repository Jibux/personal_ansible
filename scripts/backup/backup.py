#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pyyaml",
#   "paramiko"
# ]
# ///

"""Backup directories using rclone to NAS and/or cloud."""

import argparse
import logging
import shlex
import subprocess
import sys
from pathlib import Path

import paramiko
import yaml

EXIT_CODE_FAILED = 1
SCRIPT_DIR = Path(__file__).parent.resolve()
logger = logging.getLogger(Path(__file__).stem)


class SplitArgs(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        setattr(namespace, self.dest, values.split(","))


def setup_logger(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    )
    logging.getLogger("paramiko").setLevel(logging.WARNING)


def fail(msg: str = "Something wrong happened", exit_code: int = EXIT_CODE_FAILED) -> None:
    logger.error(msg)
    sys.exit(exit_code)


def dry_run_info(dry_run):
    return "[DRY-RUN] " if dry_run else ""


def load_config(config_path: Path) -> dict:
    with config_path.open("r") as f:
        config = yaml.load(f, Loader=yaml.CSafeLoader)

    required_keys = ["nas_host", "nas_user", "nas_script_path", "items"]
    for key in required_keys:
        if not config.get(key):
            fail(f"Config key '{key}' is missing or empty")

    return config


def build_rclone_cmd(
    source: str,
    destination: str,
    excludes: list[str],
    dry_run: bool,
    verbose: bool,
) -> list[str]:
    cmd = ["rclone", "sync", source, destination]
    for exc in excludes or []:
        cmd += ["--exclude", exc]
    if dry_run:
        cmd.append("--dry-run")
    if verbose:
        cmd.append("--verbose")
    return cmd


def run_subprocess(cmd: list[str], capture_output: bool = False, dry_run: bool = False, verbose: bool = False) -> None:
    logger.info(f"{dry_run_info(dry_run)}Running: {shlex.join(cmd)}")
    if dry_run:
        return
    result = subprocess.run(cmd, capture_output=capture_output, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed with return code {result.returncode}")
        if capture_output and result.stderr:
            logger.error(f"stderr: {result.stderr}")
        sys.exit(result.returncode)


def get_folder_destination_from_item(item: dict) -> str:
    return item.get("folder_destination", item["folder"])


def get_source_from_item(item: dict) -> str:
    return f"{item['source']}/{item['folder']}"


def get_nas_destination_from_item(item: dict) -> str:
    return f"{item['nas_destination']}:{item['nas_share']}/{get_folder_destination_from_item(item)}"


def get_nas_source_from_item(item: dict) -> str:
    return f"/{item.get('nas_share', 'share1')}/{item['nas_share']}/{get_folder_destination_from_item(item)}"


def get_cloud_destination_from_item(item: dict, from_nas: False) -> str:
    cloud_dest = (
        item.get("cloud_destination_from_nas", item["cloud_destination"]) if from_nas else item["cloud_destination"]
    )
    return f"{cloud_dest}:{get_folder_destination_from_item(item)}"


def backup_to_nas(item: dict, dry_run: bool, verbose: bool) -> None:
    name = item.get("name", "<unnamed>")
    source = get_source_from_item(item)
    nas_dest = get_nas_destination_from_item(item)

    if not source or not nas_dest:
        fail(f"Item '{name}' missing source or nas_destination, skipping NAS backup")

    logger.info(f"{dry_run_info(dry_run)}Backing up '{name}': local -> NAS")
    cmd = build_rclone_cmd(source, nas_dest, item.get("exclude", []), dry_run, verbose)
    run_subprocess(cmd, verbose=verbose)


def backup_to_cloud(item: dict, dry_run: bool, verbose: bool) -> None:
    name = item.get("name", "<unnamed>")
    source = get_source_from_item(item)
    cloud_dest = get_nas_destination_from_item(item)

    if not source or not cloud_dest:
        fail(f"Item '{name}' missing source or cloud_destination, skipping cloud backup")

    logger.info(f"{dry_run_info(dry_run)}Backing up '{name}': local -> cloud")
    cmd = build_rclone_cmd(source, cloud_dest, item.get("exclude", []), dry_run, verbose)
    run_subprocess(cmd, verbose=verbose)


def write_backup_list(items: list[dict], backup_list_path: Path, dry_run: bool, verbose: bool) -> None:
    lines = []
    for item in items:
        nas_src = get_nas_source_from_item(item)
        cloud_dest_from_nas = get_cloud_destination_from_item(item, True)
        if nas_src and cloud_dest_from_nas:
            lines.append(f"{nas_src}|{cloud_dest_from_nas}")

    content = "\n".join(lines) + "\n" if lines else ""

    logger.info(f"{dry_run_info(dry_run)}Writing backup list to {backup_list_path} ({len(lines)} entries)")
    logger.info(f"Backup list content:\n{content}")

    if not dry_run:
        if backup_list_path.is_file():
            backup_list_path.unlink()
        backup_list_path.write_text(content)
        backup_list_path.chmod(0o400)

    return backup_list_path


def scp_preserve(local_path: Path, nas_host: str, remote_path: Path, dry_run: bool, verbose: bool) -> None:
    """Copy a local file to the NAS using scp -p (preserve permissions) -O for compatibility with old ssh."""
    cmd = ["scp", "-p", "-O", str(local_path), f"{nas_host}:{remote_path}"]
    run_subprocess(cmd, True, dry_run, verbose)


def connect_with_ssh_agent(host: str, user: str) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user)
    return client


def ssh_execute(
    host: str, user: str, command: list[str], background: bool = False, timeout: int = 60, dry_run: bool = False
) -> int:
    exit_code = 0
    escaped_command = shlex.join(command)
    if background:
        escaped_command = f"nohup {escaped_command} > /dev/null &"

    logger.info(f"{dry_run_info(dry_run)}SSH on {host} and execute command: {escaped_command}")

    client = connect_with_ssh_agent(host, user)

    if dry_run:
        client.close()
        return exit_code

    try:
        _, stdout, stderr = client.exec_command(escaped_command)
        for line in stdout:
            print(line, end="", flush=True)
        for line in stderr:
            print(line, end="", flush=True)
        exit_code = stdout.channel.recv_exit_status()
    finally:
        client.close()

    if exit_code != 0:
        fail(f"SSH command failed with exit code {exit_code}")

    return exit_code


def execute_from_nas(
    config: dict,
    items: list[dict],
    nas_script_args: list[str] | None,
    dry_run: bool,
    verbose: bool,
) -> None:
    nas_host = config["nas_host"]
    nas_user = config["nas_user"]
    nas_script_path = config["nas_script_path"]
    remote_rclone_conf = Path("/tmp/.rclone.conf")
    backup_list_path = Path("/tmp/.backup_list.txt")

    write_backup_list(items, backup_list_path, dry_run, verbose)

    # ssh_execute(nas_host, nas_user, ["sleep", "100"], True)
    # ssh_execute(nas_host, nas_user, ["dates"], True)
    # sys.exit(0)
    ssh_execute(nas_host, nas_user, ["rm", "-f", str(remote_rclone_conf), str(backup_list_path)], dry_run=dry_run)

    local_rclone_conf = Path.home() / ".config" / "rclone" / "rclone.conf"
    logger.info(f"{dry_run_info(dry_run)}Copying rclone.conf to {nas_host}:{remote_rclone_conf}")
    scp_preserve(local_rclone_conf, nas_host, remote_rclone_conf, dry_run, verbose)
    logger.info(f"{dry_run_info(dry_run)}Copying backup list to {nas_host}:{backup_list_path}")
    scp_preserve(backup_list_path, nas_host, backup_list_path, dry_run, verbose)
    nas_script_name = Path(nas_script_path).name
    local_script = SCRIPT_DIR / nas_script_name

    if not local_script.exists() and not dry_run:
        fail(f"NAS script not found locally: {local_script}")

    logger.info(f"{dry_run_info(dry_run)}Copying script '{local_script}' to {nas_host}:{nas_script_path}")
    scp_preserve(local_script, nas_host, nas_script_path, dry_run, verbose)

    remote_cmd = [nas_script_path] + nas_script_args
    ssh_execute(nas_host, nas_user, remote_cmd, True, dry_run=dry_run)


def launch_pre_backup_script(pre_backup_script: list[dict] | None, filter_shares: list[str], verbose=False) -> None:
    if not pre_backup_script:
        return
    logger.debug(f"Filter shares: {filter_shares}")
    shares_to_handle = ",".join([vol for vol in pre_backup_script["shares"] if vol in filter_shares])
    logger.debug(f"Shares to handle: {shares_to_handle}")
    pre_backup_script_final = [s.replace("%i", shares_to_handle) for s in pre_backup_script["script"]]
    run_subprocess(pre_backup_script_final, verbose=verbose)


def list_names(items: list[str]) -> None:
    print(f"Available backup item names: {', '.join([i.get('name') for i in items])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup using rclone to NAS and/or cloud")
    parser.add_argument("--all", "-a", action="store_true", dest="all_targets", help="Backup to NAS and cloud")
    parser.add_argument("--nas", "-n", action="store_true", help="Backup local to NAS")
    parser.add_argument("--cloud", "-c", action="store_true", help="Backup to cloud")
    parser.add_argument("--list-names", "-l", action="store_true", help="List backup item names")
    parser.add_argument(
        "--from-nas",
        action="store_true",
        help="Used with --cloud: execute cloud backup from NAS via SSH instead of local->cloud",
    )
    parser.add_argument(
        "--nas-script-args",
        default=[],
        action=SplitArgs,
        help="Comma-separated args passed to the NAS script",
    )
    parser.add_argument("--names", default=[], action=SplitArgs, help="Comma-separated list of backup names to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (passes --dry-run to rclone)")
    parser.add_argument(
        "--config",
        default=str(SCRIPT_DIR / "backup_config.yaml"),
        help="Path to config YAML file (default: backup_config.yaml next to this script)",
    )

    args = parser.parse_args()
    dry_run = args.dry_run
    verbose = args.verbose

    setup_logger(verbose)

    do_nas = args.nas or args.all_targets
    do_cloud = args.cloud or args.all_targets

    config_path = Path(args.config)
    if not config_path.exists():
        fail(f"Config file not found: {config_path}")

    config = load_config(config_path)
    items: list[dict] = config["items"]

    if args.list_names:
        list_names(items)
        sys.exit(0)

    filter_names = args.names
    if len(filter_names) > 0:
        non_existing_names = [n for n in filter_names if n not in [i.get("name") for i in items]]
        if len(non_existing_names):
            fail(f"The provided names does not match any items: {non_existing_names}")
        items = [i for i in items if i.get("name") in filter_names]
        logger.info(f"Filtered to {len(items)} item(s): {filter_names}")

    filter_shares = list(set([i["nas_share"] for i in items]))
    launch_pre_backup_script(config.get("pre_backup_script"), filter_shares, verbose)

    if do_nas:
        for item in items:
            name = item.get("name", "<unnamed>")
            if item.get("cloud_only") or item.get("from_nas_only"):
                logger.debug(f"Skipping NAS backup for '{name}' (cloud_only/from_nas_only)")
                continue
            backup_to_nas(item, dry_run, verbose)

    if do_cloud:
        if args.from_nas:
            from_nas_items = []
            for item in items:
                name = item.get("name", "<unnamed>")
                if item.get("local_to_nas_only"):
                    logger.debug(f"Skipping from-NAS cloud backup for '{name}' (local_to_nas_only)")
                    continue
                from_nas_items.append(item)
            execute_from_nas(config, from_nas_items, args.nas_script_args, dry_run, verbose)
        else:
            for item in items:
                name = item.get("name", "<unnamed>")
                if item.get("local_to_nas_only"):
                    logger.debug(f"Skipping cloud backup for '{name}' (local_to_nas_only)")
                    continue
                if item.get("from_nas_only"):
                    logger.debug(f"Skipping local->cloud for '{name}' (from_nas_only; use --from-nas)")
                    continue
                backup_to_cloud(item, dry_run, verbose)


if __name__ == "__main__":
    main()
