from collections import namedtuple

from pygame import Color

from .containers import GlobalEffect, Song, Sound, Theme


Colormap = namedtuple('Colormap', ['text', 'bg', 'emph', 'fade'])


class RPGmusicbox(object):
	'''
	Contains music and sound information for a game evening.
	Reads infos from an XML file.
	'''

	# Default values
	DEFAULT_BASETIME = 3600		# Default basetime is 3600 seconds (1 hour)
	MIN_BASETIME = 1			# Minimum basetime is 1 second
	MAX_BASETIME = 36000		# Maximum basetime is 36 000 seconds (10 hours)
	DEFAULT_OCCURRENCE = 0.01	# Default occurrence is 0.01 (1% of basetime)
	MIN_OCCURRENCE = 0			# Minimum occurrence is 0 (never)
	MAX_OCCURRENCE = 1			# Maximum occurrence is 1 (always)
	DEFAULT_VOLUME = 100		# Default volume is 100% (100)
	MIN_VOLUME = 0				# Minimum volume is 0%
	MAX_VOLUME = 1				# Maximum volume is 100% (1.0)
	DEFAULT_COOLDOWN = 10		# Default cooldown is 10 seconds
	# MIN and MAX cooldown are not defined, as they are not needed

	# Default colors
	COLOR_TEXT = '#000000'			# Text color: black
	COLOR_BG = '#ffffff'			# Background color: white
	COLOR_EMPH = '#c80000'			# Emphasizing color: red
	COLOR_FADE = '#7f7f7f'			# Fading color: grey


	def __init__(self):
		'''
		Creates an empty RPG music box.
		'''

		self.name_to_color = {
			'text': self.COLOR_TEXT,
			'bg': self.COLOR_BG,
			'emph': self.COLOR_EMPH,
			'fade': self.COLOR_FADE,
		}


		# Default colors
		self.colors = self.update_colors({}, default=True)

		# Saves theme keys and connects them to theme object {themeID: Theme(), ...}
		self.themes = {}

		# Saves theme keys and connects them to global effect object {globalEffectID: GlobalEffect(), ...}
		self.global_effects = {}


	def __str__(self):
		'''
		:returns: String representation of all themes and global effects of this box.
		'''

		ret = ['RPGmusicbox', 'Themes']
		for t in sorted(self.themes.keys()):
			ret.append(str(self.themes[t]))

		ret.append('Global effects')

		for e in sorted(self.globalEffects.keys()):
			ret.append(str(self.globalEffects[e]))

		return '\n'.join(ret)


	def update_colors(self, colors, default=False):
		'''
		Sets a color in the config.
		'''

		colors = {}

		for c in self.name_to_color:
			if c in colors:
				colors[c] = Color(colors[c])
			else:
				colors[c] = Color(self.name_to_color[c])

		if default:
			self.colors = Colormap(colors)
		else:
			return Colormap(colors)


	def add_global_effect(self, kid, filename, key, name, volume, interrupting):
		'''
		Adds a global effect.
		'''

		self._ensureValidID(kid)
		volume = self._ensureVolume(volume)

		self.global_effects[kid] = GlobalEffect(filename = filename, key = key, name = name, volume = volume, interrupting = interrupting)


	def add_theme(self, kid, name, colors):
		'''
		Adds a theme.
		'''

		colors = self.update_colors(colors, default=False)

		self.themes[kid] = Theme(key = kid, name = name, colors = colors)


	def add_song(self, kid, path, name, volume):
		'''
		Adds a background song to a theme.
		'''

		volume = self._ensureVolume(volume)

		self.themes[kid].addSong(Song(path, name, volume))


	def add_sound(self, kid, path, name, volume, cooldown, loop):
		'''
		Adds a sound effect to a theme.
		'''

		volume = self._ensureVolume(volume)

		self.themes[kid].addSound(Sound(path, name=name, volume=volume, cooldown=cooldown, loop=loop))


	def add_occurrences(self, kid, occurrences):
		'''
		Adds a sound effect to a theme.
		'''

		self.themes[kid].occurrences = occurrences


	def _ensureValidID(self, kid):
		'''
		Ensures, that a given keyboard key (or rather its ID) is valid for the RPGbox.

		:param kid: The key ID to check (not the key, but its ID!)
		:raises: ValueError
		'''

		# Allowed: 0-9, a-z
		if not (48 <= kid <= 57 or 97 <= kid <= 122):
			raise ValueError('The key {} is not in the allowed range (a-z lowercase and 0-9 only!)'.format(chr(kid)))

		if kid in self.global_effects or kid in self.themes:
			raise ValueError('The key {} is already registered!'.format(chr(kid)))


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


	def ensureBasetime(self, b):
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


	def _ensureOccurrence(self, o):
		'''
		Ensures that a given occurrence is within the allowed range.

		:param o: The occurrence to check
		:returns: The occurrence, that is guaranteed to be within the allowed range
		'''

		if o < self.MIN_OCCURRENCE:
			return self.MIN_OCCURRENCE
		elif o > self.MAX_OCCURRENCE:
			return self.MAX_OCCURRENCE

		return o


	def getIDs(self):
		'''
		:returns: a list of two lists: the keys of all global IDs and the keys of all theme IDs
		'''

		return list(self.globalEffects.keys()), list(self.themes.keys())


	def getGlobalEffects(self):
		'''
		:returns: all global effects (a dict in the form {globalEffectID: GlobalEffectObject, ...})
		'''

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
			raise KeyError('The key {} is not registered.'.format(themeID))
