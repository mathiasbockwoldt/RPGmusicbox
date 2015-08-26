#!/usr/bin/env python
#-*- coding:utf-8 -*-

# # # #  To do  # # # #
#
# Must haves
# - Provide example "box" with songs and sounds and global effects in the public domain
#
# Ideas
# - Config for individual fonts, background, etc. for box and themes?
# - The screen output could be further improved
# - Allow for "silence" instead of background music (also in addition to background music -> music - 2 min silence - music)
#   + This could be realized with a <silence prob="50" duration="10-20"> tag in a theme. prob is the probability (in percent) after each song that silence comes and duration is the possible duration of silence in seconds.
#
# Bugs
# - Long song/sound names leave a trace at the right end of the screen
# - Interrupting global effects must be tested in all combinations with the pause/unpause and allowMusic/Sounds functions
# - Cooldown time of sounds is not stopped by pausing or interrupting global effects
#

from __future__ import generators, division, with_statement, print_function

import pygame
import sys
import os
import copy
import random
import xml.etree.ElementTree as ET
from glob import glob


class NoValidRPGboxError(Exception):
	''' Custom Exception for use when there is an error with the RPGbox XML file. '''
	pass


class Playlist(object):
	''' Contains a playlist that is dynamically extended, taking care that no song is repeated directly '''

	def __init__(self, songs, remember = 5):
		'''
		Initiates the playlist.

		:param songs: List of available songs
		:param remember: How many songs shall (minimum) be remembered to allow going back
		'''

		if songs:
			self.remember = int(remember)
		else:
			self.remember = 0

		self.songs = songs[:]
		self.playlist = []
		self.nowPlaying = -1

		while len(self.playlist) < self.remember:
			self._extendPlaylist()


	def _extendPlaylist(self):
		''' Extends the playlist, taking care that no song is repeated directly '''

		if len(self.songs) == 1:
			self.playlist.append(self.songs[0])
		else:
			newSonglist = self.songs[:]
			random.shuffle(newSonglist)

			if self.playlist:
				# prevent two songs from being played one after another (but don't try it indefinitely long)
				i = 0
				while newSonglist[0] == self.playlist[-1]:
					if i >= 10:
						break
					random.shuffle(newSonglist)
					i += 1

			self.playlist.extend(newSonglist)


	def _shortenPlaylist(self):
		''' Cuts away parts in the beginning of the playlist to save memory '''

		pass ############ (Do I ever need this? Memory consumption of the list is low anyway...)


	def nextSong(self):
		''' :returns: The next song '''

		if not self.playlist:
			return None

		if self.nowPlaying > len(self.playlist) - self.remember:
			self._extendPlaylist()

		self.nowPlaying += 1

		return self.playlist[self.nowPlaying]


	def previousSong(self):
		''' :returns: The previous song (if there is any) '''

		if not self.playlist:
			return None

		self.nowPlaying -= 1

		if self.nowPlaying >= 0:
			return self.playlist[self.nowPlaying]
		else:
			self.nowPlaying = 0	# In case, previousSong() is called multiple times while in the beginning of the list, the pointer needs to be reset to 0, such that nextSong() starts at 0 again.
			return None


	def getSongsForViewing(self):
		'''
		:returns: A list with three songs that are the previous, current and next song. If there is only one song in the whole playlist, the list will have only one element. If the current song is the first one in the playlist, the list will have only two elements.
		'''

		if not self.playlist:
			return None

		# If there is only one song in total
		if len(self.songs) == 1:
			return self.songs	# [the_only_song]

		# If the first song did not yet start to play
		if self.nowPlaying < 0:
			return ['', self.playlist[0]]	# ['', next]

		# If the first song plays
		if self.nowPlaying == 0:
			return self.playlist[0:2]	# [current, next]

		# Usual playing
		return self.playlist[self.nowPlaying - 1: self.nowPlaying + 2]	# [prev, current, next]


	# CLASS Playlist END


