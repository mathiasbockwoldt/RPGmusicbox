from collections import namedtuple

from pygame import Color

from .containers import GlobalEffect, Song, Sound, Theme


Colormap = namedtuple('Colormap', ['text', 'bg', 'emph', 'fade'])


class RPGmusicbox():
	'''
	Contains music and sound information for a game evening.
	Reads infos from an XML file.
	'''

	# Default values
	DEFAULT_BASETIME = 3600    # Default basetime is 3600 seconds (1 hour)
	MIN_BASETIME = 1           # Minimum basetime is 1 second
	MAX_BASETIME = 36000       # Maximum basetime is 36 000 seconds (10 hours)
	DEFAULT_OCCURRENCE = 0.01  # Default occurrence is 0.01 (1% of basetime)
	MIN_OCCURRENCE = 0         # Minimum occurrence is 0 (never)
	MAX_OCCURRENCE = 1         # Maximum occurrence is 1 (always)
	DEFAULT_VOLUME = 100       # Default volume is 100% (100)
	MIN_VOLUME = 0             # Minimum volume is 0%
	MAX_VOLUME = 1             # Maximum volume is 100% (1.0)
	DEFAULT_COOLDOWN = 10      # Default cooldown is 10 seconds
	# MIN and MAX cooldown are not defined, as they are not needed

	# Default colors
	COLOR_TEXT = '#000000'     # Text color: black
	COLOR_BG = '#ffffff'       # Background color: white
	COLOR_EMPH = '#c80000'     # Emphasizing color: red
	COLOR_FADE = '#7f7f7f'     # Fading color: grey


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
		self.default_colors = self.colors

		# Saves theme keys and connects them to theme object {theme_id: Theme(), ...}
		self.themes = {}

		# Saves theme keys and connects them to global effect object
		# {global_Effect_id: GlobalEffect(), ...}
		self.global_effects = {}


	def __str__(self):
		'''
		:returns: String representation of all themes and global effects of this box.
		'''

		ret = ['RPGmusicbox', 'Themes']
		for key in sorted(self.themes):
			ret.append(str(self.themes[key]))

		ret.append('Global effects')

		for key in sorted(self.global_effects):
			ret.append(str(self.global_effects[key]))

		return '\n'.join(ret)


	def update_colors(self, new_colors, default=False):
		'''
		Sets a color in the config.
		'''

		colors = {}

		for name in self.name_to_color:
			if name in new_colors:
				colors[name] = Color(new_colors[name])
			else:
				colors[name] = Color(self.name_to_color[name])

		if default:
			self.colors = Colormap(**colors)
		else:
			return Colormap(**colors)


	def add_global_effect(self, kid, filename, name, volume, interrupting):
		'''
		Adds a global effect.
		'''

		self._ensure_valid_id(kid)
		volume = self._ensure_volume(volume)

		self.global_effects[kid] = GlobalEffect(
			filename=filename,
			key=chr(kid),
			name=name,
			volume=volume,
			interrupting=interrupting
		)


	def add_theme(self, kid, name, colors):
		'''
		Adds a theme.
		'''

		colors = self.update_colors(colors, default=False)

		self.themes[kid] = Theme(kid=kid, name=name, colors=colors)


	def add_song(self, kid, path, name, volume):
		'''
		Adds a background song to a theme.
		'''

		volume = self._ensure_volume(volume)

		self.themes[kid].add_song(Song(path, name, volume))


	def add_sound(self, kid, path, name, volume, cooldown, loop):
		'''
		Adds a sound effect to a theme.
		'''

		volume = self._ensure_volume(volume)

		self.themes[kid].add_sound(Sound(path, name=name, volume=volume, cooldown=cooldown, loop=loop))


	def add_occurrences(self, kid, occurrences):
		'''
		Adds a sound effect to a theme.
		'''

		self.themes[kid].occurrences = occurrences


	def _ensure_valid_id(self, kid):
		'''
		Ensures, that a given keyboard key (or rather its id) is valid for the RPGbox.

		:param kid: The key id to check (not the key, but its id!)
		:raises: ValueError
		'''

		# Allowed: 0-9, a-z
		if not (48 <= kid <= 57 or 97 <= kid <= 122):
			raise ValueError(
				'The key {} is not in the allowed range (a-z lowercase and 0-9 only!)'.
				format(chr(kid))
			)

		if kid in self.global_effects or kid in self.themes:
			raise ValueError('The key {} is already registered!'.format(chr(kid)))


	def _ensure_volume(self, vol):
		'''
		Ensures that a given volume is within the allowed range.

		:param v: The volume to check
		:returns: The volume, that is guaranteed to be within the allowed range
		'''

		if vol < self.MIN_VOLUME:
			return self.MIN_VOLUME
		if vol > self.MAX_VOLUME:
			return self.MAX_VOLUME

		return vol


	def ensure_basetime(self, basetime):
		'''
		Ensures that a given basetime is within the allowed range.

		:param b: The basetime to check
		:returns: The basetime, that is guaranteed to be within the allowed range
		'''

		if basetime < self.MIN_BASETIME:
			return self.MIN_BASETIME
		if basetime > self.MAX_BASETIME:
			return self.MAX_BASETIME

		return basetime


	def _ensure_occurrence(self, occ):
		'''
		Ensures that a given occurrence is within the allowed range.

		:param o: The occurrence to check
		:returns: The occurrence, that is guaranteed to be within the allowed range
		'''

		if occ < self.MIN_OCCURRENCE:
			return self.MIN_OCCURRENCE
		if occ > self.MAX_OCCURRENCE:
			return self.MAX_OCCURRENCE

		return occ


	def get_ids(self):
		'''
		:returns: a list of two lists: the keys of all global ids and the keys of all theme ids
		'''

		return list(self.global_effects.keys()), list(self.themes.keys())


	def get_global_effects(self):
		'''
		:returns: all global effects (a dict in the form {global_Effect_id: GlobalEffect(), ...})
		'''

		return self.global_effects


	def get_theme(self, theme_id):
		'''
		:param theme_id: The id of the theme to get
		:returns: The Theme object of the desired theme
		:raises KeyError: if the given theme_id is no theme_id
		'''

		if theme_id in self.themes:
			return self.themes[theme_id]

		raise KeyError('The key {} is not registered.'.format(theme_id))
