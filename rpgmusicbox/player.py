import os
from collections import namedtuple
from random import random
from bisect import bisect_right
from copy import deepcopy

import pygame

import display

Field = namedtuple('Field', ['text', 'active'])


class Player():
	'''
	This class can read RPGbox objects and play music and sounds etc.
	'''

	def __init__(self, box, debug = False):
		'''
		Initiates all necessary stuff for playing an RPGbox.

		:param box: The RPGbox object to read from
		:param debug: Boolean that states, whether debugging texts should be sent to STDOUT
		'''

		self.box = box
		self.debug = debug

		# Initialize pygame, clock, and screen
		pygame.init()
		self.clock = pygame.time.Clock()
		self.display = Display(self.box.colors)
		self.display.screen_size_changed(800, 600)  # Default screen size is 800x600

		# Create my own event to indicate that a song stopped playing to trigger a new song
		self.SONG_END = pygame.USEREVENT + 1
		pygame.mixer.music.set_endevent(self.SONG_END)

		# Reserve a channel for global sound effects, such that a global sound can always be played
		self.GLOBAL_END = pygame.USEREVENT + 2
		pygame.mixer.set_reserved(1)
		self.global_channel = pygame.mixer.Channel(0)
		self.global_channel.set_endevent(self.GLOBAL_END)

		# Initialize variables
		self.global_IDs, self.theme_IDs = self.box.get_IDs()
		self.global_effects = None
		self.active_sounds = []
		self.active_global_effect = None
		self.occurrences = []
		self.playlist = Playlist([])
		self.active_theme = None
		self.active_theme_ID = None

		self.cycle = 0
		self.allow_music = True
		self.allow_sounds = True
		self.allow_custom_colors = True
		self.paused = False
		self.new_song_while_pause = False
		self.interrupting_global_effect = False
		self.active_channels = []
		self.blocked_Sounds = {}	# {filename: time_to_start_again, ...}

		self.initialize_global_effects()

		# Start visualisation
		self.update_text_all()


	def debug_print(self, t):
		'''
		Prints the given text, if debugging (self.debug) is active.

		:param t: The text to print.
		'''

		if self.debug:
			print(t)


	def initialize_global_effects(self):
		'''
		Loads the file for each global effect to RAM and adjust its volume to have it ready.
		'''

		self.global_effects = self.box.get_global_effects()

		for e in self.global_effects:
			self.global_effects[e].obj = pygame.mixer.Sound(self.global_effects[e].filename)
			self.global_effects[e].obj.set_volume(self.global_effects[e].volume)


	def toggle_debug_output(self):
		''' Allows or disallows debug output to stdout '''

		if self.debug:
			self.debug = False
		else:
			self.debug = True
			self.debug_print('Debug printing activated')

		self.update_text_footer()


	def toggle_pause(self):
		''' Pause or unpause music and sounds, depending on the self.paused and self.interrupting_global_effect variables. '''

		if self.paused:
			self.debug_print('Player unpaused')
			self.paused = False
			if self.interrupting_global_effect:
				self.global_channel.unpause()
			else:
				pygame.mixer.music.unpause()
				pygame.mixer.unpause()
				if self.new_song_while_pause:
					self.new_song_while_pause = False
					pygame.mixer.music.play()
		else:
			pygame.mixer.music.pause()
			pygame.mixer.pause()
			self.debug_print('Player paused')
			self.paused = True
		self.update_text_footer()


	def toggle_allow_music(self):
		''' Allow or disallow music to be played. '''

		if self.allow_music:
			self.allow_music = False
			pygame.mixer.music.stop()
			self.playlist.now_playing -= 1	# Necessary to start with the same song, when music is allowed again
			self.update_text_now_playing()
			self.debug_print('Music switched off')
		else:
			self.allow_music = True
			pygame.event.post(pygame.event.Event(self.SONG_END))
			self.debug_print('Music switched on')
		self.update_text_footer()


	def toggle_allow_sounds(self):
		''' Allow or disallow sounds to be played. '''

		if self.allow_sounds:
			self.allow_sounds = False
			if self.active_channels:
				for c in self.active_channels:
					c[1].stop()
			self.update_text_now_playing()
			self.debug_print('Sound switched off')
		else:
			self.allow_sounds = True
			self.debug_print('Sound switched on')
		self.update_text_footer()


	def toggle_allow_custom_colors(self):
		''' Allow or disallow custom colors. '''

		self.allow_custom_colors = not self.allow_custom_colors

		if self.allow_custom_colors:
			if self.active_theme is None:
				self.display.colors = self.box.colors
			else:
				self.display.colors = self.active_theme.colors
		else:
			self.display.colors = self.box.default_colors

		self.update_text_all()


	def update_text_all(self):
		''' Update the whole screen. '''
		self.background.fill(self.colors.bg)
		self.update_text_global_effects(update = False)
		self.update_text_themes(update = False)
		self.update_text_now_playing(update = False)
		self.update_text_footer(update = False)

		pygame.display.flip()


	def update_text_global_effects(self, update = True):
		'''
		Update the global effects panel

		:param update: Boolean to state, whether the display should be updated
		'''

		to_draw = []

		for k in sorted(self.global_effects.keys()):
			t = ''.join((chr(k), ' - ', self.global_effects[k].name))
			to_draw.append(Field(t, k == self.active_global_effect))

		self.display.draw_global_effects(to_draw, update)


	def update_text_themes(self, update = True):
		'''
		Update the themes panel

		:param update: Boolean to state, whether the display should be updated
		'''

		to_draw = []

		for k in sorted(self.box.themes.keys()):
			t = ''.join((chr(k), ' - ', self.box.themes[k].name))
			to_draw.append(Field(t, k == self.active_theme_ID))

		self.display.draw_themes(to_draw, update)


	def update_text_now_playing(self, update = True):
		'''
		Update the now playing panel

		:param update: Boolean to state, whether the display should be updated
		'''

		to_draw = []

		songs = self.playlist.get_songs_for_viewing()

		# In this case, active is:
		# 0 for standard text
		# 1 for emphasized text
		# 2 for fading text

		if songs is not None:
			if len(songs) == 1:
				to_draw.append(Field('>> {}'.format(songs[0].name), 1))
			elif len(songs) == 2:
				if songs[0]:
					to_draw.append(Field(songs[0].name, 1))
				else:
					to_draw.append(Field('', 0))
				to_draw.append(Field(songs[1].name, 0))
			else:
				to_draw.append(Field(songs[0].name, 2))
				to_draw.append(Field(songs[1].name, 1))
				to_draw.append(Field(songs[2].name, 0))

		if self.active_channels:
			to_delete = []
			for i, channel in enumerate(self.active_channels):
				if channel is None or not channel.get_busy():
					to_delete.append(i)

			for i in to_delete[::-1]:
				del(self.active_channels[i])

			# all members may have been deleted, that's why here is a new `if`
			if self.active_channels:
				to_draw.append(Field('', 0))
				for name, c in sorted(self.active_channels):
					to_draw.append(Field(name, 1))

		if self.blocked_Sounds:
			to_delete = []
			for k in self.blocked_Sounds.keys():
				if self.blocked_Sounds[k] < 0:
					del self.blocked_Sounds[k]

		self.display.draw_playing(to_draw, update)


	def update_text_footer(self, update = True):
		'''
		Update the footer

		:param update: Boolean to state, whether the display should be updated
		'''

		to_draw = []

		if self.allow_music:
			to_draw.append(Field(('F1', 'allow music'), True))
		else:
			to_draw.append(Field(('F1', 'disallow music'), False))

		if self.allow_sounds:
			to_draw.append(Field(('F2', 'allow sounds'), True))
		else:
			to_draw.append(Field(('F2', 'disallow sounds'), False))

		if not self.paused:
			to_draw.append(Field(('Space', 'unpaused'), True))
		else:
			to_draw.append(Field(('Space', 'paused'), False))

		if self.allow_custom_colors:
			to_draw.append(Field(('F5', 'custom colors'), True))
		else:
			to_draw.append(Field(('F5', 'standard colors'), False))

		if not self.debug:
			to_draw.append(Field(('F10', 'no debug output'), True))
		else:
			to_draw.append(Field(('F10', 'debug output'), False))

		to_draw.append(Field(('Escape', 'quit'), True))

		self.display.draw_footer(to_draw, update)


	def play_music(self, previous = False):
		'''
		Plays the next or previous song. Any playing song will be replaced by the new song.

		:param previous: If True, play previous song, if False, play next song.
		'''

		# If no music is allowed, don't do anything
		if not self.allow_music:
			return

		if previous:
			next_song = self.playlist.previous_song()
		else:
			next_song = self.playlist.next_song()

		if next_song is not None:
			self.debug_print('Now playing {} with volume {}'.format(next_song.filename, next_song.volume))
			pygame.mixer.music.load(next_song.filename)
			pygame.mixer.music.set_volume(next_song.volume)
			if self.paused:
				self.new_song_while_pause = True
			else:
				if len(self.playlist.songs) == 1:
					pygame.mixer.music.play(-1)
				else:
					pygame.mixer.music.play()
			self.update_text_now_playing()
		else:
			pygame.mixer.music.stop()
			if not previous and self.active_theme is not None:
				self.debug_print('No music available in theme {}'.format(self.active_theme.name))


	def play_global_effect(self, effect_ID):
		'''
		Plays a global effect taking care of interrupting other music and sounds if necessary.

		:param effect_ID: The ID of the effect to be played.
		'''

		if self.global_channel.get_busy():
			self.debug_print('Reserved channel is busy! Active key is {}'.format(chr(self.active_global_effect)))
			return

		if self.global_effects[effect_ID].interrupting:
			self.interrupting_global_effect = True
			pygame.mixer.music.pause()
			for name, channel in self.active_channels:
				channel.pause()

		self.active_global_effect = effect_ID
		self.global_channel.play(self.global_effects[effect_ID].obj)

		self.debug_print('Now playing {}'.format(self.global_effects[effect_ID].name))

		self.update_text_global_effects()
		self.update_text_now_playing()


	def stop_global_effect(self, by_end_event = False):
		'''
		Stops a global effect, if it is still running.
		Takes care of restarting potentially interrupted music and sounds.

		:param by_end_event: If True, this function is called, because the global effect stopped.
		'''

		if self.active_global_effect is None:
			return

		self.active_global_effect = None

		if not by_end_event:
			self.global_channel.stop()

		if not self.paused:
			pygame.mixer.music.unpause()
			pygame.mixer.unpause()

		self.debug_print('Now stopping last global effect.')

		self.interrupting_global_effect = False
		self.update_text_global_effects()


	def play_sound(self):
		'''
		Plays a random sound and adds its channel to the active_channels list.
		'''

		def find_sound(a, x):
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
		if not self.allow_sounds:
			self.update_text_now_playing()
			return

		if not self.paused and not self.active_global_effect and self.active_sounds and pygame.mixer.find_channel() is not None:
			rand = random()
			if rand < self.occurrences[-1]:
				i = find_sound(self.occurrences, rand)
				if i is not None and self.active_sounds[i].filename not in self.blocked_Sounds:
					new_sound = self.active_sounds[i]
					self.debug_print('Now playing sound {} with volume {}'.format(new_sound.filename, new_sound.volume))
					self.active_channels.append((new_sound.name, new_sound.obj.play()))
					self.blocked_Sounds[new_sound.filename] = new_sound.obj.get_length() + new_sound.cooldown
		self.update_text_now_playing()


	def activate_new_theme(self, theme_ID):
		'''
		Activates a new theme. All sounds of that theme are loaded and their volumes adjusted. A new playlist is initiated with all songs. All running sounds are stopped and new music is played.

		:param theme_ID: The ID of the theme to activate
		'''

		self.active_theme = self.box.get_theme(theme_ID)
		self.active_theme_ID = theme_ID

		self.debug_print('New theme is {}'.format(self.active_theme.name))

		# Update colors
		if self.allow_custom_colors:
			self.display.colors = self.active_theme.colors

		looped_Sounds = []

		# Get sounds and load them into pygame
		self.active_sounds = deepcopy(self.active_theme.sounds)
		for i in range(len(self.active_sounds)):
			self.active_sounds[i].obj = pygame.mixer.Sound(self.active_sounds[i].filename)
			self.active_sounds[i].obj.set_volume(self.active_sounds[i].volume)
			if self.active_sounds[i].loop:
				looped_Sounds.append(i)

		self.playlist = Playlist(self.active_theme.songs)

		self.occurrences = self.active_theme.occurrences

		# Push a SONG_END event on the event stack to trigger the start of a new song (causes a delay of one cycle, but that should be fine)
		pygame.event.post(pygame.event.Event(self.SONG_END))

		pygame.mixer.stop()	# Stop all playing sounds

		# Start all sounds that shall be looped
		for i in looped_Sounds:
			new_sound = self.active_sounds[i]
			self.active_channels.append(('>> ' + new_sound.name, new_sound.obj.play(loops = -1)))
			self.blocked_Sounds[new_sound.filename] = 604800 # one week

		self.update_text_all()


	def deactivate_theme(self):
		'''
		Deactivates a theme. All sounds of that theme are discarded. The playlist is emptied. All running sounds and music are stopped.
		'''

		self.debug_print('Theme {} was deactivated'.format(self.active_theme.name))

		self.active_theme = None
		self.active_theme_ID = None

		# Update colors
		if self.allow_custom_colors:
			self.display.colors = self.box.colors

		for name, channel in self.active_channels:
			channel.stop()

		self.active_sounds = []
		self.occurrences = []
		self.playlist = Playlist([])

		#pygame.mixer.stop()	# Stop all playing sounds
		pygame.mixer.music.stop() # Stop all music

		self.update_text_all()


	def start(self):
		'''
		Starts the main loop, that takes care of events (e.g. key strokes) and triggers random sounds.
		'''

		# remove clutter from the event queue
		pygame.event.set_blocked()
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

				# The window size was changed
				if event.type == pygame.VIDEORESIZE:
					self.display.screen_size_changed(event.w, event.h)

				# At least one key was pressed
				elif event.type == pygame.KEYDOWN:

					# Pre-processing: Map numpad keys to normal numbers
					if 256 <= event.key <= 265:
						event.key -= 208


					# The Escape key was pressed -> quit and return
					if event.key == pygame.K_ESCAPE:
						pygame.quit()
						return

					# The space key was pressed -> (un)pause everything
					elif event.key == pygame.K_SPACE:
						self.toggle_pause()

					# The "->" key was pressed -> next song
					elif event.key == pygame.K_RIGHT:
						self.play_music()

					# The "<-" key was pressed -> previous song
					elif event.key == pygame.K_LEFT:
						self.play_music(previous = True)

					# The F1 key was pressed -> (dis)allow Music
					elif event.key == pygame.K_F1:
						self.toggle_allow_music()

					# The F2 key was pressed -> (dis)allow Sounds
					elif event.key == pygame.K_F2:
						self.toggle_allow_sounds()

					# The F5 key was pressed -> (dis)allow custom colors
					elif event.key == pygame.K_F5:
						self.toggle_allow_custom_colors()

					# The F10 key was pressed -> do (not) print debug info to stdout
					elif event.key == pygame.K_F10:
						self.toggle_debug_output()

					# The key is the key of the active theme -> deactivate theme (become silent)
					elif event.key == self.active_theme_ID:
						self.deactivate_theme()

					# The key is the key of the active global effect -> stop it
					elif event.key == self.active_global_effect:
						self.stop_global_effect()

					# The key is one of the theme keys -> activate the theme
					elif event.key in self.theme_IDs:
						self.activate_new_theme(event.key)

					# The key is one of the global keys -> trigger effect
					elif event.key in self.global_IDs:
						self.play_global_effect(event.key)

				# The last song is finished (or a new theme was loaded) -> start new song, if available
				elif event.type == self.SONG_END:
					self.play_music()

				# A global effect is finished
				elif event.type == self.GLOBAL_END:
					self.stop_global_effect(by_end_event = True)

			# Sound effects can be triggered every tenth cycle (about every second).
			if self.cycle > 10:
				self.cycle = 0
				if self.blocked_Sounds:
					for k in self.blocked_Sounds.keys():
						self.blocked_Sounds[k] -= 1
				self.play_sound()
			self.cycle += 1
