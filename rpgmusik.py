#!/usr/bin/env python
#-*- coding:utf-8 -*-

# # # #  To do  # # # #
#
# Structural stuff
# - Shall themes, music, sounds have their own classes? I think so!
# - The theme id is currently not needed for anything (key has to be unique anyway). Should it be dropped?
# - I have to think about / test, if I should preload *all* sounds in the beginning or (as it is now) preload only the active theme sounds.
# - Use more precise inits for the different pygame classes instead of a general pygame.init()?
# - Ignore unnecessary inputs, like mouse input?
#
# Must haves
# - Global effects like Jeopardy music; with option to be interrupting (pausing all other music/sounds while playing) or non-interrupting (overlaying like a sound effect)
#   + These sounds must be stoppable, e.g. by pressing the same key again
# - Allow to select the previous song by pressing "<-"
# - Allow for "silence" instead of background music (also in addition to background music -> music - 2 min silence - music)
#
# Ideas
# - Config for individual fonts, colors etc? Could be something like: <config bgcolor="#000000" color="#ff2222" />
# - Colors, background image, etc. depending on theme (as attribute)?
# - Default starting theme (defined in the xml file)
# - The screen output could be improved
#
# Bugs
# - The playlist management must be improved. A new list must be generated earlier, such that there are always n new songs in the list. The playlist could be a class with a generator...
#

from __future__ import generators, division, with_statement, print_function

import pygame
import sys
#import os.path
import copy
import random
import xml.etree.ElementTree as ET
from glob import glob
from pygame.locals import *


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

		self.songs = songs
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
			self.nowPlaying = -1	# In case, previousSong() is called multiple times while in the beginning of the list, the pointer needs to be reset to -1, such that nextSong() starts at 0 again.
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
			return [None, None, self.playlist[0]]	# [None, None, next]

		# If the first song plays
		if self.nowPlaying == 0:
			return [None] + self.playlist[0:2]	# [None, current, next]

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

		self.songs = songs
		self.sounds = sounds
		self.occurences = occurences


	def addSong(self, song):
		self.songs.append(song)


	def addSound(self, sound):
		self.sounds.append(sound)


	def addOccurences(self, occurences):
		self.occurences.extend(occurences)

		if len(self.occurences) != len(self.songs):
			raise KeyError('The number of songs is not equal to the number of occurences in {}!'.format(self.name))


	# CLASS Theme END


