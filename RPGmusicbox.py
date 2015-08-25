#!/usr/bin/env python
#-*- coding:utf-8 -*-

# # # #  To do  # # # #
#
# Must haves
# - Global effects must be able to interrupt normal playback
# - Allow for "silence" instead of background music (also in addition to background music -> music - 2 min silence - music)
# - Better documentation of the source code. At least a well-describing doc string for every class and method
#
# Ideas
# - Config for individual fonts, colors etc? Could be something like: <config bgcolor="#000000" color="#ff2222" />
# - Colors, background image, etc. depending on theme (as attribute)?
# - Default starting theme (defined in the xml file)
# - The screen output could be further improved
# - The extra keys like F1, F2, space and Esc could be shown in a kind of footer bar. Here, the status of pause, allowMusic, and allowSounds could be shown
#
# Bugs
# - Long song/sound names leave a trace at the right end of the screen
#

from __future__ import generators, division, with_statement, print_function

import pygame
import sys
import os.path
import copy
import random
import xml.etree.ElementTree as ET
from glob import glob


class NoValidRPGboxError(Exception):
	''' Custom Exception for use when there is an error with the RPGbox XML file. '''
	pass


class Playlist(object):
	''' Contains a playlist. '''

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
		''' Extends the playlist '''

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
		''' :returns: the next song '''

		if not self.playlist:
			return None

		if self.nowPlaying > len(self.playlist) - self.remember:
			self._extendPlaylist()

		self.nowPlaying += 1

		return self.playlist[self.nowPlaying]


	def previousSong(self):
		''' :returns: the previous song (if there is any) '''

		if not self.playlist:
			return None

		self.nowPlaying -= 1

		if self.nowPlaying >= 0:
			return self.playlist[self.nowPlaying]
		else:
			self.nowPlaying = 0	# In case, previousSong() is called multiple times while in the beginning of the list, the pointer needs to be reset to -1, such that nextSong() starts at 0 again.
			return None


	def getSongsForViewing(self):
		'''
		:returns: A list with three songs that are the previous, current and next song. If there is only one song in the whole playlist, the list will have only one element.
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
	Container for themes.
	'''

	def __init__(self, key, name, songs = [], sounds = [], occurences = []):
		self.key = str(key)[0]
		self.name = str(name)

		self.songs = songs[:]
		self.sounds = sounds[:]
		self.occurences = occurences[:]


	def __str__(self):
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
		self.songs.append(song)


	def addSound(self, sound):
		self.sounds.append(sound)


	def addOccurences(self, occurences):
		self.occurences.extend(occurences)

		if len(self.occurences) != len(self.sounds):
			raise KeyError('The number of sounds is not equal to the number of occurences in {}!'.format(self.name))

		for i in range(len(self.sounds)):
			self.sounds[i].occurence = self.occurences[i]


	# CLASS Theme END


class Sound(object):
	'''
	Container for a sound
	'''

	def __init__(self, filename, volume = 100, occurence = 0.01):
		self.filename = str(filename)
		self.volume = int(volume)
		self.occurence = float(occurence)


	def __str__(self):
		return ''.join((self.filename, ' (vol: ', str(self.volume), ', occ: ', '{:.4f}'.format(self.occurence), ')'))


	# CLASS Sound END


class Song(object):
	'''
	Container for a song
	'''

	def __init__(self, filename, volume = 100):
		self.filename = str(filename)
		self.volume = int(volume)


	def __str__(self):
		return ''.join((self.filename, ' (vol: ', str(self.volume), ')'))


	# CLASS Song END


class GlobalEffect(object):
	'''
	Container for a global effect
	'''

	# {'name': effectName, 'key': effectKey, 'volume': effectVolume, 'file': effectFile, 'interrupting': interrupting}
	def __init__(self, filename, key, name, volume = 100, interrupting = True):
		self.filename = str(filename)
		self.key = str(key)[0]
		self.name = str(name)
		self.volume = int(volume)
		self.interrupting = bool(interrupting)


	def __str__(self):
		if self.interrupting:
			s = ', interrupting'
		else:
			s = ''
		return ''.join((self.key, ') ', self.name, ': ', self.filename, ' (vol: ', str(self.volume), s, ')'))


	# CLASS GlobalEffect END


