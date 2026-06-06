"""
ClipperCard Client - CLI entry point
"""

import argparse
import configparser
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

import clippercard
import clippercard.porcelain


class ClipperCardCommandError(Exception):
    pass


_CREDENTIAL_STORE_SERVICE = "clippercard.credentials"


def _init_config_file(config_file_path):
    """Initialize a config file with template structure."""
    os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
    template = """\
[default]
username = <replace_with_your_email>
password = <replace_with_your_password>
"""
    with open(config_file_path, "w") as f:
        f.write(template)
    print(f"Created config file: {config_file_path}")


def _run_keychain(*args, input_text=None):
    if sys.platform != "darwin":
        raise ClipperCardCommandError("macOS Keychain credential storage is only supported on macOS")
    kwargs = {}
    if input_text is not None:
        kwargs["input"] = input_text
    return subprocess.run(
        ["security", *args],
        check=False,
        capture_output=True,
        text=True,
        **kwargs,
    )


def _load_keychain_auth(account):
    result = _run_keychain(
        "find-generic-password",
        "-s",
        _CREDENTIAL_STORE_SERVICE,
        "-a",
        account,
        "-w",
    )
    if result.returncode != 0:
        return None
    try:
        credentials = json.loads(result.stdout)
        return credentials["username"], credentials["password"]
    except (KeyError, TypeError, json.JSONDecodeError) as err:
        raise ClipperCardCommandError(f"Keychain credentials for account {account!r} are unreadable") from err


def _keychain_item_exists(service, account):
    if sys.platform != "darwin":
        return False
    result = _run_keychain("find-generic-password", "-s", service, "-a", account)
    return result.returncode == 0


def _save_keychain_auth(account, username, password):
    result = _run_keychain(
        "add-generic-password",
        "-U",
        "-s",
        _CREDENTIAL_STORE_SERVICE,
        "-a",
        account,
        "-w",
        input_text=json.dumps({"username": username, "password": password}),
    )
    if result.returncode != 0:
        raise ClipperCardCommandError(f"Unable to save credentials to macOS Keychain: {result.stderr.strip()}")


def _get_config_or_arg_auth(args):
    """
    Finds/parses the username and password from either the args or a config file.

    :returns: a tuple of (username, password)
    """
    username, password = args.username, args.password
    if not (username and password):
        config_file_path = os.path.expanduser(args.config)
        if not os.path.exists(config_file_path):
            response = input(f"Config file {config_file_path} does not exist. Create it? (y/n): ").strip().lower()
            if response == "y":
                _init_config_file(config_file_path)
                raise ClipperCardCommandError(
                    f"Config file created. Please edit {config_file_path} and add your credentials."
                )
            else:
                raise ClipperCardCommandError(
                    f"Login config file {config_file_path} does not exist. "
                    "Use --username and --password flags or create a config file."
                )
        try:
            parser = configparser.ConfigParser()
            parser.read(config_file_path)
            section = args.account
            username, password = parser.get(section, "username"), parser.get(section, "password")
        except configparser.NoSectionError as err:
            raise ClipperCardCommandError(
                f"Account config section {args.account!r} is not found in {config_file_path}"
            ) from err
    return username, password


def _config_auth_available(args):
    username, password = args.username, args.password
    if username and password:
        return True

    config_file_path = os.path.expanduser(args.config)
    if not os.path.exists(config_file_path):
        return False

    parser = configparser.ConfigParser()
    parser.read(config_file_path)
    try:
        section = args.account
        parser.get(section, "username")
        parser.get(section, "password")
    except (configparser.NoSectionError, configparser.NoOptionError):
        return False
    return True


def _arg_auth_available(args):
    return bool(args.username and args.password)


def _get_client_auth_with_source(args):
    if args.credential_store == "keychain":
        if _arg_auth_available(args):
            return _get_config_or_arg_auth(args), "config"
        credentials = _load_keychain_auth(args.account)
        if credentials:
            return credentials, "keychain"
        return _get_config_or_arg_auth(args), "config"

    if args.credential_store is None:
        if _config_auth_available(args):
            return _get_config_or_arg_auth(args), "config"
        credentials = _load_keychain_auth(args.account)
        if credentials:
            return credentials, "keychain"

    return _get_config_or_arg_auth(args), "config"


def _get_client_auth(args):
    credentials, source = _get_client_auth_with_source(args)
    args._credential_source = source
    return credentials


