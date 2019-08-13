import os
import sys
from glob import glob

from .box import RPGmusicbox, NoValidRPGboxError


def read_path(path):
	'''
	Reads all information from the given path.

	:param path: String with the path
	:returns: An RPGmusicbox object with all information from the path
	:raises: NoValidRPGboxError
	'''

	box = RPGmusicbox()

	globals_path = os.path.join(path, 'globals')

	if os.path.isdir(globals_path):
		_add_global_effects(globals_path, box)


	# Scan through themes
	for p in glob(os.path.join(path, '*')):
		if p != globals_path and os.path.isdir(p):
			_add_theme(p, box)

	# Test, whether there is at least one theme in the whole box
	if not box.get_ids()[1]:
		raise NoValidRPGboxError('No theme found! There must be at least one theme!')

	return box


def prettify_path(path):
	'''
	Extracts the filename without extension from path and turns underscores to spaces.

	:param path: String with the full path
	:returns: The prettified filename
	'''

	path = os.path.basename(path)
	path = os.path.splitext(path)[0]
	path = path.replace('_', ' ')

	return path


def _add_global_effects(path, box):
	n = 0
	for filename in sorted(glob(os.path.join(path, '*'))):
		# Ignore directories
		if os.path.isdir(filename):
			continue

		n += 1
		if n > 10:
			raise NoValidRPGboxError('No more than 10 global effects are allowed in path mode.')
		effect_name = prettify_path(filename)
		effect_key = str(n%10)
		effect_id = ord(effect_key)

		# Save the global effect
		box.add_global_effect(
			kid=effect_id,
			filename=filename,
			name=effect_name,
			volume=100,
			interrupting=True,
		)


# TODO: This should be split in multiple functions!
def _add_theme(path, box):
	theme_name = prettify_path(path)

	id1, id2 = box.get_ids()
	taken_keys = [chr(x) for x in id1+id2]

	theme_key = None
	for char in theme_name.lower():
		if char.isalpha() and char not in taken_keys:
			theme_key = char

	if theme_key is None:
		raise NoValidRPGboxError('No key can be assigned to {}'.format(theme_name))

	theme_id = ord(theme_key)

	# Create the theme
	box.add_theme(theme_id, theme_name, {})

	# Initiate the occurrences list. First element must be 0
	occurrences = [0]

	# Scan through all subtags and get data like background songs and sound effects
	for filename in glob(os.path.join(path, '*')):

		if filename.endswith('.mp3') or filename.endswith('*.ogg'):
			box.add_song(
				kid=theme_id,
				path=filename,
				name=prettify_path(filename),
				volume=100,
			)

		elif filename.endswith('.wav'):
			box.add_sound(
				kid=theme_id,
				path=filename,
				name=prettify_path(filename),
				volume=100,
				cooldown=10,
				loop=False,
			)
			occurrences.append(occurrences[-1] + 1)


	# Ensure, that all sounds CAN be played.
	# If the sum of occurrences is higher than one, normalize to one
	if occurrences[-1] > box.MAX_OCCURRENCE:
		divisor = occurrences[-1]
		for i in range(len(occurrences)):
			occurrences[i] /= divisor

	# Add occurrences to the theme
	box.add_occurrences(theme_id, occurrences[1:])
