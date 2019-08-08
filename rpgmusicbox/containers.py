class Sound():
	'''
	Container for one sound.
	'''

	def __init__(self, filename, name, volume = 1, cooldown = 10, occurrence = 0.01, loop = False):
		'''
		Initiates the sound.

		:param filename: String with the filename
		:param name: String with the name
		:param volume: Float with the relative volume (already adjusted by the theme volume)
		:param cooldown: Float with the cooldown time in seconds
		:param occurrence: Float with relative occurrence (already adjusted by the theme basetime)
		:param loop: Boolean whether the sound shall be played indefinitely or not. `occurrence` is disregarded when loop is True.
		'''

		self.filename = str(filename)
		self.name = str(name)
		self.volume = float(volume)
		self.cooldown = float(cooldown)
		self.occurrence = float(occurrence)
		self.loop = bool(loop)
		if self.loop:
			self.occurrence = 0.01


	def __str__(self):
		''' :returns: A string representation of the sound with all attributes. '''

		return ''.join((self.filename, ' (vol: ', str(self.volume), ', occ: ', '{:.4f}'.format(self.occurrence), ', cd: ', str(self.cooldown), ', loop: ', str(self.loop), ')'))


class Song():
	'''
	Container for one song.
	'''

	def __init__(self, filename, name, volume = 1):
		'''
		Initiates the song.

		:param filename: String with the filename
		:param name: String with the name
		:param volume: Float with the relative volume (already adjusted by the theme volume)
		'''

		self.filename = str(filename)
		self.name = str(name)
		self.volume = float(volume)


	def __str__(self):
		''' :returns: A string representation of the song with its volume. '''

		return ''.join((self.filename, ' (vol: ', str(self.volume), ')'))


class Global_Effect():
	'''
	Container for one global effect.
	'''

	def __init__(self, filename, key, name, volume = 1, interrupting = True):
		'''
		Initiates the global effect.

		:param filename: String with the filename
		:param key: The keyboard key to activate the global effect. Must be a one-letter string.
		:param name: String with the name
		:param volume: Float with the relative volume (already adjusted by the theme volume)
		:param interrupting: Boolean that indicates, whether the global effect should interrupt playing music and sounds, or not.
		'''

		self.filename = str(filename)
		self.key = str(key)[0]
		self.name = str(name)
		self.volume = float(volume)
		self.interrupting = bool(interrupting)


	def __str__(self):
		''' :returns: A string representation of the global effect with its attributes. '''

		if self.interrupting:
			s = ', interrupting'
		else:
			s = ''
		return ''.join((self.key, ') ', self.name, ': ', self.filename, ' (vol: ', str(self.volume), s, ')'))


class Theme():
	'''
	Container for one theme including its songs and sounds.
	'''

	def __init__(self, kid, name, colors, songs = None, sounds = None, occurrences = None):
		'''
		Initiates the theme.

		:param kid: The keyboard key id to activate the theme. Must be an integer (ord(c) of the key c).
		:param name: String with the name of the theme.
		:param colors: A dictionary with the colors for this theme
		:param songs: A list with songs in the theme.
		:param sounds: A list with sounds in the theme.
		:param occurrences: A list with occurrences of the songs in the theme.
		'''

		self.theme_ID = kid
		self.key = chr(kid)
		self.name = str(name)

		if songs is None:
			self.songs = []
		else:
			self.songs = songs[:]

		if sounds is None:
			self.sounds = []
		else:
			self.sounds = sounds[:]

		if occurrences is None:
			self.occurrences = []
		else:
			self.occurrences = occurrences[:]

		self.colors = colors


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


	def add_song(self, song):
		'''
		Add a song to the theme.

		:param song: The Song object to add
		'''

		self.songs.append(song)


	def add_sound(self, sound):
		'''
		Add a sound to the theme

		:param sound: The Sound object to add
		'''

		self.sounds.append(sound)


	def add_occurrences(self, occurrences):
		'''
		Adds a list of occurrences to the theme. The total number of occurrences after the addition must be the same as the total number of songs in the theme. So add the songs first.

		:param occurrences: List of occurrences of the songs
		:raises KeyError: When the total number of occurrences does not fit the total number of songs in the theme
		'''

		self.occurrences.extend(occurrences)

		if len(self.occurrences) != len(self.sounds):
			raise KeyError('The number of sounds is not equal to the number of occurrences in {}!'.format(self.name))

		for i in range(len(self.sounds)):
			self.sounds[i].occurrence = self.occurrences[i]
