import os
import sys
import xml.etree.ElementTree as ET
from glob import glob

from .box import RPGmusicbox


class NoValidRPGboxError(ValueError):
	''' Custom Exception for use when there is an error with the RPGbox XML file. '''

	pass


def read_xml(filename):
	'''
	Reads all information from the given XML file.

	:param filename: String with the filename or path of the XML file
	:returns: A RPGmusicbox object with all information from the XML file
	:raises: NoValidRPGboxError
	'''

	box = RPGmusicbox()

	# Read in the file, parse it and point to root
	root = ET.parse(filename).getroot()

	# Basic tag checking
	if root.tag != 'rpgbox':
		raise NoValidRPGboxError('No valid RPGmusicbox XML file!')


	# If a config is given, read it. If not, use default values.
	colors = {}
	try:
		config = next(root.iter('config'))
		colors['text'] = config.get('textcolor', default = '')
		colors['bg'] = config.get('bgcolor', default = '')
		colors['emph'] = config.get('emphcolor', default = '')
		colors['fade'] = config.get('fadecolor', default = '')
		box.update_colors(colors, default=True)
	except StopIteration:
		pass


	# Scan through globals
	for global_tag in root.iter('globals'):
		# Get the globals volume. If not available, use default volume. If outside margins, set to margins.
		# The globals volume is eventually not saved but directly taken account of for each sound effect and music
		globals_volume = int(global_tag.get('volume', default = box.DEFAULT_VOLUME)) / 100

		for effect in global_tag.iter('effect'):
			_add_global_effect(effect, globals_volume, box)


	# Scan through themes
	for i, theme in enumerate(root.iter('theme')):
		_add_theme(theme, globals_volume, box)

	# Test, whether there is at least one theme in the whole box
	if i == 0:
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


def _interpret_bool(s):
	'''
	Interprets whether a string is "falsy" or "truthy"

	:param s: The sting to be interpreted
	:returns: True or False depending on the string
	'''

	return s.lower() in {'yes', 'y', 'true', '1', 'on'}


def _add_global_effect(effect, global_volume, box):
	# Get name of the global effect (each global effect must have a name!)
	try:
		effect_name = effect.attrib['name']
	except KeyError:
		raise NoValidRPGboxError('A global effect without name was found. Each global effect must have a name!')

	# Get the keyboard key of the effect (each global effect must have a unique key!)
	try:
		effect_key = effect.attrib['key'][0].lower() # get only first char and make it lowercase.
		effect_ID = ord(effect_key)
	except KeyError:
		raise NoValidRPGboxError('The global effect {} has no key. Each global effect must have a unique keyboard key!'.format(effect_name))

	# Get the effect file from the tag attribute
	try:
		effect_file = effect.attrib['file']
		if not os.path.isfile(effect_file):
			effect_file = None
	except KeyError:
		raise NoValidRPGboxError('No file given in global effect {}.'.format(effect_name))
	if effect_file is None:
		raise NoValidRPGboxError('File {} for global effect {} not found.'.format(effect.attrib['file'], effect_name))

	# Get potential volume of the effect. Alter it by the globals volume
	effect_volume = globals_volume * int(effect.get('volume', default = box.DEFAULT_VOLUME)) / 100

	# Check, whether the effect should interrupt everything else
	interrupting = ('interrupting' in effect.attrib and _interpret_bool(effect.attrib['interrupting']))

	# Save the global effect
	box.add_global_effect(
		kid = effect_ID,
		filename = effect_file,
		key = effect_key,
		name = effect_name,
		volume = effect_volume,
		interrupting = interrupting,
	)


