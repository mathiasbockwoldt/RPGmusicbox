RPGbox
======

This script, the RPGbox, is thought to help to create atmosphere at the game table by adding music and sound effects to it.

A disco in Shadowrun could have plenty of background music and some shouting guests, clinking glasses, and some gun shots as random sound effects. A bar in D&D may have mumbling guests as background music and shouts and moving chairs as sound effects. You may also imagine a beach with rolling waves in the background and sea gulls, noises of ships, and laughter of children occasionally interspersed. Or what about a rainy forrest, say for Cthulhu? Heavy showers in the background, and every now and then, you hear thunder, birds, and wind. And of course, when it comes to fight, all sounds fade out to make place for throbbing battle music.

RPGbox can provide all of this. First, you need to collect the music and the sound effects (if you want any). See below for possible sources. Then, you create an xml file in which you define themes and associate the background and effect sounds to them.

At the gaming table, you set up the computer with speakers and a keyboard. No mouse fiddling is needed. When you need a certain theme, just hit the corresponding key on your keyboard. The background music will start in random order and sound effects will start playing randomly. You can skip an inappropriate song anytime by pressing the right-arrow key. You can also pause and unpause anytime by hitting space. There is also the possibility for global effects, like some sound for a critical hit or killing a particularly difficult enemy. Or what about the Jeopardy thinking music for some player that cannot decide? These global effects have a key assigned to them that you can press anytime. You can define for each effect whether it should interrupt all other music (Jeopardy music) or just overlay existing music and effects (critical hit).


Dependencies
------------

RPGbox is written in Python 2, but it is ready to be opened with Python 3 as well. The script needs Pygame, which is currently more stable with Python 2. If you installed Pygame for Python 3, you can run the script with Python 3 as well.

- Python: http://www.python.org
- Pygame: http://www.pygame.org/download.shtml
   or newer versions: https://bitbucket.org/pygame/pygame/downloads


Supported media files
---------------------

Media support is limited by Pygame. Currently, only `ogg` and uncompressed `wav` files are generaly supported. Depending on the system, also `mp3` files may be supported for background music but not for sound effects.


The XML file
------------

The XML file contains information about all music, background noises, sound effects etc. Here is an example file:

```xml
<rpgbox version="150824">
	<theme id="theme1" key="t" name="The first theme" basetime="3600" volume="100" default="default">
		<background file="theme1/*.mp3" volume="100" />
		<background file="theme1/veryLoudFile.mp3" volume="75" />
		<background file="generalStuff/niceBG?.mp3" />
		<effect file="theme1/*.ogg" occurence="10" />
		<effect file="theme1/playThisOften.wav" occurence="120" volume="90" />
	</theme>

	<theme id="jungle" key="j">
		<background file="generalStuff/jungle.mp3" />
	</theme>

	<globals volume="100">
		<global file="generalStuff/jeopardy.ogg" id="jeopardy" key="1" name="Jeopardy Thinking Music" volume="100" interrupting="interrupting" />
	</globals>
</rpgbox>
```

All tags and attributes *must* be in lowercase.

The contents of every RPGbox xml file must be contained in `<rpgbox version="xxx">...</rpgbox>`.

Every theme starts with a `<theme>` tag that *must* have an `id` and a `key` attribute. Optionally, every theme can have a `name`, a `basetime`, and a base `volume`. The `id` must be unique and is mainly used internally. The `key` is the keyboard key (a-z, 0-9) that you want to press while in game to start this theme. The `name` is shown on the screen (in case you look at it). If no `name` is given, the `id` will be shown instead. The `basetime` is a reference time in seconds. The default value is 3600 seconds or one hour. It must be in range 1 to 36000 (one second to ten hours). See below at `<effect>` for more info on this attribute. The `volume` is the basic volume of the whole theme in percent. Default is 100 and it must be in range 0 to 100. Optionally, a theme may be set to `default`. If there is a `default` attribute this theme will be started directly, when the script starts. The text of the `default` attribute is irrelevant, it is just there to comply with the xml standard.

Themes may contain an arbitrary number of `<background>` tags. With these tags, you can define music (or noise) files that permanently play in the background in a random order. Every background must have a `file` attribute that points to one or several files. You can address several files by using `*` (matches an arbitrary number of arbitrary characters), `?` (matches exactly one arbitrary character), or `[]` (matches exactly one character in a range of characters, e.g. `[0-9]` or `[asdf]`). In addition, backgrounds may have a `volume` in percent associated to them. Default is 100. The background volume will be adjusted by the theme volume.

Themes may also contain `<effect>` tags. Here, you can define sounds that are randomly played on top of the background music. Like backgrounds, each effect must have a `file` attribute and *may* have a `volume` associated to them. See `<background>` tags for details. In addition, you may define an `occurence` attribute that defines, how often the given sound(s) is played. This `occurence` is always in relation to the `basetime` of the `<theme>`. It states how often (on average) the sound effect will be played within the `basetime`. So if the `basetime` is 3600 (one hour) and the `occurence` is 10. The sound effect(s) will be played approximately ten times per hour or every six minutes. The numbers are not precise, as the sound effects are triggered randomly. Default, minimum and maximum are 1%, 0% and 100%, respectively, of `basetime`.

**Globals**


Keys
----

You can assign all keys from `a` to `z` (lowercase only) and `0` to `9` for any theme or global sound effect. No key may be assigned twice.

Other predefined keys are:

- right-arrow: next song
- left-arrow: previous song (up to ten songs back)
- space: pause or unpause playback
- escape: quit


Sources of music and sounds
---------------------------

OK, now you got the script running, but what should you feed into it? There are plenty of sources for background music and sound effects on the net.

In addition to free online sources, you may also look for soundtracks. Movie soundtracks are great, but they tend to shift the mood within one song as they are fitted to one particular scene. However, there are also many soundtracks for computer or console games. Here, the tracks are more often consistent in mood. Some (particularly older) computer games even have their sound effects in single files, easy to use for background sounds.

Here are some suggestions of free sources on the net.

- [Tabletop Audio](http://tabletopaudio.com) offers ten minute pieces for table top games with different atmospheres that can of course also be used for role-playing games.

- [Kingdom Hearts Insider](http://downloads.khinsider.com) has a large database of computer game soundtracks that can be downloaded.

- [Game Theme Songs](http://www.gamethemesongs.com) also has many, many game songs.

Take care when you want to use prominent soundtracks for gaming. It can create an unwanted atmosphere. Imagine a serious fight of the player vampires against NPC werewolves. The mood is tense, it's a narrow fight – and suddenly the Pirates of the Caribbean main theme blares through the room. This theme is certainly suited for action scenes, but it is completely wrong in an intense fight in the World of Darkness.


Bugs and things that are planned to do
--------------------------------------

You can send me bugs via the GitHub issue system.

A todo list is in the first lines of the script.
