#!/usr/bin/env python3

from setuptools import setup


long_description = open('readme.md').read()

version = {}
exec(open('rpgmusicbox/version.py').read(), version)

setup(
	name = 'rpg-music-box',
	version = version['__version__'],
	description = 'Tool to bring music and sound effects to the game table.',
	url = 'https://github.com/mathiasbockwoldt/RPGmusicbox',
	maintainer = 'Mathias Bockwoldt',
	author = 'Mathias Bockwoldt',
	long_description = long_description,
	long_description_content_type = 'text/markdown',
	packages = ['rpgmusicbox'],
	entry_points = {
		'console_scripts': ['rpgmusicbox = rpgmusicbox.cli:cli'],
	},
	classifiers = [
		'Development Status :: 3 - Alpha',
		'Programming Language :: Python :: 3 :: Only',
		'Programming Language :: Python :: 3.6',
		'Programming Language :: Python :: 3.7',
		'Natural Language :: English',
		'Operating System :: OS Independent',
		'Topic :: Games/Entertainment :: Board Games',
		'Topic :: Games/Entertainment :: Role-Playing',
		'Topic :: Multimedia :: Sound/Audio :: Players',
		'Topic :: Utilities',
	],
)
