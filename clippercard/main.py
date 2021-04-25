"""
ClipperCard Client

Usage:
  clippercard (-h | --version)
  clippercard summary {auth_args}

Options:
  -h --help             Show this screen.
  -v --version          Show version.
  --account=<acct>      Optional, account section name in ~/.clippercardrc config [Default: default].
  --config=<cfg>        Optional, account login config file path [Default: ~/.clippercardrc].
  --username=<user>     Optional, login username if not using config file.
  --password=<pass>     Optional, login password if not using config file.
"""

__doc__ = __doc__.format(
    auth_args="([--account=<acct>] [--config=<cfg>] | [ (--username=<user> --password=<pass>) ])"
)

import configparser
import logging
import os
import sys

import docopt
import clippercard
import clippercard.porcelain


class ClipperCardCommandError(Exception):
    pass


def _get_client_auth(args):
    """
    Finds/parses the username and password from either the args or a config file.

    :returns: a tuple of (username, password)
    """
    username, password = args["--username"], args["--password"]
    if not (username and password):
        config_file_path = os.path.expanduser(args["--config"])
        if not os.path.exists(config_file_path):
            raise ClipperCardCommandError(
                "Login config file {0} does not exist.".format(config_file_path)
            )
        try:
            parser = configparser.SafeConfigParser()
            parser.read(config_file_path)
            section = args["--account"]
            username, password = parser.get(section, "username"), parser.get(
                section, "password"
            )
        except configparser.NoSectionError:
            raise ClipperCardCommandError(
                "Account config section {0} is not found in {1}".format(
                    repr(args["--account"]), config_file_path
                )
            )
    return username, password


def main():
    args = docopt.docopt(__doc__, version=clippercard.__version__)
    if args["--version"]:
        print(clippercard.__version__)
        sys.exit(0)

    try:
        username, password = _get_client_auth(args)
        session = clippercard.Session(username, password)
        if args["summary"]:
            print(
                clippercard.porcelain.tabular_output(
                    session.profile_info, session.cards
                )
            )
    except (clippercard.client.ClipperCardError, ClipperCardCommandError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
