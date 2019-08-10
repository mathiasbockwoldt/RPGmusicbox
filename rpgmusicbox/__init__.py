from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from .version import __version__
from .xml_reader import read_xml
from .box import RPGmusicbox
from .player import Player
