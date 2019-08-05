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
		colors['background'] = config.get('bgcolor', default = '')
		colors['emph'] = config.get('emphcolor', default = '')
		colors['fade'] = config.get('fadecolor', default = '')
		box.update_colors(colors, default=True)
	except StopIteration:
		pass


	# Scan through globals
	for globalTag in root.iter('globals'):
		# Get the globals volume. If not available, use default volume. If outside margins, set to margins.
		# The globals volume is eventually not saved but directly taken account of for each sound effect and music
		globalsVolume = int(globalTag.get('volume', default = box.DEFAULT_VOLUME)) / 100

		for effect in globalTag.iter('effect'):
			_add_global_effect(effect, globalsVolume, box)


	# Scan through themes
	for i, theme in enumerate(root.iter('theme')):
		_add_theme(theme, globalsVolume, box)

	# Test, whether there is at least one theme in the whole box
	if i == 0:
		raise NoValidRPGboxError('No theme found! There must be at least one theme!')


	return box


def prettifyPath(path):
	'''
	Extracts the filename without extension from path and turns underscores to spaces.

	:param path: String with the full path
	:returns: The prettified filename
	'''

	path = os.path.basename(path)
	path = os.path.splitext(path)[0]
	path = path.replace('_', ' ')

	return path


def _interpretBool(s):
	'''
	Interprets whether a string is "falsy" or "truthy"

	:param s: The sting to be interpreted
	:returns: True or False depending on the string
	'''

	return s.lower() in {'yes', 'y', 'true', '1', 'on'}


def _add_global_effect(effect, global_volume, box):
	# Get name of the global effect (each global effect must have a name!)
	try:
		effectName = effect.attrib['name']
	except KeyError:
		raise NoValidRPGboxError('A global effect without name was found. Each global effect must have a name!')

	# Get the keyboard key of the effect (each global effect must have a unique key!)
	try:
		effectKey = effect.attrib['key'][0].lower() # get only first char and make it lowercase.
		effectID = ord(effectKey)
	except KeyError:
		raise NoValidRPGboxError('The global effect {} has no key. Each global effect must have a unique keyboard key!'.format(effectName))

	# Get the effect file from the tag attribute
	try:
		effectFile = effect.attrib['file']
		if not os.path.isfile(effectFile):
			effectFile = None
	except KeyError:
		raise NoValidRPGboxError('No file given in global effect {}.'.format(effectName))
	if effectFile is None:
		raise NoValidRPGboxError('File {} for global effect {} not found.'.format(effect.attrib['file'], effectName))

	# Get potential volume of the effect. Alter it by the globals volume
	effectVolume = globalsVolume * int(effect.get('volume', default = box.DEFAULT_VOLUME)) / 100

	# Check, whether the effect should interrupt everything else
	interrupting = ('interrupting' in effect.attrib and _interpretBool(effect.attrib['interrupting']))

	# Save the global effect
	box.add_global_effect(
		kid = effectID,
		filename = effectFile,
		key = effectKey,
		name = effectName,
		volume = effectVolume,
		interrupting = interrupting,
	)


def _add_theme(theme, global_volume, box):
	# Get the theme name. Each theme must have a name!
	try:
		themeName = theme.attrib['name']
	except KeyError:
		raise NoValidRPGboxError('A theme without name was found. Each theme must have a name!')

	# Get the keyboard key of the theme (each theme must have a unique key!)
	try:
		themeKey = theme.attrib['key'][0].lower() # get only first char and make it lowercase.
		themeID = ord(themeKey)
	except KeyError:
		raise NoValidRPGboxError('The theme {} has no key. Each theme must have a unique keyboard key!'.format(themeName))

	# Get the theme volume. If not available, use default volume.
	# The theme volume is eventually not saved but directly taken account of for each sound effect and music
	themeVolume = int(theme.get('volume', default = box.DEFAULT_VOLUME)) / 100

	# Read theme basetime (How often soundeffects appear)
	# The basetime is eventually not saved but directly taken account of for each sound effect
	basetime = int(theme.get('basetime', default = box.DEFAULT_BASETIME))
	basetime = box.ensureBasetime(basetime)

	# If a config is given, read it. If not, use default values.
	colors = {}
	try:
		config = next(theme.iter('config'))
		colors['text'] = config.get('textcolor', default = '')
		colors['background'] = config.get('bgcolor', default = '')
		colors['emph'] = config.get('emphcolor', default = '')
		colors['fade'] = config.get('fadecolor', default = '')
	except StopIteration:
		pass

	# Create the theme
	box.add_theme(themeID, themeName, colors)

	# Initiate the occurrences list. First element must be 0
	occurrences = [0]

	# Scan through all subtags and get data like background songs and sound effects
	for subtag in theme:

		# <background> tag found
		if subtag.tag == 'background':
			# Get the song file(s) from the attribute of the tag (can be a glob)
			try:
				songFiles = glob(subtag.attrib['file'])
			except KeyError:
				raise NoValidRPGboxError('No file given in background of {}'.format(themeName))
			if not songFiles:
				raise NoValidRPGboxError('File {} not found in {}'.format(subtag.attrib['file'], themeName))

			# Get potential volume of song. Alter it by the theme volume
			volume = themeVolume * int(subtag.get('volume', default = box.DEFAULT_VOLUME)) / 100

			# Save each song with its volume. If a filename occurs more than once, basically, the volume is updated
			for songFile in sorted(songFiles):
				name = prettifyPath(songFile)
				box.add_song(
					kid = themeID,
					path = songFile,
					name = name,
					volume = volume,
				)

		# <effect> tag found
		elif subtag.tag == 'effect':
			# Get the sound file(s) from the attribute of the tag (can be a glob)
			try:
				soundFiles = glob(subtag.attrib['file'])
			except KeyError:
				raise NoValidRPGboxError('No file given in effect of {}'.format(themeName))
			if not soundFiles:
				raise NoValidRPGboxError('File {} not found in {}'.format(subtag.attrib['file'], themeName))

			# Get relative volume of the sound. Alter it by the theme volume
			volume = themeVolume * int(subtag.get('volume', default = box.DEFAULT_VOLUME)) / 100

			# Get occurrence of the sound. Alter it by the theme basetime
			occurrence = int(subtag.get('occurrence', default = box.DEFAULT_OCCURRENCE * basetime))
			occurrence = box._ensureOccurrence(occurrence / basetime)

			# Get cooldown of the sound.
			cooldown = float(subtag.get('cooldown', default = box.DEFAULT_COOLDOWN))

			# Check, whether the effect should run indefinitely (i.e. it should loop)
			loop = ('loop' in subtag.attrib and _interpretBool(subtag.attrib['loop']))

			# Save each sound with its volume. If a filename occurs more than once, basically, the volume and occurrence are updated
			for soundFile in soundFiles:
				name = prettifyPath(soundFile)
				box.add_sound(
					kid = themeID,
					path = soundFile,
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
	box.add_occurrences(themeID, occurrences[1:])
