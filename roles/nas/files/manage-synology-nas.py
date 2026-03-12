#!/usr/bin/env python3


# Found api methods in nas:
# find /usr -name '*SYNO*lib' | sort
# cat /usr/syno/synoman/webapi/SYNO.Core.Share.lib | jq 'keys'
# cat /usr/syno/synoman/webapi/SYNO.Core.Share.lib |jq '.["SYNO.Core.Share.Crypto"]'
# Synology API documentation:
# * https://global.download.synology.com/download/Document/Software/DeveloperGuide/Package/FileStation/All/enu/Synology_File_Station_API_Guide.pdf
# * https://kb.synology.com/fr-fr/DG/DSM_Login_Web_API_Guide/1

import argparse
import logging
import subprocess
import sys
from pathlib import Path

import requests
import urllib3

SCRIPT_DIR = Path(__file__).parent
TOKEN_FILE_PATH = Path.home() / ".nas-token"
PING_TIMEOUT = 1
EXIT_CODE_FAILED = 1
REQUESTS_TIMEOUT = 60
ENCRYPT = "encrypt"
DECRYPT = "decrypt"

logger = logging.getLogger(__name__)
session = requests.Session()


class SplitArgs(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        setattr(namespace, self.dest, values.split(","))


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
    r = session.get(f"{url}/webapi/entry.cgi", params=params, timeout=REQUESTS_TIMEOUT)
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
    r = session.get(f"{url}/webapi/auth.cgi", params=params, timeout=REQUESTS_TIMEOUT)
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
    TOKEN_FILE_PATH.touch()
    TOKEN_FILE_PATH.chmod(0o600)
    TOKEN_FILE_PATH.write_text(token)
    return token


def share_action(url, token, share_passwords, share, action):
    # FIXME: if action is DECRYPT, share password is not needed
    share_password = share_passwords.get(share)
    if share_password is None:
        fail(f"Password not found for share {share}")
    params = {
        "api": "SYNO.Core.Share.Crypto",
        "version": "1",
        "method": action,
        "name": share,
        "password": share_password,
        "_sid": token,
    }
    r = session.post(f"{url}/webapi/entry.cgi", data=params, timeout=REQUESTS_TIMEOUT)
    data = parse_response(r)
    if request_succeeded(data):
        logger.info(f"{action} {share} succeeded")
    else:
        fail(f"{action} share {share} failed!")


def test_share(url, token, share):
    params = {
        "api": "SYNO.FileStation.List",
        "version": "2",
        "method": "list",
        "folder_path": f'"/{share}"',
        "limit": 1,
        "_sid": token,
    }
    r = session.post(f"{url}/webapi/entry.cgi", data=params, timeout=REQUESTS_TIMEOUT)
    data = parse_response(r)
    if request_succeeded(data):
        logger.info(f"Test share {share} succeeded")
    else:
        fail(f"Test share {share} failed!")


def dict_keys_str(d: dict):
    return ", ".join(list(d.keys()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="Synology host", default="nas")
    parser.add_argument("--port", "-p", help="Synology port", default=5001, type=int)
    parser.add_argument("--scheme", "-s", help="http/https", default="https", choices=["http", "https"])
    parser.add_argument("--no-verify", help="Skip ssl certificate validation", action="store_true", default=False)
    parser.add_argument(
        "--credentials", help="Path to the credentials file", type=Path, default=SCRIPT_DIR / ".nas-cred"
    )
    parser.add_argument(
        "--share-passwords-file",
        help="Path to the share passwords yaml file",
        type=Path,
        default=SCRIPT_DIR / ".nas-share-passwords",
    )
    parser.add_argument("--shares", help="Comma-separated share names", action=SplitArgs, required=True)
    parser.add_argument("--crypt-action", help="Action to do", choices=[ENCRYPT, DECRYPT])
    parser.add_argument("--verbose", "-v", help="Verbose mode (v or vv for trace)", action="count", default=0)
    args = parser.parse_args()

    if args.verbose == 1:
        logger.setLevel(logging.DEBUG)
    elif args.verbose == 2:
        logger.setLevel(logging.TRACE)

    if args.no_verify:
        session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = f"{args.scheme}://{args.host}:{args.port}"
    logger.info(f"url: {url}")
    logger.debug("Parse credentials file")
    credentials = parse_key_equal_value_file(args.credentials)
    logger.debug(f"Credentials keys: {dict_keys_str(credentials)}")
    logger.debug("Parse share passwords file")
    share_passwords = parse_key_equal_value_file(args.share_passwords_file)
    logger.debug(f"Volume passwords keys: {dict_keys_str(share_passwords)}")
    ping_test(args.host)
    token = get_and_write_token(url, credentials)
    if not args.crypt_action:
        sys.exit(0)
    for share in args.shares:
        share_action(url, token, share_passwords, share, args.crypt_action)
        if args.crypt_action == DECRYPT:
            test_share(url, token, share)


if __name__ == "__main__":
    setup_logger(logger)
    main()
