import pygame

class Display():


	def __init__(self, colors):
		self.colors = colors
		pygame.display.set_caption('RPGbox player')        # Set window title

		# Define positional variables
		self.display_width = 0
		self.display_panel_width = 0
		self.display_footer_width = 0
		self.display_height = 0
		self.display_panel_height = 0
		self.display_footer_height = 0
		self.display_border = 0

		# Define Surface variables to drawon
		self.screen = None
		self.background = None
		self.text_global_keys = None
		self.text_theme_keys = None
		self.text_now_playing = None
		self.text_footer = None

		# Define fonts
		self.standard_font = pygame.font.Font(None, 24)
		self.header_font = pygame.font.Font(None, 32)


	def update_colors(self, colors):
		self.colors = colors


	def screen_size_changed(self, width, height):
		'''
		Updates the screen parameters.
		'''

		self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)

		self.background = pygame.Surface(self.screen.get_size()).convert()
		self.background.fill(self.colors.bg)
		self.screen.blit(self.background, (0, 0))
		pygame.display.flip()

		w, h = self.background.get_size()
		self.display_width = w
		self.display_panel_width = w // 3
		self.display_footer_width = w // 6
		self.display_height = h
		self.display_panel_height = h - 2 * self.standard_font.size(' ')[1]
		self.display_footer_height = h - self.display_panel_height
		self.display_border = 5

		self.text_global_keys = pygame.Surface((self.display_panel_width, self.display_panel_height))
		self.text_theme_keys = pygame.Surface((self.display_panel_width, self.display_panel_height))

		# The display_width - 2*panel_width fills the rounding error pixels on the right side
		self.text_now_playing = pygame.Surface((self.display_width - 2*self.display_panel_width, self.display_panel_height))

		# The footer stretches horizontally to 100%.
		# The display_footer_width is for the single elements in the footer.
		self.text_footer = pygame.Surface((self.display_width, self.display_footer_height))


	def draw_line(self, area, t, color, font):
		'''
		Prints one line of text to a panel.

		:param area: A rect with information, where the text shall be blitted on the background
		:param t: The text to be rendered
		:param color: The color of the text
		:param font: The font object that shall be rendered
		'''

		text_rect = font.render(t, True, color)
		self.background.blit(text_rect, area)
		area.top += font.get_linesize()


	def draw_footer_element(self, n, field):
		'''
		Helper function for self.draw_footer(). Prints two lines of text to screen in a given color.
		It never updates the screen.

		:param n: The number of the panel in the footer counted from the left (determines position)
		:param field: Field with a tuple of two strings with the lines to be rendered and the information whether the field is active or not
		'''

		fgcolor = self.colors.text
		bgcolor = self.colors.bg

		if not field.active:
			fgcolor, bgcolor = bgcolor, fgcolor

		s = pygame.Surface((self.display_footer_width, self.display_footer_height)).convert()
		s.fill(bgcolor)
		s_pos = s.get_rect()

		for i, line in enumerate(field.text):
			t = self.standard_font.render(line, True, fgcolor)
			t_pos = t.get_rect()
			t_pos.centerx = s_pos.centerx
			t_pos.top = t_pos.height * i
			s.blit(t, t_pos2)

		s_pos.top = self.display_panel_height
		s_pos.left = n * self.display_footer_width

		self.background.blit(s, s_pos)


	def draw_footer(self, fields, update):
		'''
		Draw the footer

		:param fields:
		:param update: Boolean to state, whether the display should be updated
		'''

		self.text_footer.fill(self.colors.bg)
		rect = self.background.blit(self.text_footer, (0, self.display_panel_height))

		for i, field in enumerate(fields):
			self.draw_footer_element(i, field)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(rect)


	def draw_global_effects(self, fields, update):
		'''
		Draw the global effects panel

		:param fields:
		:param update: Boolean to state, whether the display should be updated
		'''

		self.text_global_keys.fill(self.colors.bg)
		rect = self.background.blit(self.text_global_keys, (0, 0))

		area = self.text_global_keys.get_rect()
		area.left = self.display_border
		area.top = self.display_border

		self.draw_line(area, 'Global Keys', self.colors.text, self.header_font)
		self.draw_line(area, '', self.colors.text, self.standard_font)

		for field in fields:
			if field.active:
				color = self.colors.emph
			else:
				color = self.colors.text

			self.draw_line(area, field.text, color, self.standard_font)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(rect)


	def draw_themes(self, fields, update):
		'''
		Draw the themes panel

		:param fields:
		:param update: Boolean to state, whether the display should be updated
		'''

		self.text_theme_keys.fill(self.colors.bg)
		rect = self.background.blit(self.text_theme_keys, (self.display_panel_width, 0))

		area = self.text_theme_keys.get_rect()
		area.left = self.display_panel_width + self.display_border
		area.top = self.display_border

		self.draw_line(area, 'Themes', self.colors.text, self.header_font)
		self.draw_line(area, '', self.colors.text, self.standard_font)

		for field in fields:
			if field.active:
				color = self.colors.emph
			else:
				color = self.colors.text

			self.draw_line(area, field.text, color, self.standard_font)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(rect)


	def draw_playing(self, fields, update):
		'''
		Draw the "now playing" panel

		:param fields:
		:param update: Boolean to state, whether the display should be updated
		'''

		self.text_now_playing.fill(self.colors.bg)
		rect = self.background.blit(self.text_now_playing, (2 * self.display_panel_width, 0))

		area = self.text_now_playing.get_rect()
		area.left = 2 * self.display_panel_width + self.display_border
		area.top = self.display_border

		self.draw_line(area, 'Now Playing', self.colors.text, self.header_font)
		self.draw_line(area, '', self.colors.text, self.standard_font)

		# Possible colors sorted to match the expectations by Player.update_text_now_playing()
		possible_colors = [self.colors.text, self.colors.emph, self.colors.fade]

		for field in fields:
			color = possible_colors[field.active]
			self.draw_line(area, field.text, color, self.standard_font)

		self.screen.blit(self.background, (0, 0))

		if update:
			pygame.display.update(rect)
