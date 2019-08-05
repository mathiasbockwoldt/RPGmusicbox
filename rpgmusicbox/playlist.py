from random import shuffle


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
			shuffle(newSonglist)

			if self.playlist:
				# prevent two songs from being played one after another (but don't try it indefinitely long)
				i = 0
				while newSonglist[0] == self.playlist[-1]:
					if i >= 10:
						break
					shuffle(newSonglist)
					i += 1

			self.playlist.extend(newSonglist)


	# I don't need this function until now. If playlists get too long, it would be a good idea to write this function
	#def _shortenPlaylist(self):
	#	''' Cuts away parts in the beginning of the playlist to save memory '''
	#
	#	pass


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