def _resolve_credential_store(args):
    if args.credential_store is not None:
        return args.credential_store
    if _config_auth_available(args):
        return "config"
    if _keychain_item_exists(_CREDENTIAL_STORE_SERVICE, args.account):
        return "keychain"
    return "config"


def _cookie_jar_path_for_account(account, cookie_jar_path=None):
    """
    Returns the cookie jar path for a config section.

    The default account keeps using auth.cookies for backwards compatibility.
    Other accounts get a section-specific cookie jar so saved sessions do not
    collide across profiles.
    """
    base_path = Path(cookie_jar_path).expanduser() if cookie_jar_path else clippercard.Session.COOKIE_JAR_PATH
    if not account or account == "default":
        return base_path

    safe_account = re.sub(r"[^A-Za-z0-9._-]+", "_", account).strip("._")
    if not safe_account:
        safe_account = "account"

    if base_path.suffix:
        cookie_name = f"{base_path.stem}.{safe_account}{base_path.suffix}"
    else:
        cookie_name = f"{base_path.name}.{safe_account}"
    return base_path.with_name(cookie_name)


def _resolve_cookie_store(args, cookie_jar_path=None):
    if args.cookie_store is not None:
        return args.cookie_store

    cookie_jar_path = cookie_jar_path or _cookie_jar_path_for_account(args.account)
    if cookie_jar_path.exists():
        return "file"
    if _keychain_item_exists(clippercard.Session.COOKIE_STORE_SERVICE, args.account):
        return "keychain"
    return "file"


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="clippercard",
        description="Unofficial CLI for Clipper Card (SF Bay Area transit pass)",
    )
    parser.add_argument("-v", "--version", action="version", version=clippercard.__version__)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command")

    summary = subparsers.add_parser("summary", help="Show account summary")
    summary.add_argument("--debug", action="store_true", help="Enable debug logging")
    summary.add_argument(
        "--show-private", action="store_true", help="Show private information like card numbers (use with caution)"
    )
    summary.add_argument(
        "--output",
        choices=("table", "json"),
        default=None,
        help="Output format (default: table when interactive, json when piped)",
    )

    auth_group = summary.add_argument_group("authentication")
    auth_group.add_argument(
        "--account",
        default="default",
        help="Account section name in config file (default: default)",
    )
    auth_group.add_argument(
        "--config",
        default="~/.config/clippercard/credentials.ini",
        help="Account login config file path (default: ~/.config/clippercard/credentials.ini)",
    )
    auth_group.add_argument("--username", help="Login username (instead of config file)")
    auth_group.add_argument("--password", help="Login password (instead of config file)")
    auth_group.add_argument(
        "--credential-store",
        choices=("config", "keychain"),
        default=None,
        help="Login credential storage backend (default: config, or keychain when config is unavailable)",
    )

    cookie_group = summary.add_argument_group("cookie storage")
    cookie_group.add_argument(
        "--cookie-store",
        choices=("file", "keychain"),
        default=None,
        help="Saved cookie storage backend (default: file, or keychain when the file jar is unavailable)",
    )

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        cookie_jar_path = _cookie_jar_path_for_account(args.account)
        credential_store = _resolve_credential_store(args)
        cookie_store = _resolve_cookie_store(args, cookie_jar_path=cookie_jar_path)
        args.credential_store = credential_store
        args.cookie_store = cookie_store
        username, password = _get_client_auth(args)
        session = clippercard.Session(
            username,
            password,
            cookie_jar_path=cookie_jar_path,
            cookie_store=cookie_store,
            keychain_account=args.account,
        )
        if credential_store == "keychain" and getattr(args, "_credential_source", "config") != "keychain":
            _save_keychain_auth(args.account, username, password)
        if args.command == "summary":
            output = args.output or ("table" if sys.stdout.isatty() else "json")
            if session.reused_cookies:
                cookie_storage_label = getattr(session, "cookie_storage_label", session.cookie_jar_path)
                cookie_message = f"Reusing saved cookies from {cookie_storage_label}"
                if output == "json":
                    print(cookie_message, file=sys.stderr)
                else:
                    print(cookie_message)
            if output == "json":
                print(
                    clippercard.porcelain.summary_json_output(
                        session.profile_info, session.cards, show_private=args.show_private
                    )
                )
            else:
                print(
                    clippercard.porcelain.tabular_output(
                        session.profile_info, session.cards, show_private=args.show_private
                    )
                )
    except (clippercard.client.ClipperCardError, ClipperCardCommandError, FileNotFoundError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
