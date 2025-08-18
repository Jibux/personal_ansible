#!/usr/bin/env python3


# Found api methods in nas:
# find /usr -name '*SYNO*lib' | sort
# cat /usr/syno/synoman/webapi/SYNO.Core.Share.lib | jq 'keys'
# cat /usr/syno/synoman/webapi/SYNO.Core.Share.lib |jq '.["SYNO.Core.Share.Crypto"]'

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
TOKEN_FILE_PATH = SCRIPT_DIR / ".nas-token"
PING_TIMEOUT = 1
EXIT_CODE_FAILED = 1

logger = logging.getLogger(__name__)


def setup_trace_level():
    trace_level = 5

    def trace(self, message, *args, **kwargs):
        if self.isEnabledFor(trace_level):
            self._log(trace_level, message, args, **kwargs)

    logging.Logger.trace = trace
    setattr(logging, "TRACE", trace_level)
    logging.addLevelName(trace_level, "TRACE")


def setup_logger(lo):
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)-6s %(message)s", "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    lo.addHandler(handler)
    lo.setLevel(logging.INFO)
    setup_trace_level()


def fail(msg="Something wrong happened", exit_code=EXIT_CODE_FAILED):
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


def parse_response(resp):
    if resp.status_code != 200:
        return {"success": False}
    json_out = resp.json()
    logger.trace(json_out)
    return json_out


def request_succeeded(data):
    return data.get("success", False)


def get_token_from_file():
    logger.info("Get token from file")
    return TOKEN_FILE_PATH.read_text()


def test_token(url, token):
    logger.debug("Test token")
    params = {
        "api": "SYNO.Core.Share",
        "version": "1",
        "method": "list",
        "_sid": token,
    }
    r = requests.get(f"{url}/webapi/entry.cgi", params, verify=False)
    data = parse_response(r)
    if request_succeeded(data):
        logger.debug("Test token succeeded")
        return True
    else:
        logger.debug("Test token failed")
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
    data = parse_response(r)
    if not request_succeeded(data):
        fail("Login failed!")
    return data["data"]["sid"]


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
    return token


def volume_action(url, token, volume_passwords, volume, action):
    # FIXME: if action is decrypt, volume password is not needed
    volume_password = volume_passwords.get(volume)
    if volume_password is None:
        fail(f"Password not found for volume {volume}")
    params = {
        "api": "SYNO.Core.Share.Crypto",
        "version": "1",
        "method": action,
        "name": volume,
        "password": volume_password,
        "_sid": token,
    }
    r = requests.post(f"{url}/webapi/entry.cgi", params, verify=False)
    data = parse_response(r)
    if request_succeeded(data):
        logger.info(f"{action} {volume} succeeded")
    else:
        fail(f"{action} volume {volume} failed!")


def test_volume(url, token, volume):
    params = {
        "api": "SYNO.FileStation.List",
        "version": "2",
        "method": "list",
        "folder_path": f"\"/{volume}\"",
        "limit": 1,
        "_sid": token,
    }
    r = requests.post(f"{url}/webapi/entry.cgi", params, verify=False)
    data = parse_response(r)
    if request_succeeded(data):
        logger.info(f"Test volume {volume} succeeded")
    else:
        fail(f"Test volume {volume} failed!")


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
    parser.add_argument(
        "-a", "--action", help="Action to do", choices=["encrypt", "decrypt"], default="decrypt")
    parser.add_argument('-v', '--verbose', help="Verbose mode (v or vv for trace)", action='count', default=0)
    args = parser.parse_args()
    if args.verbose == 1:
        logger.setLevel(logging.DEBUG)
    elif args.verbose == 2:
        logger.setLevel(logging.TRACE)
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
    volume_action(url, token, volume_passwords, args.volume, args.action)
    if args.action == "decrypt":
        test_volume(url, token, args.volume)


if __name__ == "__main__":
    setup_logger(logger)
    main()