class Theme(object):
	'''
	Container for one theme including its songs and sounds.
	'''

	def __init__(self, key, name, colorText, colorBackground, colorEmph, colorFade, songs = [], sounds = [], occurences = []):
		'''
		Initiates the theme.

		:param key: The keyboard key to activate the theme. Must be a one-letter string.
		:param name: String with the name of the theme.
		:param colorText: The text color for this theme
		:param colorBackground: The background color for this theme
		:param colorEmph: The emphasizing color for this theme
		:param colorFade: The fading color for this theme
		:param songs: A list with songs in the theme.
		:param sounds: A list with sounds in the theme.
		:param occurences: A list with occurences of the songs in the theme.
		'''

		self.key = str(key)[0]
		self.name = str(name)

		self.songs = songs[:]
		self.sounds = sounds[:]
		self.occurences = occurences[:]

		self.colorText = colorText
		self.colorBackground = colorBackground
		self.colorEmph = colorEmph
		self.colorFade = colorFade


	def __str__(self):
		''' :returns: A string representation of the theme with all songs and sounds. '''

		ret = []
		ret.append(''.join((self.key, ') ', self.name)))
		ret.append('Songs:')
		for s in self.songs:
			ret.append('    ' + str(s))
		ret.append('Sounds:')
		for s in self.sounds:
			ret.append('    ' + str(s))

		return '\n'.join(ret)


	def addSong(self, song):
		'''
		Add a song to the theme.

		:param song: The song to add
		'''

		self.songs.append(song)


	def addSound(self, sound):
		'''
		Add a sound to the theme

		:param sound: The sound to add
		'''

		self.sounds.append(sound)


	def addOccurences(self, occurences):
		'''
		Adds a list of occurences to the theme. The total number of occurences after the addition must be the same as the total number of songs in the theme. So add the songs first.

		:param occurences: List of occurences of the songs
		:raises KeyError: When the total number of occurences does not fit the total number of songs in the theme
		'''

		self.occurences.extend(occurences)

		if len(self.occurences) != len(self.sounds):
			raise KeyError('The number of sounds is not equal to the number of occurences in {}!'.format(self.name))

		for i in range(len(self.sounds)):
			self.sounds[i].occurence = self.occurences[i]


	# CLASS Theme END


class Sound(object):
	'''
	Container for one sound.
	'''

	def __init__(self, filename, name, volume = 100, cooldown = 10, occurence = 0.01):
		'''
		Initiates the sound.

		:param filename: String with the filename
		:param name: String with the name
		:param volume: Integer with the relative volume (already adjusted by the theme volume)
		:param cooldown: Float with the cooldown time in seconds
		:param occurence: Float with relative occururence (already adjusted by the theme basetime)
		'''

		self.filename = str(filename)
		self.name = str(name)
		self.volume = int(volume)
		self.cooldown = float(cooldown)
		self.occurence = float(occurence)


	def __str__(self):
		''' :returns: A string representation of the sound with all attributes. '''

		return ''.join((self.filename, ' (vol: ', str(self.volume), ', occ: ', '{:.4f}'.format(self.occurence), ', cd: ', str(self.cooldown), ')'))


	# CLASS Sound END


class Song(object):
	'''
	Container for one song.
	'''

	def __init__(self, filename, name, volume = 100):
		'''
		Initiates the song.

		:param filename: String with the filename
		:param name: String with the name
		:param volume: Integer with the relative volume (already adjusted by the theme volume)
		'''

		self.filename = str(filename)
		self.name = str(name)
		self.volume = int(volume)


	def __str__(self):
		''' :returns: A string representation of the song with its volume. '''

		return ''.join((self.filename, ' (vol: ', str(self.volume), ')'))


	# CLASS Song END


class GlobalEffect(object):
	'''
	Container for one global effect.
	'''

	def __init__(self, filename, key, name, volume = 100, interrupting = True):
		'''
		Initiates the global effect.

		:param filename: String with the filename
		:param key: The keyboard key to activate the global effect. Must be a one-letter string.
		:param name: String with the name
		:param volume: Integer with the relative volume (already adjusted by the theme volume)
		:param interrupting: Boolean that indicates, whether the global effect should interrupt playing music and sounds, or not.
		'''

		self.filename = str(filename)
		self.key = str(key)[0]
		self.name = str(name)
		self.volume = int(volume)
		self.interrupting = bool(interrupting)


	def __str__(self):
		''' :returns: A string representation of the global effect with its attributes. '''

		if self.interrupting:
			s = ', interrupting'
		else:
			s = ''
		return ''.join((self.key, ') ', self.name, ': ', self.filename, ' (vol: ', str(self.volume), s, ')'))


	# CLASS GlobalEffect END


