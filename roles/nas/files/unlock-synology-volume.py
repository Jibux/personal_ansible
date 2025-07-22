#!/usr/bin/env python3


import argparse
import logging
import subprocess
import sys
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


SCRIPT_DIR = Path(__file__).parent
TOKEN_FILE_PATH = SCRIPT_DIR / ".nas-token"
PING_TIMEOUT = 1
EXIT_CODE_FAILED = 1


def setup_logger(lo):
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)-6s %(message)s", "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    lo.addHandler(handler)
    lo.setLevel(logging.INFO)


def fail(msg, exit_code=EXIT_CODE_FAILED):
    logger.error(msg)
    sys.exit(exit_code)


def parse_key_equal_value_file(path: Path):
    content = path.read_text().splitlines()
    return {line.split("=")[0].strip(): line.split("=")[1].strip() for line in content}


def ping_test(host):
    command = ["ping", "-q", "-c", "1", "-W", str(PING_TIMEOUT), host]
    response = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if response != 0:
        fail(f"Ping {host} failed")
    else:
        logger.info(f"Ping {host} OK")


def get_token_from_file():
    logger.info("Get token from file")
    return TOKEN_FILE_PATH.read_text()[0]


def test_token(url, token):
    logger.info("Test token")
    params = {
        "api": "SYNO.???",
        "version": "6",
        "method": "???",
        "_sid": token,
    }
    r = requests.get(f"{url}/webapi/entry.cgi", params, verify=False)
    if r.status_code == 200:
        return True
    else:
        return False


def get_token_from_credentials(url, credentials):
    logger.info("Get token from credentials")
    params = {
        "api": "SYNO.API.Auth",
        "version": "6",
        "method": "login",
        "account": credentials["username"],
        "passwd": credentials["password"],
        "session": "FileStation",
        "format": "sid",
    }
    r = requests.get(f"{url}/webapi/auth.cgi", params, verify=False)
    return r.text


def get_token(url, credentials):
    if TOKEN_FILE_PATH.is_file():
        token = get_token_from_file()
        if test_token(url, token):
            return token
        else:
            return get_token_from_credentials(url, credentials)
    else:
        return get_token_from_credentials(url, credentials)


def get_and_write_token(url, credentials):
    token = get_token(url, credentials)
    TOKEN_FILE_PATH.write_text(token)


def unlock_volume(url, token, volume_passwords, volume):
    params = {
        "api": "SYNO.Core.Share.Crypto",
        "version": "1",
        "method": "decrypt",
        "name": volume,
        "password": volume_passwords[volume],
        "_sid": token,
    }
    r = requests.post(f"{url}/webapi/entry.cgi", params, verify=False)
    if r.status_code == 200:
        return True
    else:
        return False


def dict_keys_str(d: dict):
    return ", ".join(list(d.keys()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="Synology host", default="nas")
    parser.add_argument("-p", "--port", help="Synology port", default=5001, type=int)
    parser.add_argument("-s", "--scheme", help="http/https", default="https", choices=["http", "https"])
    parser.add_argument("-c", "--credentials", help="Path to the credentials file", type=Path, required=True)
    parser.add_argument(
        "--volume-passwords-file", help="Path to the volume passwords yaml file", type=Path, required=True
    )
    parser.add_argument("--volume", help="Volume name", required=True)
    parser.add_argument("-v", "--verbose", help="Verbose", action='store_true', default=False)
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    url = f"{args.scheme}://{args.host}:{args.port}"
    logger.info(f"url: {url}")
    logger.debug("Parse credentials file")
    credentials = parse_key_equal_value_file(args.credentials)
    logger.debug(f"Credentials keys: {dict_keys_str(credentials)}")
    logger.debug("Parse volume passwords file")
    volume_passwords = parse_key_equal_value_file(args.volume_passwords_file)
    logger.debug(f"Volume passwords keys: {dict_keys_str(volume_passwords)}")
    ping_test(args.host)
    token = get_and_write_token(url, credentials)
    unlock_volume(url, token, volume_passwords, args.volume)


if __name__ == "__main__":
    setup_logger(logger)
    main()