class Song(object):
	'''
	Container for a song
	'''

	def __init__(self, ):


	# CLASS Song END


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
		self.version = None
		self.themes = {}		# Saves theme keys and connects them to theme object {themeKey: Theme(), ...}
		self.globalKeys = {}	# Saves global keys and connects them to global effect ids {globalKey: globalEffectID, ...}
		self.globalEffects = {}	# Saves global effects in the manner {globalEffectID: {'name': effectName, 'key': effectKey, 'volume': effectVolume, 'file': effectFile, 'interrupting': bool}, ...}

		# Read in the file, parse it and point to root
		root = ET.parse(filename).getroot()

		# Basic tag checking
		if root.tag != 'rpgbox':
			raise NoValidRPGboxError('No valid RPGbox file!')

		# Determine the version of the RPGbox file (NOT the XML version!)
		try:
			self.version = root.attrib['version']
		except KeyError:
			raise NoValidRPGboxError('Version attribute not given in <rpgbox> tag.')

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
				# Get id of the global effect (each global effect must have a unique id!)
				try:
					effectID = effect.attrib['id']
				except KeyError:
					raise NoValidRPGboxError('A global effect without id was found. Each global effect must have a unique id!')
				if effectID in self.globalKeys:	# No need to check for themes, as globals are processed earlier
					raise NoValidRPGboxError('The id {} is already in use.'.format(themeID))

				# Get the keyboard key of the effect (each global effect must have a unique key!)
				try:
					effectKey = effect.attrib['key'][0].lower() # get only first char and make it lowercase.
				except KeyError:
					raise NoValidRPGboxError('A global effect without key was found. Each global effect must have a unique keyboard key!')
				if ord(effectKey) in self.globalKeys:
					raise NoValidRPGboxError('The key {} is already in use.'.format(effectKey))
				self._ensureValidKey(effectKey)	# Ensure that the key is valid

				# Get the effect file from the attribute of the tag.
				try:
					globalsFile = effect.attrib['file']
					if os.path.isfile(globalsFile):
						globalsFile = None
				except KeyError:
					raise NoValidRPGboxError('No file given in global effect.')
				if globalsFile is None:
					raise NoValidRPGboxError('File {} not found in global.'.format(effect.attrib['file']))

				# Get potential volume of the effect. Alter it by the globals volume
				try:
					effectVolume = int(effect.attrib['volume'])
				except KeyError:
					effectVolume = self.DEFAULT_VOLUME
				effectVolume = self._ensureVolume(int(effectVolume * globalsVolume / 100))

				# Get the effect name. If not available, use id as name
				try:
					effectName = effect.attrib['name']
				except KeyError:
					effectName = effectID

				# Check, whether the effect should interrupt everything else
				interrupting = ('interrupting' in effect.attrib)

				# Save the global effect with its name, volume, and key.
				self.globalKeys[effectKey] = effectID
				self.globalEffects[effectID] = {'name': effectName, 'key': effectKey, 'volume': effectVolume, 'file': effectFile, 'interrupting': interrupting}

		# Scan through themes
		for theme in root.iter('theme'):

			# Get the keyboard key of the theme (each theme must have a unique key!)
			try:
				themeKey = theme.attrib['key'][0].lower() # get only first char and make it lowercase.
				themeID = ord(themeKey)
			except KeyError:
				raise NoValidRPGboxError('A theme without key was found. Each theme must have a unique keyboard key!')

			if themeID in self.themes or themeID in self.globalKeys:
				raise NoValidRPGboxError('The key {} is already in use. Found in {}'.format(themeKey, themeID))
			self._ensureValidKey(themeKey)	# Ensure that the key is valid

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
						self.themes[themeID].addSong({'file': songFile, 'volume': volume})

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
						self.themes[themeID].addSound({'file': soundFile, 'volume': volume, 'occurence': occurence})
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

		##### This could be elegantly solved by calling the __str__ methods of each theme object (that can call the __str__ methods of each song/sound object.

		ret = []
		for t in sorted(self.themes.keys()):
			ret.append(self.themes[t].key + ': ' + self.themes[t].name)
			ret.append('Songs:')
			for s in self.themes[t].songs:
				ret.append('    vol: ' + str(m['volume']) + ', file: ' + m['file'])
			ret.append('Sounds:')
			for s in self.themes[t].sounds:
				ret.append('    vol: ' + str(s['volume']) + ', occ: ' + str(s['occurence']) +  ', file: ' + s['file'])

		###### global effects missing

		return '\n'.join(ret)


	def _ensureValidKey(self, k):
		'''
		Ensures, that a given keyboard key is valid for the RPGbox.

		:raises: NoValidRPGboxError
		'''

		num = ord(k)

		if not (48 <= num <= 57 or 97 <= num <= 122):
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


	def getDefaultThemeKey(self):
		''' Returns the default theme, if it is set, None otherwise '''

		############## No possibility for default theme, yet!
		return None


	def getIDs(self):
		''' Returns a tuple with two dicts: the global IDs and the theme IDs '''

		return self.globalKeys, list(self.themes.keys())


	def getGlobalKeysAndNames(self):
		''' Returns a list of tuples with global keys and their names. '''

		return [('1', 'Jeopardy Theme')] ################# Not yet implemented


	def getThemeKeysAndNames(self):
		''' Returns a list of tuples with theme keys and their names. '''

		ret = []

		for k in sorted(self.themes, key=lambda x: self.themes[x]['key']):
			ret.append((self.themes[k]['key'], self.themes[k]['name']))

		return ret


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

	def __init__(self, box, debug = True):
		'''
		Initiates all necessary stuff for playing an RPGbox.
		'''

		self.debug = debug

		self.box = box

		# Initialize pygame, screen and clock
		pygame.init()	### Could be split into more precise inits to avoid initiating unnecessary parts. But probably ok like this.
		self.clock = pygame.time.Clock()
		self.screen = pygame.display.set_mode((600, 400))	# Screen is 600*400 px large
		pygame.display.set_caption('RPGbox player')		# Set window title

		# Fill background
		self.background = pygame.Surface(self.screen.get_size()).convert()	# Define a background surface
		self.background.fill((255, 255, 255))							# Fill the background with white

		self.screen.blit(self.background, (0, 0))
		pygame.display.flip()

		# Create my own event to indicate that a song stopped playing to trigger a new song
		self.SONG_END = pygame.USEREVENT + 1
		pygame.mixer.music.set_endevent(self.SONG_END)

		# Reserve a channel for global sounds, such that a global sound can always be played
		pygame.mixer.set_reserved(1)
		self.globalChannel = pygame.mixer.Channel(0)
		self.initializeGlobalEffects()

		# Initiate text stuff
		w, h = self.background.get_size()
		self.w = w // 3

		self.myFont = pygame.font.Font(None, 24)

		self.textGlobalKeys = pygame.Surface((self.w, h))
		self.textThemeKeys = pygame.Surface((self.w, h))
		self.textNowPlaying = pygame.Surface((self.w, h))

		# Initialize variables
		self.globalIDs, self.themeIDs = self.box.getIDs()
		self.activeSounds = []
		self.playlist = None
		self.activeTheme = {'name': 'NONE', 'key': 0, 'musics': [], 'sounds': [], 'occurences': []}
		self.activeThemeKey = self.box.getDefaultThemeKey()
		if self.activeThemeKey:
			self.activateNewTheme(self.activeThemeKey)

		self.cycle = 0
		self.paused = False
		self.newSongWhilePause = False
		self.activeChannels = []

		# Start visualisation
		self.updateTextAll()


	def _togglePause(self):
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


	def debugPrint(self, t):
		''' Prints the given text, if debugging is active. '''

		if self.debug:
			print(t)


	def updateTextAll(self):
		self.updateTextGlobalKeys()
		self.updateTextThemeKeys()
		self.updateTextNowPlaying()

		pygame.display.flip()


	def updateTextGlobalKeys(self, update = False):
		text = ['GlobalKeys', '']
		for k, t in self.box.getGlobalKeysAndNames():
			text.append(''.join((k, ' - ', t)))

		area = self.textGlobalKeys.get_rect()
		area.left = 5
		area.top = 5

		self.textGlobalKeys.fill((255, 255, 255))
		self.background.blit(self.textGlobalKeys, (0, 0))

		for t in text:
			textRect = self.myFont.render(t, True, (0, 0, 0))
			self.background.blit(textRect, area)
			area.top += self.myFont.get_linesize()

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update() ####### How does it only update the important region?


	def updateTextThemeKeys(self, update = False):
		text = ['Available themes', '']
		for k, t in self.box.getThemeKeysAndNames():
			text.append(''.join((k, ' - ', t)))

		area = self.textThemeKeys.get_rect()
		area.left = self.w + 5
		area.top = 5

		self.textThemeKeys.fill((255, 255, 255))
		self.background.blit(self.textThemeKeys, (self.w, 0))

		for t in text:
			textRect = self.myFont.render(t, True, (0, 0, 0))
			self.background.blit(textRect, area)
			area.top += self.myFont.get_linesize()

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update() ####### How does it only update the important region?


	def updateTextNowPlaying(self, update = False):
		text = ['Now Playing', '']

		if self.playlist is not None:
			songs = self.playlist.getSongsForViewing()
			for song in songs:
				if song is not None:
					text.append(song['file'])
			text.append('')

		if self.activeChannels:
			toDelete = []
			toList = []
			for i in range(len(self.activeChannels)):
				if self.activeChannels[i][1].get_busy():
					toList.append(self.activeChannels[i][0])
				else:
					toDelete.append(i)

			for i in toDelete[::-1]:
				del(self.activeChannels[i])

			if toList:
				text.append('')
				text.extend(sorted(toList))

		area = self.textNowPlaying.get_rect()
		area.left = 2 * self.w + 5
		area.top = 5

		self.textNowPlaying.fill((255, 255, 255))
		self.background.blit(self.textNowPlaying, (2 * self.w, 0))

		for t in text:
			textRect = self.myFont.render(t, True, (0, 0, 0))
			self.background.blit(textRect, area)
			area.top += self.myFont.get_linesize()

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update() ####### How does it only update the important region?


	def playMusic(self):
		##### If only one music is available, it can easily be run in a loop by saying `play(-1)`
		nextSong = self.playlist.nextSong()

		if nextSong is not None:
			self.debugPrint('Now playing {} with volume {}'.format(nextSong['file'], nextSong['volume']))
			pygame.mixer.music.load(nextSong['file'])
			pygame.mixer.music.set_volume(nextSong['volume'] / 100.0)
			if self.paused:
				self.newSongWhilePause = True
			else:
				pygame.mixer.music.play()
			self.updateTextNowPlaying(update=True)
		else:
			self.debugPrint('No music available in theme {}'.format(self.activeTheme['name']))


	def playGlobalEffect(self, effect):
		pass ############################


	def playSound(self):
		if not self.paused and self.activeSounds and pygame.mixer.find_channel() is not None:
			rand = random.random()
			if rand < self.occurences[-1]:
				for i in range(len(self.occurences)): #### probably replace with bisect
					if self.occurences[i] > rand:
						newSound = self.activeSounds[i]
						self.debugPrint('Now playing sound {} with volume {}'.format(newSound['file'], newSound['volume']))
						self.activeChannels.append((newSound['file'], newSound['obj'].play()))
						break
		self.updateTextNowPlaying(update=True)


	def initializeGlobalEffects(self):
		self.globalEffects = self.box.getGlobalEffects()

		# {'name': effectName, 'key': effectKey, 'volume': effectVolume, 'file': effectFile, 'interrupting': bool}

		for e in self.globalEffects:
			self.globalEffects[e]['obj'] = pygame.mixer.Sound(self.globalEffects[e]['file'])
			self.globalEffects[e]['obj'].set_volume(self.globalEffects[e]['volume'])


	def activateNewTheme(self, themeKey):
		self.activeTheme = self.box.getTheme(themeKey)
		self.activeThemeKey = themeKey

		self.debugPrint('New theme is {}'.format(self.activeTheme['name']))

		# Get sounds and load them into pygame
		self.activeSounds = copy.deepcopy(self.activeTheme['sounds'])
		for i in range(len(self.activeSounds)):
			self.activeSounds[i]['obj'] = pygame.mixer.Sound(self.activeSounds[i]['file'])
			self.activeSounds[i]['obj'].set_volume(self.activeSounds[i]['volume'])

		self.playlist = Playlist(self.activeTheme['musics'])

		self.occurences = self.activeTheme['occurences']

		# Push a SONG_END event on the event stack to trigger the start of a new song/music (causes a delay of one cycle, but that should be fine)
		pygame.event.post(pygame.event.Event(self.SONG_END))

		pygame.mixer.stop()	# Stop all playing sounds

		self.updateTextAll()


	def start(self):

		# Start main loop
		while True:
			# Max 10 fps (More would be overkill, I think)
			self.clock.tick(10)

			# Let's see, what's in the event queue :)
			for event in pygame.event.get():

				# The program was quit (e.g. by clicking the X-button in the window title) -> quit and return
				if event.type == QUIT:
					pygame.quit()
					return

				# At least one key was pressed
				if event.type == KEYDOWN:

					# The Escape key was pressed -> quit and return
					if event.key == K_ESCAPE:
						pygame.quit()
						return

					# The space key was pressed -> (un)pause everything
					elif event.key == K_SPACE:
						self._togglePause()

					# The "->" key was pressed -> next song (stopping the current song triggers starting the next song)
					elif event.key == K_RIGHT:
						pygame.event.post(pygame.event.Event(self.SONG_END))

					# The key is the key of the active theme -> do nothing
					elif event.key == self.activeThemeKey:
						pass

					# The key is one of the theme keys -> activate the theme
					elif event.key in self.themeIDs:
						self.activateNewTheme(event.key)

					# The key is one of the global keys -> trigger effect
					elif event.key in self.globalIDs:
						self.playGlobalEffect(event.key)

					# The key is the space key -> pause or unpause the player
					elif event.key == K_SPACE:
						self._togglePause()

				# The last song/music is finished (or a new theme was loaded) -> start new music, if available
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

