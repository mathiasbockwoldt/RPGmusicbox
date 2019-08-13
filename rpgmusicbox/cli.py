#!/usr/bin/env python3

import os
import sys
import argparse

from .player import Player

def cli():
	parser = argparse.ArgumentParser(description='Tool to bring music and sound effects to the game table.')

	parser.add_argument('-x', '--xml', help='Path to the XML file with the information')
	parser.add_argument('-j', '--json', help='Path to the JSON file with the information')
	parser.add_argument('-p', '--path', help='Path to the root of the sound files')

	args = parser.parse_args()

	if args.xml is None and args.json is None and args.path is None:
		parser.print_help()
		sys.exit()

	if bool(args.xml) + bool(args.json) + bool(args.path) > 1:
		print('Please provide only one file.', file=sys.stderr)
		parser.print_help()
		sys.exit()

	if args.xml:
		from .xml_reader import read_xml as reader
		filename = args.xml
	elif args.json:
		from .json_reader import read_json as reader
		filename = args.json
	elif args.path:
		from .path_reader import read_path as reader
		filename = args.path


	# change working directory to the xml file's working directory, so that the paths to media are correct
	os.chdir(os.path.dirname(os.path.realpath(filename)))

	# The config file is now at the root of the working directory, so no path is needed anymore
	filename = os.path.basename(filename)

	box = reader(filename)
	player = Player(box)
	player.start()