class RPGbox(object):
	'''
	Contains music and sound information for an RPG evening.
	Reads info from an XML file.
	'''

	DEFAULT_BASETIME = 3600		# Default basetime is 3600 seconds (1 hour)
	MIN_BASETIME = 1			# Minimum basetime is 1 second
	MAX_BASETIME = 36000		# Maximum basetime is 36 000 seconds (10 hours)
	DEFAULT_OCCURENCE = 0.01	# Default occurence is 0.01 (1% of basetime)
	MIN_OCCURENCE = 0			# Minimum occurence is 0 (never)
	MAX_OCCURENCE = 1			# Maximum occurence is 1 (always)
	DEFAULT_VOLUME = 100		# Default volume is 100%
	MIN_VOLUME = 0				# Minimum volume is 0%
	MAX_VOLUME = 100			# Maximum volume is 100%


	def __init__(self, filename):
		'''
		Reads all information from the given XML file `filename`.

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

		# Scan through globals
		for globalTag in root.iter('globals'):
			# Get the globals volume. If not available, use default volume. If outside margins, set to margins.
			# The globals volume is eventually not saved but directly taken account of for each sound effect and music
			try:
				globalsVolume = int(globalTag.attrib['volume'])
			except KeyError:
				globalsVolume = self.DEFAULT_VOLUME

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
				try:
					effectVolume = int(effect.attrib['volume'])
				except KeyError:
					effectVolume = self.DEFAULT_VOLUME
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

			# Get the theme name. If not available, use id as name
			try:
				themeName = theme.attrib['name']
			except KeyError:
				raise NoValidRPGboxError('A theme without name was found. Each theme must have a name!')

			# Get the theme volume. If not available, use default volume. If outside margins, set to margins.
			# The theme volume is eventually not saved but directly taken account of for each sound effect and music
			try:
				themeVolume = int(theme.attrib['volume'])
			except KeyError:
				themeVolume = self.DEFAULT_VOLUME

			themeVolume = self._ensureVolume(themeVolume)

			# Read theme basetime (How often soundeffects appear)
			# The basetime is eventually not saved but directly taken account of for each sound effect
			try:
				basetime = int(theme.attrib['basetime'])
			except KeyError:
				basetime = self.DEFAULT_BASETIME
			basetime = self._ensureBasetime(basetime)

			occurences = [0]

			self.themes[themeID] = Theme(key = themeKey, name = themeName)

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
					try:
						volume = int(subtag.attrib['volume'])
					except KeyError:
						volume = self.DEFAULT_VOLUME
					volume = self._ensureVolume(int(volume * themeVolume / 100))

					# Save each song with its volume. If a filename occurs more than once, basically, the volume is updated
					for songFile in songFiles:
						self.themes[themeID].addSong(Song(songFile, volume))

				# <effect> tag found
				elif subtag.tag == 'effect':
					# Get the sound file(s) from the attribute of the tag (can be a glob)
					try:
						soundFiles = glob(subtag.attrib['file'])
					except KeyError:
						raise NoValidRPGboxError('No file given in effect of {}'.format(themeName))
					if not soundFiles:
						raise NoValidRPGboxError('File {} not found in {}'.format(subtag.attrib['file'], themeName))

					# Get potential volume of the sound. Alter it by the theme volume
					try:
						volume = int(subtag.attrib['volume'])
					except KeyError:
						volume = self.DEFAULT_VOLUME
					volume = self._ensureVolume(int(volume * themeVolume / 100))

					# Get occurence of the sound. Alter it by the theme basetime
					try:
						occurence = int(subtag.attrib['occurence'])
					except KeyError:
						occurence = self.DEFAULT_OCCURENCE * basetime
					occurence = self._ensureOccurence(occurence / basetime)

					# Save each sound with its volume. If a filename occurs more than once, basically, the volume and occurence are updated
					for soundFile in soundFiles:
						self.themes[themeID].addSound(Sound(soundFile, volume))
						occurences.append(occurences[-1] + occurence)

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
		''' Used for print statements etc. Returns themes and global effects. Main use is debugging '''

		ret = ['RPGmusicbox', 'Themes']
		for t in sorted(self.themes.keys()):
			ret.append(str(self.themes[t]))

		ret.append('Global effects')

		for e in sorted(self.globalEffects.keys()):
			ret.append(str(self.globalEffects[e]))

		return '\n'.join(ret)


	def _ensureValidID(self, k):
		'''
		Ensures, that a given keyboard key resp. the ID is valid for the RPGbox.

		:raises: NoValidRPGboxError
		'''

		if not (48 <= k <= 57 or 97 <= k <= 122):
			# Allowed: 0-9, a-z
			raise NoValidRPGboxError


	def _ensureVolume(self, v):
		''' Ensures that a given volume is within the allowed range.'''

		if v < self.MIN_VOLUME:
			return self.MIN_VOLUME
		elif v > self.MAX_VOLUME:
			return self.MAX_VOLUME

		return v


	def _ensureBasetime(self, b):
		''' Ensures that a given basetime is within the allowed range.'''

		if b < self.MIN_BASETIME:
			return self.MIN_BASETIME
		elif b > self.MAX_BASETIME:
			return self.MAX_BASETIME

		return b


	def _ensureOccurence(self, o):
		''' Ensures that a given basetime is within the allowed range.'''

		if o < self.MIN_OCCURENCE:
			return self.MIN_OCCURENCE
		elif o > self.MAX_OCCURENCE:
			return self.MAX_OCCURENCE

		return o


	def getDefaultThemeID(self):
		''' Returns the default theme ID '''

		############## No possibility for default theme, yet!
		return None


	def getIDs(self):
		''' Returns a tuple with two dicts: the global IDs and the theme IDs '''

		return list(self.globalEffects.keys()), list(self.themes.keys())


	def getGlobalEffects(self):
		''' Returns the global effects '''

		return self.globalEffects


	def getTheme(self, themeID):
		''' Returns a dict with the selected theme, if it is available or None otherwise '''

		if themeID in self.themes:
			return self.themes[themeID]
		else:
			raise KeyError('The key {} was not found as theme key.'.format(themeID))


	# CLASS RPGbox END


class Player(object):

	WHITE = (255, 255, 255)
	BLACK = (0, 0, 0)
	RED = (200, 0, 0)
	GREY = (127, 127, 127)

	def __init__(self, box, debug = True):
		'''
		Initiates all necessary stuff for playing an RPGbox.
		'''

		self.debug = debug

		self.box = box

		# Initialize pygame, screen and clock
		pygame.init()
		self.clock = pygame.time.Clock()
		self.screen = pygame.display.set_mode((800, 600))	# Screen is 800*600 px large
		pygame.display.set_caption('RPGbox player')		# Set window title

		# Fill background
		self.background = pygame.Surface(self.screen.get_size()).convert()	# Define a background surface
		self.background.fill(self.WHITE)									# Fill the background with white

		self.screen.blit(self.background, (0, 0))
		pygame.display.flip()

		# Create my own event to indicate that a song stopped playing to trigger a new song
		self.SONG_END = pygame.USEREVENT + 1
		pygame.mixer.music.set_endevent(self.SONG_END)

		# Reserve a channel for global sound effects, such that a global sound can always be played
		pygame.mixer.set_reserved(1)
		self.globalChannel = pygame.mixer.Channel(0)

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
		self.activeThemeID = self.box.getDefaultThemeID()
		if self.activeThemeID:
			self.activateNewTheme(self.activeThemeID)

		self.cycle = 0
		self.paused = False
		self.allowMusic = True
		self.allowSounds = True
		self.newSongWhilePause = False
		self.activeChannels = []

		# Start visualisation
		self.updateTextAll()


	def togglePause(self):
		''' Pause or unpause music and sounds, depending on the self.paused variable. '''

		if self.paused:
			pygame.mixer.music.unpause()
			pygame.mixer.unpause()
			self.debugPrint('Player unpaused')
			self.paused = False
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
		''' Allow or disallow music to be played '''

		if self.allowMusic:
			self.allowMusic = False
			pygame.mixer.music.stop()
			self.playlist.previousSong()	# Necessary to start with the same song, when music is allowed again
			self.updateTextNowPlaying()
			self.debugPrint('Music switched off')
		else:
			self.allowMusic = True
			pygame.event.post(pygame.event.Event(self.SONG_END))
			self.debugPrint('Music switched on')
		self.updateTextFooter()


	def toggleAllowSounds(self):
		''' Allow or disallow sounds to be played '''

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


	def debugPrint(self, t):
		''' Prints the given text, if debugging is active. '''

		if self.debug:
			print(t)


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


	def updateTextAll(self):
		self.background.fill(self.WHITE)
		self.updateTextGlobalKeys(update = False)
		self.updateTextThemeKeys(update = False)
		self.updateTextNowPlaying(update = False)
		self.updateTextFooter(update = False)

		pygame.display.flip()


	def showLine(self, area, t, color, font):
		textRect = font.render(t, True, color)
		self.background.blit(textRect, area)
		area.top += font.get_linesize()


	def updateTextGlobalKeys(self, update = True):
		self.textGlobalKeys.fill(self.WHITE)
		r = self.background.blit(self.textGlobalKeys, (0, 0))

		area = self.textGlobalKeys.get_rect()
		area.left = self.displayBorder
		area.top = self.displayBorder

		self.showLine(area, 'Global Keys', self.BLACK, self.headerFont)
		self.showLine(area, '', self.BLACK, self.standardFont)

		for k in sorted(self.globalEffects.keys()):
			t = ''.join((chr(k), ' - ', self.globalEffects[k].name))
			if k == self.activeGlobalEffect:
				self.showLine(area, t, self.RED, self.standardFont)
			else:
				self.showLine(area, t, self.BLACK, self.standardFont)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(r)


	def updateTextThemeKeys(self, update = True):
		self.textThemeKeys.fill(self.WHITE)
		r = self.background.blit(self.textThemeKeys, (self.displayPanelWidth, 0))

		area = self.textThemeKeys.get_rect()
		area.left = self.displayPanelWidth + self.displayBorder
		area.top = self.displayBorder

		self.showLine(area, 'Themes', self.BLACK, self.headerFont)
		self.showLine(area, '', self.BLACK, self.standardFont)

		for k in sorted(self.box.themes.keys()):
			t = ''.join((chr(k), ' - ', self.box.themes[k].name))
			if k == self.activeThemeID:
				self.showLine(area, t, self.RED, self.standardFont)
			else:
				self.showLine(area, t, self.BLACK, self.standardFont)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(r)


	def updateTextNowPlaying(self, update = True):
		self.textNowPlaying.fill(self.WHITE)
		r = self.background.blit(self.textNowPlaying, (2 * self.displayPanelWidth, 0))

		area = self.textNowPlaying.get_rect()
		area.left = 2 * self.displayPanelWidth + self.displayBorder
		area.top = self.displayBorder

		self.showLine(area, 'Now Playing', self.BLACK, self.headerFont)

		songs = self.playlist.getSongsForViewing()

		if songs is not None:
			self.showLine(area, '', self.BLACK, self.standardFont)

			if len(songs) == 1:
				self.showLine(area, '>> ' + self.prettifyPath(songs[0].filename), self.RED, self.standardFont)
			elif len(songs) == 2:
				if songs[0]:
					self.showLine(area, self.prettifyPath(songs[0].filename), self.RED, self.standardFont)
				else:
					self.showLine(area, '', self.BLACK, self.standardFont)
				self.showLine(area, self.prettifyPath(songs[1].filename), self.BLACK, self.standardFont)
			else:
				self.showLine(area, self.prettifyPath(songs[0].filename), self.GREY, self.standardFont)
				self.showLine(area, self.prettifyPath(songs[1].filename), self.RED, self.standardFont)
				self.showLine(area, self.prettifyPath(songs[2].filename), self.BLACK, self.standardFont)

		if self.activeChannels:
			toDelete = []
			for i in range(len(self.activeChannels)):
				if not self.activeChannels[i][1].get_busy():
					toDelete.append(i)

			for i in toDelete[::-1]:
				del(self.activeChannels[i])

			# all members may have been deleted, that's why here is a new `if`
			if self.activeChannels:
				self.showLine(area, '', self.BLACK, self.standardFont)
				for c in sorted(self.activeChannels):
					self.showLine(area, self.prettifyPath(c[0]), self.RED, self.standardFont)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(r)


	def showFooterElement(self, n, t1, t2, color, bgcolor, font):
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
		self.textFooter.fill(self.WHITE)
		r = self.background.blit(self.textFooter, (0, self.displayPanelHeight))

		if self.allowMusic:
			self.showFooterElement(0, 'F1', 'allow music', self.BLACK, self.WHITE, self.standardFont)
		else:
			self.showFooterElement(0, 'F1', 'allow music', self.WHITE, self.BLACK, self.standardFont)

		if self.allowSounds:
			self.showFooterElement(1, 'F2', 'allow sounds', self.BLACK, self.WHITE, self.standardFont)
		else:
			self.showFooterElement(1, 'F2', 'allow sounds', self.WHITE, self.BLACK, self.standardFont)

		if not self.paused:
			self.showFooterElement(2, 'Space', 'pause', self.BLACK, self.WHITE, self.standardFont)
		else:
			self.showFooterElement(2, 'Space', 'pause', self.WHITE, self.BLACK, self.standardFont)

		self.showFooterElement(3, 'F10', 'redraw screen', self.BLACK, self.WHITE, self.standardFont)

		self.showFooterElement(4, 'Escape', 'quit', self.BLACK, self.WHITE, self.standardFont)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(r)


	def playMusic(self, previous = False):
		##### If only one song is available, it can easily be run in a loop by saying `play(-1)`

		if not self.allowMusic:
			self.updateTextNowPlaying()
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
				pygame.mixer.music.play()
			self.updateTextNowPlaying()
		else:
			if not previous and self.activeTheme is not None:
				self.debugPrint('No music available in theme {}'.format(self.activeTheme.name))


	def playGlobalEffect(self, effectID):
		if self.globalChannel.get_busy():
			self.debugPrint('Reserved channel is busy! Effect key: {}'.format(chr(effectID)))

		self.activeGlobalEffect = effectID
		self.globalChannel.play(self.globalEffects[effectID].obj)

		self.updateTextGlobalKeys()

		##### Must consider interrupting effects!
		##### I must also consider the effects on and of pausing


	def stopGlobalEffect(self):
		self.activeGlobalEffect = None
		self.globalChannel.stop()
		self.updateTextGlobalKeys()


	def playSound(self):
		if not self.allowSounds:
			self.updateTextNowPlaying()
			return

		if not self.paused and self.activeSounds and pygame.mixer.find_channel() is not None:
			rand = random.random()
			if rand < self.occurences[-1]:
				for i in range(len(self.occurences)): #### probably replace with bisect, if possible
					if self.occurences[i] > rand:
						newSound = self.activeSounds[i]
						self.debugPrint('Now playing sound {} with volume {}'.format(newSound.filename, newSound.volume))
						self.activeChannels.append((newSound.filename, newSound.obj.play()))
						break
		self.updateTextNowPlaying()


	def initializeGlobalEffects(self):
		self.globalEffects = self.box.getGlobalEffects()

		for e in self.globalEffects:
			self.globalEffects[e].obj = pygame.mixer.Sound(self.globalEffects[e].filename)
			self.globalEffects[e].obj.set_volume(self.globalEffects[e].volume)


	def activateNewTheme(self, themeID):
		self.activeTheme = self.box.getTheme(themeID)
		self.activeThemeID = themeID

		self.debugPrint('New theme is {}'.format(self.activeTheme.name))

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

		# remove clutter from the event queue
		pygame.event.set_allowed(None)
		pygame.event.set_allowed([pygame.QUIT, pygame.KEYDOWN, self.SONG_END])

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
		filename = 'test.xml'

	box = RPGbox(filename)

	#print(box)

	player = Player(box)
	player.start()