class RPGbox(object):
	'''
	Contains music and sound information for an RPG evening.
	Reads infos from an XML file.
	'''

	# Default values
	DEFAULT_BASETIME = 3600		# Default basetime is 3600 seconds (1 hour)
	MIN_BASETIME = 1			# Minimum basetime is 1 second
	MAX_BASETIME = 36000		# Maximum basetime is 36 000 seconds (10 hours)
	DEFAULT_OCCURENCE = 0.01	# Default occurence is 0.01 (1% of basetime)
	MIN_OCCURENCE = 0			# Minimum occurence is 0 (never)
	MAX_OCCURENCE = 1			# Maximum occurence is 1 (always)
	DEFAULT_VOLUME = 100		# Default volume is 100%
	MIN_VOLUME = 0				# Minimum volume is 0%
	MAX_VOLUME = 100			# Maximum volume is 100%
	DEFAULT_COOLDOWN = 10		# Default cooldown is 10 seconds
	# MIN and MAX cooldown are not defined, as they are not needed

	# Default colors
	COLOR_TEXT = (0, 0, 0)			# Text color: black
	COLOR_BG = (255, 255, 255)		# Background color: white
	COLOR_EMPH = (200, 0, 0)		# Emphasizing color: red
	COLOR_FADE = (127, 127, 127)	# Fading color: grey


	def __init__(self, filename):
		'''
		Reads all information from the given XML file.

		:param filename: String with the filename of the XML file
		:raises: NoValidRPGboxError
		'''

		# Initiate class variables
		self.themes = {}		# Saves theme keys and connects them to theme object {themeID: Theme(), ...}
		self.globalEffects = {}	# Saves theme keys and connects them to global effect object {globalEffectID: GlobalEffect(), ...}

		# Read in the file, parse it and point to root
		root = ET.parse(filename).getroot()

		# Basic tag checking
		if root.tag != 'rpgbox':
			raise NoValidRPGboxError('No valid RPGbox file!')

		# If a config is given, read it. If not, use default values.
		try:
			config = next(root.iter('config')):
			self.colorText = pygame.Color(config.get('textcolor', default = self.COLOR_TEXT))
			self.colorBackground = pygame.Color(config.get('bgcolor', default = self.COLOR_BG))
			self.colorEmph = pygame.Color(config.get('emphcolor', default = self.COLOR_EMPH))
			self.colorFade = pygame.Color(config.get('fadecolor', default = self.COLOR_FADE))
		except StopIteration:
			self.colorText = pygame.Color(self.COLOR_TEXT))
			self.colorBackground = pygame.Color(self.COLOR_BG))
			self.colorEmph = pygame.Color(self.COLOR_EMPH))
			self.colorFade = pygame.Color(self.COLOR_FADE))

		# Scan through globals
		for globalTag in root.iter('globals'):
			# Get the globals volume. If not available, use default volume. If outside margins, set to margins.
			# The globals volume is eventually not saved but directly taken account of for each sound effect and music
			globalsVolume = int(globalTag.get('volume', default = self.DEFAULT_VOLUME))
			globalsVolume = self._ensureVolume(globalsVolume)

			for effect in globalTag.iter('effect'):
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
					raise NoValidRPGboxError('A global effect without key was found. Each global effect must have a unique keyboard key!')

				if effectID in self.globalEffects:
					raise NoValidRPGboxError('The key {} is already in use.'.format(effectKey))
				self._ensureValidID(effectID)	# Ensure that the id is valid

				# Get the effect file from the tag attribute
				try:
					effectFile = effect.attrib['file']
					if not os.path.isfile(effectFile):
						effectFile = None
				except KeyError:
					raise NoValidRPGboxError('No file given in global effect.')
				if effectFile is None:
					raise NoValidRPGboxError('File {} not found in global.'.format(effect.attrib['file']))

				# Get potential volume of the effect. Alter it by the globals volume
				effectVolume = int(effect.get('volume', default = self.DEFAULT_VOLUME))
				effectVolume = self._ensureVolume(int(effectVolume * globalsVolume / 100))

				# Check, whether the effect should interrupt everything else
				interrupting = ('interrupting' in effect.attrib)

				# Save the global effect
				self.globalEffects[effectID] = GlobalEffect(filename = effectFile, key = effectKey, name = effectName, volume = effectVolume, interrupting = interrupting)

		# Scan through themes
		for theme in root.iter('theme'):

			# Get the keyboard key of the theme (each theme must have a unique key!)
			try:
				themeKey = theme.attrib['key'][0].lower() # get only first char and make it lowercase.
				themeID = ord(themeKey)
			except KeyError:
				raise NoValidRPGboxError('A theme without key was found. Each theme must have a unique keyboard key!')

			if themeID in self.themes or themeID in self.globalEffects:
				raise NoValidRPGboxError('The key {} is already in use. Found in {}'.format(themeKey, themeID))
			self._ensureValidID(themeID)	# Ensure that the id is valid

			# Get the theme name. Each theme must have a name!
			try:
				themeName = theme.attrib['name']
			except KeyError:
				raise NoValidRPGboxError('A theme without name was found. Each theme must have a name!')

			# Get the theme volume. If not available, use default volume. If outside margins, set to margins.
			# The theme volume is eventually not saved but directly taken account of for each sound effect and music
			themeVolume = int(theme.get('volume', default = self.DEFAULT_VOLUME))
			themeVolume = self._ensureVolume(themeVolume)

			# Read theme basetime (How often soundeffects appear)
			# The basetime is eventually not saved but directly taken account of for each sound effect
			basetime = int(theme.get('basetime', default = self.DEFAULT_BASETIME))
			basetime = self._ensureBasetime(basetime)

			# If a config is given, read it. If not, use default values.
			try:
				config = next(theme.iter('config')):
				colorText = pygame.Color(config.get('textcolor', default = self.colorText))
				colorBackground = pygame.Color(config.get('bgcolor', default = self.colorBackground))
				colorEmph = pygame.Color(config.get('emphcolor', default = self.colorEmph))
				colorFade = pygame.Color(config.get('fadecolor', default = self.colorFade))
			except StopIteration:
				colorText = self.colorText)
				colorBackground = self.colorBackground)
				colorEmph = self.colorEmph)
				colorFade = self.colorFade)

			# Create the theme and add it to the themes dict
			self.themes[themeID] = Theme(key = themeKey, name = themeName, colorText = colorText, colorBackground = colorBackground, colorEmph = colorEmph, colorFade = colorFade)

			# Initiate the occurences list. First element must be 0
			occurences = [0]

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
					volume = int(subtag.get('volume', default = self.DEFAULT_VOLUME))
					volume = self._ensureVolume(int(volume * themeVolume / 100))

					# Save each song with its volume. If a filename occurs more than once, basically, the volume is updated
					for songFile in songFiles:
						name = self.prettifyPath(songFile)
						self.themes[themeID].addSong(Song(songFile, name, volume))

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
					volume = int(subtag.get('volume', default = self.DEFAULT_VOLUME))
					volume = self._ensureVolume(int(volume * themeVolume / 100))

					# Get occurence of the sound. Alter it by the theme basetime
					occurence = int(subtag.get('occurence', default = self.DEFAULT_OCCURENCE * basetime))
					occurence = self._ensureOccurence(occurence / basetime)

					# Get cooldown of the sound.
					cooldown = float(subtag.get('cooldown', default = self.DEFAULT_COOLDOWN))

					# Save each sound with its volume. If a filename occurs more than once, basically, the volume and occurence are updated
					for soundFile in soundFiles:
						name = self.prettifyPath(soundFile)
						self.themes[themeID].addSound(Sound(soundFile, name, volume, cooldown))
						occurences.append(occurences[-1] + occurence)

				# config tag found. That was already analysed, so we just ignore it silently
				elif subtag.tag == 'config':
					pass

				# other tag found. We just ignore it.
				else:
					print('Unknown Tag {}. Ignoring.'.format(attr.tag), file=sys.stderr)

			# Ensure, that all sounds CAN be played. If the sum of occurences is higher than one, normalize to one
			if occurences[-1] > self.MAX_OCCURENCE:
				divisor = occurences[-1]
				for i in range(len(occurences)):
					occurences[i] /= divisor

			# Add occurences to the theme
			self.themes[themeID].addOccurences(occurences[1:])

		# Test, whether there is at least one theme in the whole box
		if not self.themes:
			raise NoValidRPGboxError('No theme found! There must be at least one theme!')


	def __str__(self):
		''' :returns: All themes and global effects in the box. '''

		ret = ['RPGmusicbox', 'Themes']
		for t in sorted(self.themes.keys()):
			ret.append(str(self.themes[t]))

		ret.append('Global effects')

		for e in sorted(self.globalEffects.keys()):
			ret.append(str(self.globalEffects[e]))

		return '\n'.join(ret)


	def prettifyPath(self, path):
		'''
		Extracts the filename without extension from path and turns underscores to spaces.

		:param path: String with the full path
		:returns: The prettified filename
		'''

		path = os.path.basename(path)
		path = os.path.splitext(path)[0]
		path = path.replace('_', ' ')

		return path


	def _ensureValidID(self, kid):
		'''
		Ensures, that a given keyboard key (or rather its ID) is valid for the RPGbox.

		:param kid: The key ID to check (not the key, but its ID!)
		:raises: NoValidRPGboxError
		'''

		# Allowed: 0-9, a-z
		if not (48 <= kid <= 57 or 97 <= kid <= 122):
			raise NoValidRPGboxError('The key {} is not in the allowed range (a-z and 0-9; lowercase only!)'.format(chr(kid)))


	def _ensureVolume(self, v):
		'''
		Ensures that a given volume is within the allowed range.

		:param v: The volume to check
		:returns: The volume, that is guaranteed to be within the allowed range
		'''

		if v < self.MIN_VOLUME:
			return self.MIN_VOLUME
		elif v > self.MAX_VOLUME:
			return self.MAX_VOLUME

		return v


	def _ensureBasetime(self, b):
		'''
		Ensures that a given basetime is within the allowed range.

		:param b: The basetime to check
		:returns: The basetime, that is guaranteed to be within the allowed range
		'''

		if b < self.MIN_BASETIME:
			return self.MIN_BASETIME
		elif b > self.MAX_BASETIME:
			return self.MAX_BASETIME

		return b


	def _ensureOccurence(self, o):
		'''
		Ensures that a given occurence is within the allowed range.

		:param o: The occurence to check
		:returns: The occurence, that is guaranteed to be within the allowed range
		'''

		if o < self.MIN_OCCURENCE:
			return self.MIN_OCCURENCE
		elif o > self.MAX_OCCURENCE:
			return self.MAX_OCCURENCE

		return o


	def getIDs(self):
		''' :returns: a tuple with two lists: the keys of all global IDs and the keys of all theme IDs '''

		return list(self.globalEffects.keys()), list(self.themes.keys())


	def getGlobalEffects(self):
		''' :returns: all global effects (a dict in the form {globalEffectID: GlobalEffectObject, ...}) '''

		return self.globalEffects


	def getTheme(self, themeID):
		'''
		:param themeID: The id of the theme to get
		:returns: The Theme object of the desired theme
		:raises KeyError: if the given themeID is no themeID
		'''

		if themeID in self.themes:
			return self.themes[themeID]
		else:
			raise KeyError('The key {} was not found as theme key.'.format(themeID))


	# CLASS RPGbox END


