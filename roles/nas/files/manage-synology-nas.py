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
import time
from pathlib import Path

import requests
import urllib3
from requests.exceptions import ConnectionError, SSLError
from wakeonlan import send_magic_packet

SCRIPT_DIR = Path(__file__).parent
TOKEN_FILE_PATH = Path.home() / ".nas-token"
PING_TIMEOUT = 1
EXIT_CODE_FAILED = 1
REQUESTS_TIMEOUT = 60
SLEEP_TIME = 10
ENCRYPT = "encrypt"
DECRYPT = "decrypt"

logger = logging.getLogger(Path(__file__).stem)
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
    formatter = logging.Formatter("%(asctime)s [%(levelname)-8s] %(name)s: %(message)s")
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


def ping_test(host, should_fail=True):
    command = ["ping", "-q", "-c", "1", "-W", str(PING_TIMEOUT), host]
    response = subprocess.call(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if response != 0:
        if should_fail:
            fail(f"Ping {host} failed")
        else:
            return False
    else:
        logger.info(f"Ping {host} OK")
        return True


def wake_up_nas_and_wait_for_ping(host, mac):
    logger.info(f"Wake up {host}")
    send_magic_packet(mac)
    count = 0
    while True:
        if count == 30:
            fail(f"{host} did not wake up on time or is not reachable at all")
        logger.debug(f"Waiting {SLEEP_TIME} second(s) for {host} to be reachable")
        time.sleep(SLEEP_TIME)
        if ping_test(host, False):
            break
        count += 1


def login_attempt(url, credentials):
    params = {
        "api": "SYNO.API.Auth",
        "version": "6",
        "method": "login",
        "account": credentials["username"],
        "passwd": credentials["password"],
        "session": "FileStation",
        "format": "sid",
    }
    return session.get(f"{url}/webapi/auth.cgi", params=params, timeout=REQUESTS_TIMEOUT)


def parse_response(resp):
    if resp.status_code != 200:
        return {"success": False}
    json_out = resp.json()
    logger.trace(json_out)
    return json_out


def dsm_api_test(url, should_fail=True):
    try:
        r = login_attempt(url, {"username": "invalid", "password": "invalid"})
        data = parse_response(r)
        # 400 = wrong credentials → auth daemon is up and rejecting properly
        if data.get("error", {}).get("code") == 400:
            logger.info("DSM API ready")
            ret = {"succeed": True}
        else:
            ret = {"succeed": False, "msg": "DSM started, but API not yet ready"}
    except SSLError:
        fail("SSLError, did you forget to use --no-verify option?")
    except ConnectionError:
        ret = {"succeed": False, "msg": "DSM starting"}

    if should_fail and not ret.get("succeed"):
        fail(ret.get("msg"))
    else:
        return ret


def wait_for_dsm_api_to_be_ready(url):
    count = 0
    sleep_time = 1
    while True:
        if count == 300:
            fail(f"DSM login API on {url} failed to be ready on time")
        ret = dsm_api_test(url, False)
        if ret.get("succeed"):
            return
        logger.debug(f"Waiting {sleep_time} second(s) for DSM login API on {url} to be ready ({ret.get('msg')})")
        time.sleep(sleep_time)
        count += 1


def get_token_from_file():
    logger.info("Get token from file")
    return TOKEN_FILE_PATH.read_text()


def request_succeeded(data):
    return data.get("success", False)


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
    r = login_attempt(url, credentials)
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
    parser.add_argument("--port", "-p", help="Synology http port", default=5001, type=int)
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
    parser.add_argument("--shares", help="Comma-separated share names", action=SplitArgs, default=[])
    parser.add_argument("--crypt-action", help="Action to do", choices=[ENCRYPT, DECRYPT])
    parser.add_argument("--verbose", "-v", help="Verbose mode (v or vv for trace)", action="count", default=0)

    wake_up_nas_group = parser.add_argument_group("wake-up-nas", "Options for waking up the NAS")
    wake_up_nas_group.add_argument(
        "--wake-up-nas", "-w", help="Wake up NAS and wait for its readiness", action="store_true", default=False
    )
    wake_up_nas_group.add_argument("--mac", "-m", help="Synology MAC address used for wake on lan", type=str)

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

    if args.wake_up_nas:
        if not args.mac:
            parser.error("--mac is required when --wake-up-nas is specified")
        if not ping_test(args.host, False):
            wake_up_nas_and_wait_for_ping(args.host, args.mac)
        wait_for_dsm_api_to_be_ready(url)
    else:
        ping_test(args.host)
        dsm_api_test(url)

    if not args.crypt_action:
        logger.warning("No --crypt-action specified, exiting...")
        sys.exit(0)

    if not args.shares:
        logger.warning("No --shares specified, exiting...")
        sys.exit(0)

    token = get_and_write_token(url, credentials)

    for share in args.shares:
        share_action(url, token, share_passwords, share, args.crypt_action)
        if args.crypt_action == DECRYPT:
            test_share(url, token, share)


if __name__ == "__main__":
    setup_logger(logger)
    main()
