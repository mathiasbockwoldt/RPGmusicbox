from random import shuffle


class Playlist():
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
		self.now_playing = -1

		while len(self.playlist) < self.remember:
			self._extend_playlist()


	def _extend_playlist(self):
		''' Extends the playlist, taking care that no song is repeated directly '''

		if len(self.songs) == 1:
			self.playlist.append(self.songs[0])
		else:
			new_songlist = self.songs[:]
			shuffle(new_songlist)

			if self.playlist:
				# prevent two songs from being played one after another (but don't try it indefinitely long)
				i = 0
				while new_songlist[0] == self.playlist[-1] and i < 10:
					shuffle(new_songlist)
					i += 1

			self.playlist.extend(new_songlist)


	# I don't need this function until now. If playlists get too long, it would be a good idea to write this method
	#def _shorten_playlist(self):
	#	''' Cuts away parts in the beginning of the playlist to save memory '''
	#
	#	pass


	def next_song(self):
		''' :returns: The next song '''

		if not self.playlist:
			return None

		if self.now_playing > len(self.playlist) - self.remember:
			self._extend_playlist()

		self.now_playing += 1

		return self.playlist[self.now_playing]


	def previous_song(self):
		''' :returns: The previous song (if there is any) '''

		if not self.playlist:
			return None

		self.now_playing -= 1

		if self.now_playing >= 0:
			return self.playlist[self.now_playing]

		# In case, previous_song() is called multiple times while in the beginning of the list, the pointer needs to be reset to 0, such that next_song() starts at 0 again.
		self.now_playing += 1
		return None


	def get_songs_for_viewing(self):
		'''
		:returns: A list with three songs that are the previous, current and next song. If there is only one song in the whole playlist, the list will have only one element. If the current song is the first one in the playlist, the list will have only two elements.
		'''

		if not self.playlist:
			return None

		# If there is only one song in total
		if len(self.songs) == 1:
			return self.songs	# [the_only_song]

		# If the first song did not yet start to play
		if self.now_playing < 0:
			return ['', self.playlist[0]]	# ['', next]

		# If the first song plays
		if self.now_playing == 0:
			return self.playlist[0:2]	# [current, next]

		# Usual playing
		return self.playlist[self.now_playing - 1: self.now_playing + 2]	# [prev, current, next]