def _add_theme(theme, global_volume, box):
	# Get the theme name. Each theme must have a name!
	try:
		theme_name = theme.attrib['name']
	except KeyError:
		raise NoValidRPGboxError('A theme without name was found. Each theme must have a name!')

	# Get the keyboard key of the theme (each theme must have a unique key!)
	try:
		theme_key = theme.attrib['key'][0].lower() # get only first char and make it lowercase.
		theme_ID = ord(theme_key)
	except KeyError:
		raise NoValidRPGboxError('The theme {} has no key. Each theme must have a unique keyboard key!'.format(theme_name))

	# Get the theme volume. If not available, use default volume.
	# The theme volume is eventually not saved but directly taken account of for each sound effect and music
	theme_volume = int(theme.get('volume', default = box.DEFAULT_VOLUME)) / 100

	# Read theme basetime (How often soundeffects appear)
	# The basetime is eventually not saved but directly taken account of for each sound effect
	basetime = int(theme.get('basetime', default = box.DEFAULT_BASETIME))
	basetime = box.ensure_basetime(basetime)

	# If a config is given, read it. If not, use default values.
	colors = {}
	try:
		config = next(theme.iter('config'))
		colors['text'] = config.get('textcolor', default = '')
		colors['bg'] = config.get('bgcolor', default = '')
		colors['emph'] = config.get('emphcolor', default = '')
		colors['fade'] = config.get('fadecolor', default = '')
	except StopIteration:
		pass

	# Create the theme
	box.add_theme(theme_ID, theme_name, colors)

	# Initiate the occurrences list. First element must be 0
	occurrences = [0]

	# Scan through all subtags and get data like background songs and sound effects
	for subtag in theme:

		# <background> tag found
		if subtag.tag == 'background':
			# Get the song file(s) from the attribute of the tag (can be a glob)
			try:
				song_files = glob(subtag.attrib['file'])
			except KeyError:
				raise NoValidRPGboxError('No file given in background of {}'.format(theme_name))
			if not song_files:
				raise NoValidRPGboxError('File {} not found in {}'.format(subtag.attrib['file'], theme_name))

			# Get potential volume of song. Alter it by the theme volume
			volume = theme_volume * int(subtag.get('volume', default = box.DEFAULT_VOLUME)) / 100

			# Save each song with its volume. If a filename occurs more than once, basically, the volume is updated
			for song_file in sorted(song_files):
				name = prettify_path(song_file)
				box.add_song(
					kid = theme_ID,
					path = song_file,
					name = name,
					volume = volume,
				)

		# <effect> tag found
		elif subtag.tag == 'effect':
			# Get the sound file(s) from the attribute of the tag (can be a glob)
			try:
				sound_files = glob(subtag.attrib['file'])
			except KeyError:
				raise NoValidRPGboxError('No file given in effect of {}'.format(theme_name))
			if not sound_files:
				raise NoValidRPGboxError('File {} not found in {}'.format(subtag.attrib['file'], theme_name))

			# Get relative volume of the sound. Alter it by the theme volume
			volume = theme_volume * int(subtag.get('volume', default = box.DEFAULT_VOLUME)) / 100

			# Get occurrence of the sound. Alter it by the theme basetime
			occurrence = int(subtag.get('occurrence', default = box.DEFAULT_OCCURRENCE * basetime))
			occurrence = box.ensure_occurrence(occurrence / basetime)

			# Get cooldown of the sound.
			cooldown = float(subtag.get('cooldown', default = box.DEFAULT_COOLDOWN))

			# Check, whether the effect should run indefinitely (i.e. it should loop)
			loop = ('loop' in subtag.attrib and _interpret_bool(subtag.attrib['loop']))

			# Save each sound with its volume. If a filename occurs more than once, basically, the volume and occurrence are updated
			for sound_file in sound_files:
				name = prettify_path(sound_file)
				box.add_sound(
					kid = theme_ID,
					path = sound_file,
					name = name,
					volume = volume,
					cooldown = cooldown,
					loop = loop,
				)
				occurrences.append(occurrences[-1] + occurrence)

		# config tag found. That was already analysed, so we just ignore it silently
		elif subtag.tag == 'config':
			continue

		# other tag found. We just ignore it.
		else:
			print('Unknown Tag {}. Ignoring it.'.format(attr.tag), file=sys.stderr)

	# Ensure, that all sounds CAN be played. If the sum of occurrences is higher than one, normalize to one
	if occurrences[-1] > box.MAX_OCCURRENCE:
		divisor = occurrences[-1]
		for i in range(len(occurrences)):
			occurrences[i] /= divisor

	# Add occurrences to the theme
	box.add_occurrences(theme_ID, occurrences[1:])
