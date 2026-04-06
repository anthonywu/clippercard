"""
ClipperCard fixture parsing CLI for tests and development.
"""

import argparse
import logging
import sys

import clippercard
import clippercard.parser
import clippercard.porcelain


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="clippercard-test",
        description="Test helpers for Clipper Card HTML fixtures",
    )
    parser.add_argument("-v", "--version", action="version", version=clippercard.__version__)
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command")

    parse_dashboard = subparsers.add_parser("parse-dashboard", help="Parse dashboard HTML fixture")
    parse_dashboard.add_argument("html_file", help="Path to dashboard HTML file")

    parse_profile = subparsers.add_parser("parse-profile", help="Parse profile HTML fixture")
    parse_profile.add_argument("html_file", help="Path to profile HTML file")

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        with open(args.html_file) as f:
            html_content = f.read()

        if args.command == "parse-dashboard":
            cards = clippercard.parser.parse_dashboard_cards(html_content)
            print(clippercard.porcelain.tabular_output(None, cards))
        elif args.command == "parse-profile":
            profile = clippercard.parser.parse_profile_page(html_content)
            print(clippercard.porcelain.tabular_output(profile, None))
    except FileNotFoundError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