class Player(object):
	'''
	This class can read RPGbox objects and play music and sounds etc.
	'''

	def __init__(self, box, debug = True):
		'''
		Initiates all necessary stuff for playing an RPGbox.

		:param box: The RPGbox object to read from
		:param debug: Boolean that states, whether debugging texts should be send to STDOUT
		'''

		self.debug = debug

		self.box = box

		# Initialize pygame, screen and clock
		pygame.init()
		self.clock = pygame.time.Clock()
		self.screen = pygame.display.set_mode((800, 600))	# Screen is 800*600 px large
		pygame.display.set_caption('RPGbox player')		# Set window title

		# Get colors
		self.colorText = self.box.colorText
		self.colorBackground = self.box.colorBackground
		self.colorEmph = self.box.colorEmph
		self.colorFade = self.box.colorFade

		# Fill background
		self.background = pygame.Surface(self.screen.get_size()).convert()
		self.background.fill(self.colorBackground)
		self.screen.blit(self.background, (0, 0))
		pygame.display.flip()

		# Create my own event to indicate that a song stopped playing to trigger a new song
		self.SONG_END = pygame.USEREVENT + 1
		pygame.mixer.music.set_endevent(self.SONG_END)

		# Reserve a channel for global sound effects, such that a global sound can always be played
		self.GLOBAL_END = pygame.USEREVENT + 2
		pygame.mixer.set_reserved(1)
		self.globalChannel = pygame.mixer.Channel(0)
		self.globalChannel.set_endevent(self.GLOBAL_END)

		# Initiate text stuff
		self.standardFont = pygame.font.Font(None, 24)
		self.headerFont = pygame.font.Font(None, 32)

		w, h = self.background.get_size()
		self.displayWidth = w
		self.displayPanelWidth = w // 3
		self.displayFooterWidth = w // 5
		self.displayHeight = h
		self.displayPanelHeight = h - 2 * self.standardFont.size(' ')[1]
		self.displayFooterHeight = h - self.displayPanelHeight
		self.displayBorder = 5

		self.textGlobalKeys = pygame.Surface((self.displayPanelWidth, self.displayPanelHeight))
		self.textThemeKeys = pygame.Surface((self.displayPanelWidth, self.displayPanelHeight))
		self.textNowPlaying = pygame.Surface((self.displayPanelWidth, self.displayPanelHeight))
		self.textFooter = pygame.Surface((self.displayWidth, self.displayFooterHeight)) # The footer stretches horizontally to 100%. The displayFooterWidth is for the single elements in the footer.

		# Initialize variables
		self.globalIDs, self.themeIDs = self.box.getIDs()
		self.globalEffects = None
		self.initializeGlobalEffects()
		self.activeSounds = []
		self.activeGlobalEffect = None
		self.occurences = []
		self.playlist = Playlist([])
		self.activeTheme = None
		self.activeThemeID = None

		self.cycle = 0
		self.allowMusic = True
		self.allowSounds = True
		self.paused = False
		self.newSongWhilePause = False
		self.interruptingGlobalEffect = False
		self.activeChannels = []
		self.blockedSounds = {}	# {filename: timeToStartAgain, ...} ######## This does not work with pause or interrupting global effects! Maybe, I have to do the counting myself...

		# Start visualisation
		self.updateTextAll()


	def debugPrint(self, t):
		'''
		Prints the given text, if debugging (self.debug) is active.

		:param t: The text to print.
		'''

		if self.debug:
			print(t)


	def initializeGlobalEffects(self):
		'''
		Loads the file for each global effect to RAM and adjust its volume to have it ready.
		'''

		self.globalEffects = self.box.getGlobalEffects()

		for e in self.globalEffects:
			self.globalEffects[e].obj = pygame.mixer.Sound(self.globalEffects[e].filename)
			self.globalEffects[e].obj.set_volume(self.globalEffects[e].volume)


	def togglePause(self):
		''' Pause or unpause music and sounds, depending on the self.paused and self.interruptingGlobalEffect variables. '''

		if self.paused:
			self.debugPrint('Player unpaused')
			self.paused = False
			if self.interruptingGlobalEffect:
				if not self.globalChannel.get_busy():
					self.globalChannel.unpause()
			else:
				pygame.mixer.music.unpause()
				pygame.mixer.unpause()
				if self.newSongWhilePause:
					self.newSongWhilePause = False
					pygame.mixer.music.play()
		else:
			pygame.mixer.music.pause()
			pygame.mixer.pause()
			self.debugPrint('Player paused')
			self.paused = True
		self.updateTextFooter()


	def toggleAllowMusic(self):
		''' Allow or disallow music to be played. '''

		if self.allowMusic:
			self.allowMusic = False
			pygame.mixer.music.stop()
			self.playlist.nowPlaying -= 1	# Necessary to start with the same song, when music is allowed again
			self.updateTextNowPlaying()
			self.debugPrint('Music switched off')
		else:
			self.allowMusic = True
			pygame.event.post(pygame.event.Event(self.SONG_END))
			self.debugPrint('Music switched on')
		self.updateTextFooter()


	def toggleAllowSounds(self):
		''' Allow or disallow sounds to be played. '''

		if self.allowSounds:
			self.allowSounds = False
			if self.activeChannels:
				for c in self.activeChannels:
					c[1].stop()
			self.updateTextNowPlaying()
			self.debugPrint('Sound switched off')
		else:
			self.allowSounds = True
			self.debugPrint('Sound switched on')
		self.updateTextFooter()


	def updateTextAll(self):
		''' Update the whole screen. '''
		self.background.fill(self.colorBackground)
		self.updateTextGlobalEffects(update = False)
		self.updateTextThemes(update = False)
		self.updateTextNowPlaying(update = False)
		self.updateTextFooter(update = False)

		pygame.display.flip()


	def showLine(self, area, t, color, font):
		'''
		Prints one line of text to a panel.

		:param area: A rect with information, where the text shall be blitted on the background
		:param t: The text to be rendered
		:param color: The color of the text
		:param font: The font object that shall be rendered
		'''

		textRect = font.render(t, True, color)
		self.background.blit(textRect, area)
		area.top += font.get_linesize()


	def updateTextGlobalEffects(self, update = True):
		'''
		Update the global effects panel

		:param update: Boolean to state, whether the display should be updated
		'''

		self.textGlobalKeys.fill(self.colorBackground)
		r = self.background.blit(self.textGlobalKeys, (0, 0))

		area = self.textGlobalKeys.get_rect()
		area.left = self.displayBorder
		area.top = self.displayBorder

		self.showLine(area, 'Global Keys', self.colorText, self.headerFont)
		self.showLine(area, '', self.colorText, self.standardFont)

		for k in sorted(self.globalEffects.keys()):
			t = ''.join((chr(k), ' - ', self.globalEffects[k].name))
			if k == self.activeGlobalEffect:
				self.showLine(area, t, self.colorEmph, self.standardFont)
			else:
				self.showLine(area, t, self.colorText, self.standardFont)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(r)


	def updateTextThemes(self, update = True):
		'''
		Update the themes panel

		:param update: Boolean to state, whether the display should be updated
		'''

		self.textThemeKeys.fill(self.colorBackground)
		r = self.background.blit(self.textThemeKeys, (self.displayPanelWidth, 0))

		area = self.textThemeKeys.get_rect()
		area.left = self.displayPanelWidth + self.displayBorder
		area.top = self.displayBorder

		self.showLine(area, 'Themes', self.colorText, self.headerFont)
		self.showLine(area, '', self.colorText, self.standardFont)

		for k in sorted(self.box.themes.keys()):
			t = ''.join((chr(k), ' - ', self.box.themes[k].name))
			if k == self.activeThemeID:
				self.showLine(area, t, self.colorEmph, self.standardFont)
			else:
				self.showLine(area, t, self.colorText, self.standardFont)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(r)


	def updateTextNowPlaying(self, update = True):
		'''
		Update the now playing panel

		:param update: Boolean to state, whether the display should be updated
		'''

		self.textNowPlaying.fill(self.colorBackground)
		r = self.background.blit(self.textNowPlaying, (2 * self.displayPanelWidth, 0))

		area = self.textNowPlaying.get_rect()
		area.left = 2 * self.displayPanelWidth + self.displayBorder
		area.top = self.displayBorder

		self.showLine(area, 'Now Playing', self.colorText, self.headerFont)

		songs = self.playlist.getSongsForViewing()

		if songs is not None:
			self.showLine(area, '', self.colorText, self.standardFont)

			if len(songs) == 1:
				self.showLine(area, '>> ' + songs[0].name, self.colorEmph, self.standardFont)
			elif len(songs) == 2:
				if songs[0]:
					self.showLine(area, songs[0].name, self.colorEmph, self.standardFont)
				else:
					self.showLine(area, '', self.colorText, self.standardFont)
				self.showLine(area, songs[1].name, self.colorText, self.standardFont)
			else:
				self.showLine(area, songs[0].name, self.colorFade, self.standardFont)
				self.showLine(area, songs[1].name, self.colorEmph, self.standardFont)
				self.showLine(area, songs[2].name, self.colorText, self.standardFont)

		if self.activeChannels:
			toDelete = []
			for i in range(len(self.activeChannels)):
				if not self.activeChannels[i][1].get_busy():
					toDelete.append(i)

			for i in toDelete[::-1]:
				del(self.activeChannels[i])

			# all members may have been deleted, that's why here is a new `if`
			if self.activeChannels:
				self.showLine(area, '', self.colorText, self.standardFont)
				for c in sorted(self.activeChannels):
					self.showLine(area, c[0], self.colorEmph, self.standardFont)

		if self.blockedSounds:
			now = time.time()
			for k in self.blockedSounds.keys():
				if self.blockedSounds[k] < now:
					del(self.blockedSounds[k])

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(r)


	def showFooterElement(self, n, t1, t2, color, bgcolor, font):
		'''
		Helper function for self.updateTextFooter(). Prints two lines of text to screen in a given color.

		:param n: The number of the panel in the footer counted from the left (determines position)
		:param t1: First line of the text to be rendered
		:param t2: Second line of the text to be rendered
		:param color: The color of the text
		:param bgcolor: The background color
		:param font: The font object that shall be rendered
		'''

		s = pygame.Surface((self.displayFooterWidth, self.displayFooterHeight)).convert()
		s.fill(bgcolor)
		text1 = font.render(t1, True, color)
		text2 = font.render(t2, True, color)

		textPos1 = text1.get_rect()
		textPos2 = text2.get_rect()

		sPos = s.get_rect()

		textPos1.centerx = sPos.centerx
		textPos1.top = 0
		s.blit(text1, textPos1)

		textPos2.centerx = sPos.centerx
		textPos2.top = textPos1.height
		s.blit(text2, textPos2)

		sPos.top = self.displayPanelHeight
		sPos.left = n * self.displayFooterWidth

		self.background.blit(s, sPos)


	def updateTextFooter(self, update = True):
		'''
		Update the footer

		:param update: Boolean to state, whether the display should be updated
		'''

		self.textFooter.fill(self.colorBackground)
		r = self.background.blit(self.textFooter, (0, self.displayPanelHeight))

		if self.allowMusic:
			self.showFooterElement(0, 'F1', 'allow music', self.colorText, self.colorBackground, self.standardFont)
		else:
			self.showFooterElement(0, 'F1', 'allow music', self.colorBackground, self.colorText, self.standardFont)

		if self.allowSounds:
			self.showFooterElement(1, 'F2', 'allow sounds', self.colorText, self.colorBackground, self.standardFont)
		else:
			self.showFooterElement(1, 'F2', 'allow sounds', self.colorBackground, self.colorText, self.standardFont)

		if not self.paused:
			self.showFooterElement(2, 'Space', 'pause', self.colorText, self.colorBackground, self.standardFont)
		else:
			self.showFooterElement(2, 'Space', 'pause', self.colorBackground, self.colorText, self.standardFont)

		self.showFooterElement(3, 'F10', 'redraw screen', self.colorText, self.colorBackground, self.standardFont)

		self.showFooterElement(4, 'Escape', 'quit', self.colorText, self.colorBackground, self.standardFont)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(r)


	def playMusic(self, previous = False):
		'''
		Plays the next or previous song. Any playing song will be replaced by the new song.

		:param previous: If True, play previous song, if False, play next song.
		'''

		# If no music is allowed, don't do anything
		if not self.allowMusic:
			return

		if previous:
			nextSong = self.playlist.previousSong()
		else:
			nextSong = self.playlist.nextSong()

		if nextSong is not None:
			self.debugPrint('Now playing {} with volume {}'.format(nextSong.filename, nextSong.volume))
			pygame.mixer.music.load(nextSong.filename)
			pygame.mixer.music.set_volume(nextSong.volume / 100.0)
			if self.paused:
				self.newSongWhilePause = True
			else:
				if len(self.playlist.songs) == 1:
					pygame.mixer.music.play(-1)
				else:
					pygame.mixer.music.play()
			self.updateTextNowPlaying()
		else:
			if not previous and self.activeTheme is not None:
				self.debugPrint('No music available in theme {}'.format(self.activeTheme.name))


	def playGlobalEffect(self, effectID):
		'''
		Plays a global effect taking care of interrupting other music and sounds if necessary.

		:param effectID: The ID of the effect to be played.
		'''

		if self.globalChannel.get_busy():
			self.debugPrint('Reserved channel is busy! Effect key: {}'.format(chr(effectID)))

		if self.globalEffects[effectID].interrupting:
			self.interruptingGlobalEffect = True
			pygame.mixer.music.pause()
			for c in self.activeChannels:
				c[1].pause()

		self.activeGlobalEffect = effectID
		self.globalChannel.play(self.globalEffects[effectID].obj)

		self.updateTextGlobalEffects()
		self.updateTextNowPlaying()


	def stopGlobalEffect(self, byEndEvent = False):
		'''
		Stops a global effect, if it is still running.
		Takes care of restarting potentially interrupted music and sounds.

		:param byEndEvent: If True, this function is called, because the global effect stopped.
		'''

		self.activeGlobalEffect = None

		if not byEndEvent:
			self.globalChannel.stop()

		if not self.paused:
			pygame.mixer.music.unpause()
			pygame.mixer.unpause()
			#for c in self.activeChannels:	###
			#	c[1].unpause()

		self.interruptingGlobalEffect = False
		self.updateTextGlobalEffects()


	def playSound(self):
		'''
		Plays a random sound and adds its channel to the activeChannels list.
		'''

		# If sounds are not allowed, update the now playing panel and do nothing more
		if not self.allowSounds:
			self.updateTextNowPlaying()
			return

		if not self.paused and self.activeSounds and pygame.mixer.find_channel() is not None:
			rand = random.random()
			if rand < self.occurences[-1]:
				for i in range(len(self.occurences)): #### probably replace with bisect, if possible
					if self.occurences[i] > rand:
						if self.activeSounds[i].filename in self.blockedSounds:
							break
						newSound = self.activeSounds[i]
						self.debugPrint('Now playing sound {} with volume {}'.format(newSound.filename, newSound.volume))
						self.activeChannels.append((newSound.name, newSound.obj.play()))
						self.blockedSounds[newSound.filename] = time.time() + newSound.obj.get_length() + newSound.cooldown
						break
		self.updateTextNowPlaying()


	def activateNewTheme(self, themeID):
		'''
		Activates a new theme. All sounds of that theme are loaded and their volumes adjusted. A new playlist is initiated with all songs. All running sounds are stopped and new music is played.

		:param themeID: The ID of the theme to activate
		'''

		self.activeTheme = self.box.getTheme(themeID)
		self.activeThemeID = themeID

		self.debugPrint('New theme is {}'.format(self.activeTheme.name))

		# Update colors
		self.colorText = self.activeTheme.colorText
		self.colorBackground = self.activeTheme.colorBackground
		self.colorEmph = self.activeTheme.colorEmph
		self.colorFade = self.activeTheme.colorFade

		# Get sounds and load them into pygame
		self.activeSounds = copy.deepcopy(self.activeTheme.sounds)
		for i in range(len(self.activeSounds)):
			self.activeSounds[i].obj = pygame.mixer.Sound(self.activeSounds[i].filename)
			self.activeSounds[i].obj.set_volume(self.activeSounds[i].volume)

		self.playlist = Playlist(self.activeTheme.songs)

		self.occurences = self.activeTheme.occurences

		# Push a SONG_END event on the event stack to trigger the start of a new song (causes a delay of one cycle, but that should be fine)
		pygame.event.post(pygame.event.Event(self.SONG_END))

		pygame.mixer.stop()	# Stop all playing sounds

		self.updateTextAll()


	def start(self):
		'''
		Starts the main loop, that takes care of events (e.g. key strokes) and triggers random sounds.
		'''

		# remove clutter from the event queue
		pygame.event.set_allowed(None)
		pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, self.SONG_END, self.GLOBAL_END])

		# Start main loop
		while True:
			# Max 10 fps (More would be overkill, I think)
			self.clock.tick(10)

			# Let's see, what's in the event queue :)
			for event in pygame.event.get():

				# The program was quit (e.g. by clicking the X-button in the window title) -> quit and return
				if event.type == pygame.QUIT:
					pygame.quit()
					return

				# At least one key was pressed
				if event.type == pygame.KEYDOWN:

					# The Escape key was pressed -> quit and return
					if event.key == pygame.K_ESCAPE:
						pygame.quit()
						return

					# The space key was pressed -> (un)pause everything
					elif event.key == pygame.K_SPACE:
						self.togglePause()

					# The "->" key was pressed -> next song
					elif event.key == pygame.K_RIGHT:
						self.playMusic()

					# The "<-" key was pressed -> previous song
					elif event.key == pygame.K_LEFT:
						self.playMusic(previous = True)

					# The F1 key was pressed -> (dis)allow Music
					elif event.key == pygame.K_F1:
						self.toggleAllowMusic()

					# The F2 key was pressed -> (dis)allow Sounds
					elif event.key == pygame.K_F2:
						self.toggleAllowSounds()

					# The F10 key was pressed -> force redrawing of the whole screen
					####### This function is merely a helper function that should not be necessary when the program is mature
					elif event.key == pygame.K_F10:
						self.updateTextAll()

					# The key is the key of the active theme -> do nothing
					elif event.key == self.activeThemeID:
						pass

					# The key is the key of the active global effect -> stop it
					elif event.key == self.activeGlobalEffect:
						self.stopGlobalEffect()

					# The key is one of the theme keys -> activate the theme
					elif event.key in self.themeIDs:
						self.activateNewTheme(event.key)

					# The key is one of the global keys -> trigger effect
					elif event.key in self.globalIDs:
						self.playGlobalEffect(event.key)

				# The last song is finished (or a new theme was loaded) -> start new song, if available
				if event.type == self.SONG_END:
					self.playMusic()

				# A global effect is finished
				if event.type == self.GLOBAL_END:
					self.stopGlobalEffect(byEndEvent = True)

			# Sound effects can be triggered every tenth cycle (about every second).
			if self.cycle > 10:
				self.cycle = 0
				self.playSound()
			self.cycle += 1


	# CLASS Player END


if __name__ == '__main__':
	if len(sys.argv) == 2:
		filename = sys.argv[1]
	else:
		filename = 'test.xml'	### In the mature program, we need a message here

	# change working directory to the xml file's working directory, so that the paths to media are correct
	os.chdir(os.path.dirname(os.path.realpath(filename)))
	filename = os.path.basename(filename)	# The xml file is now at the root of the working directory, so no path is needed anymore

	box = RPGbox(filename)

	#print(box)

	player = Player(box)
	player.start()

