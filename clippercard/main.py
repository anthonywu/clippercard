"""
ClipperCard Client

Usage:
  clippercard (-h | --version)
  clippercard summary
"""

import clippercard
import docopt
import sys

def main():
	args = docopt.docopt(__doc__, argv=sys.argv, version=clippercard.__version__)
	if args['--version']:
		print(clippercard.__version__)

if __name__ == '__main__':
    main()
