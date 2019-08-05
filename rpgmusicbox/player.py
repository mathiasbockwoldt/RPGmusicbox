import os
from random import random
from bisect import bisect_right
from copy import deepcopy

import pygame


class Player(object):
	'''
	This class can read RPGbox objects and play music and sounds etc.
	'''

	# Default colors
	COLOR_TEXT = (0, 0, 0)			# Text color: black
	COLOR_BG = (255, 255, 255)		# Background color: white
	COLOR_EMPH = (200, 0, 0)		# Emphasizing color: red
	COLOR_FADE = (127, 127, 127)	# Fading color: grey

	def __init__(self, box, debug = False):
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
		self.displayFooterWidth = w // 6
		self.displayHeight = h
		self.displayPanelHeight = h - 2 * self.standardFont.size(' ')[1]
		self.displayFooterHeight = h - self.displayPanelHeight
		self.displayBorder = 5

		self.textGlobalKeys = pygame.Surface((self.displayPanelWidth, self.displayPanelHeight))
		self.textThemeKeys = pygame.Surface((self.displayPanelWidth, self.displayPanelHeight))
		self.textNowPlaying = pygame.Surface((self.displayWidth - 2*self.displayPanelWidth, self.displayPanelHeight))	# The displayWidth - 2*panelWidth fills the rounding error pixels on the right side
		self.textFooter = pygame.Surface((self.displayWidth, self.displayFooterHeight)) # The footer stretches horizontally to 100%. The displayFooterWidth is for the single elements in the footer.

		# Initialize variables
		self.globalIDs, self.themeIDs = self.box.getIDs()
		self.globalEffects = None
		self.initializeGlobalEffects()
		self.activeSounds = []
		self.activeGlobalEffect = None
		self.occurrences = []
		self.playlist = Playlist([])
		self.activeTheme = None
		self.activeThemeID = None

		self.cycle = 0
		self.allowMusic = True
		self.allowSounds = True
		self.allowCustomColors = True
		self.paused = False
		self.newSongWhilePause = False
		self.interruptingGlobalEffect = False
		self.activeChannels = []
		self.blockedSounds = {}	# {filename: timeToStartAgain, ...}

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


	def toggleDebugOutput(self):
		''' Allows or disallows debug output to stdout '''

		if self.debug:
			self.debug = False
		else:
			self.debug = True
			self.debugPrint('Debug printing activated')

		self.updateTextFooter()


	def togglePause(self):
		''' Pause or unpause music and sounds, depending on the self.paused and self.interruptingGlobalEffect variables. '''

		if self.paused:
			self.debugPrint('Player unpaused')
			self.paused = False
			if self.interruptingGlobalEffect:
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


	def toggleAllowCustomColors(self):
		''' Allow or disallow custom colors. '''

		if self.allowCustomColors:
			self.colorText = self.COLOR_TEXT
			self.colorBackground = self.COLOR_BG
			self.colorEmph = self.COLOR_EMPH
			self.colorFade = self.COLOR_FADE
			self.allowCustomColors = False
		else:
			if self.activeTheme is None:
				self.colorText = self.box.colorText
				self.colorBackground = self.box.colorBackground
				self.colorEmph = self.box.colorEmph
				self.colorFade = self.box.colorFade
			else:
				self.colorText = self.activeTheme.colorText
				self.colorBackground = self.activeTheme.colorBackground
				self.colorEmph = self.activeTheme.colorEmph
				self.colorFade = self.activeTheme.colorFade
			self.allowCustomColors = True

		self.updateTextAll()


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
				if self.activeChannels[i][1] is None or not self.activeChannels[i][1].get_busy():
					toDelete.append(i)

			for i in toDelete[::-1]:
				del(self.activeChannels[i])

			# all members may have been deleted, that's why here is a new `if`
			if self.activeChannels:
				self.showLine(area, '', self.colorText, self.standardFont)
				for name, c in sorted(self.activeChannels):
					self.showLine(area, name, self.colorEmph, self.standardFont)

		if self.blockedSounds:
			to_delete = []
			for k in list(self.blockedSounds.keys()):
				if self.blockedSounds[k] < 0:
					del self.blockedSounds[k]

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
			self.showFooterElement(0, 'F1', 'disallow music', self.colorBackground, self.colorText, self.standardFont)

		if self.allowSounds:
			self.showFooterElement(1, 'F2', 'allow sounds', self.colorText, self.colorBackground, self.standardFont)
		else:
			self.showFooterElement(1, 'F2', 'disallow sounds', self.colorBackground, self.colorText, self.standardFont)

		if not self.paused:
			self.showFooterElement(2, 'Space', 'unpaused', self.colorText, self.colorBackground, self.standardFont)
		else:
			self.showFooterElement(2, 'Space', 'paused', self.colorBackground, self.colorText, self.standardFont)

		if self.allowCustomColors:
			self.showFooterElement(3, 'F5', 'custom colors', self.colorText, self.colorBackground, self.standardFont)
		else:
			self.showFooterElement(3, 'F5', 'standard colors', self.colorBackground, self.colorText, self.standardFont)

		if not self.debug:
			self.showFooterElement(4, 'F10', 'no debug output', self.colorText, self.colorBackground, self.standardFont)
		else:
			self.showFooterElement(4, 'F10', 'debug output', self.colorBackground, self.colorText, self.standardFont)

		self.showFooterElement(5, 'Escape', 'quit', self.colorText, self.colorBackground, self.standardFont)

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
			pygame.mixer.music.set_volume(nextSong.volume)
			if self.paused:
				self.newSongWhilePause = True
			else:
				if len(self.playlist.songs) == 1:
					pygame.mixer.music.play(-1)
				else:
					pygame.mixer.music.play()
			self.updateTextNowPlaying()
		else:
			pygame.mixer.music.stop()
			if not previous and self.activeTheme is not None:
				self.debugPrint('No music available in theme {}'.format(self.activeTheme.name))


	def playGlobalEffect(self, effectID):
		'''
		Plays a global effect taking care of interrupting other music and sounds if necessary.

		:param effectID: The ID of the effect to be played.
		'''

		if self.globalChannel.get_busy():
			self.debugPrint('Reserved channel is busy! Active key is {}'.format(chr(self.activeGlobalEffect)))
			return

		if self.globalEffects[effectID].interrupting:
			self.interruptingGlobalEffect = True
			pygame.mixer.music.pause()
			for name, channel in self.activeChannels:
				channel.pause()

		self.activeGlobalEffect = effectID
		self.globalChannel.play(self.globalEffects[effectID].obj)

		self.debugPrint('Now playing {}'.format(self.globalEffects[effectID].name))

		self.updateTextGlobalEffects()
		self.updateTextNowPlaying()


	def stopGlobalEffect(self, byEndEvent = False):
		'''
		Stops a global effect, if it is still running.
		Takes care of restarting potentially interrupted music and sounds.

		:param byEndEvent: If True, this function is called, because the global effect stopped.
		'''

		if self.activeGlobalEffect is None:
			return

		self.activeGlobalEffect = None

		if not byEndEvent:
			self.globalChannel.stop()

		if not self.paused:
			pygame.mixer.music.unpause()
			pygame.mixer.unpause()

		self.debugPrint('Now stopping last global effect.')

		self.interruptingGlobalEffect = False
		self.updateTextGlobalEffects()


	def playSound(self):
		'''
		Plays a random sound and adds its channel to the activeChannels list.
		'''

		def findSound(a, x):
			'''
			Find leftmost value greater than x using bisect

			:param a: A sorted list with elements
			:param x: The element to look for
			:returns: The index of the leftmost element greater than x or None, if x is greater than the rightmost element
			'''

			i = bisect_right(a, x)
			if i != len(a):
				return i
			return None

		# If sounds are not allowed, update the now playing panel and do nothing more
		if not self.allowSounds:
			self.updateTextNowPlaying()
			return

		if not self.paused and not self.activeGlobalEffect and self.activeSounds and pygame.mixer.find_channel() is not None:
			rand = random()
			if rand < self.occurrences[-1]:
				i = findSound(self.occurrences, rand)
				if i is not None and self.activeSounds[i].filename not in self.blockedSounds:
					newSound = self.activeSounds[i]
					self.debugPrint('Now playing sound {} with volume {}'.format(newSound.filename, newSound.volume))
					self.activeChannels.append((newSound.name, newSound.obj.play()))
					self.blockedSounds[newSound.filename] = newSound.obj.get_length() + newSound.cooldown
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
		if self.allowCustomColors:
			self.colorText = self.activeTheme.colorText
			self.colorBackground = self.activeTheme.colorBackground
			self.colorEmph = self.activeTheme.colorEmph
			self.colorFade = self.activeTheme.colorFade

		loopedSounds = []

		# Get sounds and load them into pygame
		self.activeSounds = deepcopy(self.activeTheme.sounds)
		for i in range(len(self.activeSounds)):
			self.activeSounds[i].obj = pygame.mixer.Sound(self.activeSounds[i].filename)
			self.activeSounds[i].obj.set_volume(self.activeSounds[i].volume)
			if self.activeSounds[i].loop:
				loopedSounds.append(i)

		self.playlist = Playlist(self.activeTheme.songs)

		self.occurrences = self.activeTheme.occurrences

		# Push a SONG_END event on the event stack to trigger the start of a new song (causes a delay of one cycle, but that should be fine)
		pygame.event.post(pygame.event.Event(self.SONG_END))

		pygame.mixer.stop()	# Stop all playing sounds

		# Start all sounds that shall be looped
		for i in loopedSounds:
			newSound = self.activeSounds[i]
			self.activeChannels.append(('>> ' + newSound.name, newSound.obj.play(loops = -1)))
			self.blockedSounds[newSound.filename] = 604800 # one week

		self.updateTextAll()


	def deactivateTheme(self):
		'''
		Deactivates a theme. All sounds of that theme are discarded. The playlist is emptied. All running sounds and music are stopped.
		'''

		self.debugPrint('Theme {} was deactivated'.format(self.activeTheme.name))

		self.activeTheme = None
		self.activeThemeID = None

		# Update colors
		if self.allowCustomColors:
			self.colorText = self.box.colorText
			self.colorBackground = self.box.colorBackground
			self.colorEmph = self.box.colorEmph
			self.colorFade = self.box.colorFade

		for name, channel in self.activeChannels:
			channel.stop()

		self.activeSounds = []
		self.occurrences = []
		self.playlist = Playlist([])

		#pygame.mixer.stop()	# Stop all playing sounds
		pygame.mixer.music.stop() # Stop all music

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

					# Pre-processing: Map numpad keys to normal numbers
					if 256 <= event.key <= 265:
						event.key -= 208


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

					# The F5 key was pressed -> (dis)allow custom colors
					elif event.key == pygame.K_F5:
						self.toggleAllowCustomColors()

					# The F10 key was pressed -> do (not) print debug info to stdout
					elif event.key == pygame.K_F10:
						self.toggleDebugOutput()

					# The key is the key of the active theme -> deactivate theme (become silent)
					elif event.key == self.activeThemeID:
						self.deactivateTheme()

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
				if self.blockedSounds:
					for k in self.blockedSounds.keys():
						self.blockedSounds[k] -= 1
				self.playSound()
			self.cycle += 1
