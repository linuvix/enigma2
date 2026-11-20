from keyids import KEYIDS
from Components.config import config
from Components.RcModel import rc_model

keyBindings = {}

# --- OpenATV Compat: Key Aliases ---
# OpenATV plugins use "keyDown", "keyUp", etc.  OpenPLi uses "down", "up".
#
# IMPORTANT: This table is STRICTLY UNIDIRECTIONAL.
#   key  = OpenATV spelling (or legacy/alternate spelling)
#   value = OpenPLi canonical spelling
#
# Do NOT add the reverse mapping ("down": "keyDown").  Doing so turns the
# alias relation into a symmetric set and causes two different spellings
# to resolve to overlapping candidate sets, which poisons keyBindings and
# makes the C++ eActionMap dispatch the wrong action into the wrong
# context (this was the cause of the bcm_accel crash).
#
# Do NOT chain aliases (A->B, B->C).  Resolution is one hop only.
ACTION_ALIASES = {
	# Navigation / transport
	"keyUp": "up",
	"keyDown": "down",
	"keyLeft": "left",
	"keyRight": "right",
	"keyOK": "ok",
	"keyMenu": "menu",
	"keyExit": "exit",
	"keyInfo": "info",
	"keyBack": "back",
	"keyChannelUp": "channelUp",
	"keyChannelDown": "channelDown",
	"keyVolumeUp": "volumeUp",
	"keyVolumeDown": "volumeDown",
	"keyRed": "red",
	"keyGreen": "green",
	"keyYellow": "yellow",
	"keyBlue": "blue",
	"keyPlay": "play",
	"keyPause": "pause",
	"keyStop": "stop",
	"keyRecord": "record",
	"keyFastForward": "fastforward",
	"keyRewind": "rewind",

	# Uppercase variants used by some OpenATV plugins / CockpitActions.
	"OK": "ok",
	"EXIT": "exit",
	"CANCEL": "cancel",
	"SAVE": "save",
	"INFO": "info",
	"INFOS": "info",
	"MENU": "menu",
	"MENUS": "menu",

	# OpenATV SmartSeek / Cockpit action names.
	"CHANNELUP": "channelUp",
	"CHANNELDOWN": "channelDown",

	# OpenATV setup file-picker action name -> OpenPLi "select".
	"file": "select",
}
# --- End OpenATV Compat ---

keyDescriptions = [{  # id=0 - dmm0 remote directory, DM8000.
	# However, the dmm0 rcpositions.xml file should define
	# an <rc id=0 /> element, but it does not, it only has
	# an <rc id=2 /> element.
	#
	# The rcpositions.xml file defines <button/> elements,
	# but they do not appear to emit codes.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_AUDIO"]: ("YELLOW",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PLUGIN",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EDIT"]: ("EPGSETUP",),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_FASTFORWARD"]: ("FORWARD",),
	KEYIDS["KEY_FAVORITES"]: ("FAV",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LAST"]: ("BACK",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_MEDIA"]: ("MEDIA",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_NEXTSONG"]: ("NEXTSONG",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_PLAY"]: ("PLAY",),
	KEYIDS["KEY_PLAYPAUSE"]: ("PLAYPAUSE",),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_PREVIOUSSONG"]: ("PREVIOUSSONG",),
	KEYIDS["KEY_PROGRAM"]: ("TIMER",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RECORD",),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_SCREEN"]: ("SCREEN",),
	KEYIDS["KEY_SEARCH"]: ("WWW",),
	KEYIDS["KEY_SLEEP"]: ("SLEEP",),
	KEYIDS["KEY_STOP"]: ("STOP",),
	KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("PVR",),
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",)
}, {  # id=1 - dmm0 remote directory, other than DM8000.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_AUDIO"]: ("AUDIO",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PLUGIN",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EDIT"]: ("EPGSETUP",),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_FASTFORWARD"]: ("BLUE", "SHIFT"),
	KEYIDS["KEY_FAVORITES"]: ("FAV",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LAST"]: ("BACK",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_MEDIA"]: ("MEDIA",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_PLAY"]: ("GREEN", "SHIFT"),
	KEYIDS["KEY_PAUSE"]: ("YELLOW", "SHIFT"),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_PROGRAM"]: ("TIMER",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RADIO", "SHIFT"),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_REWIND"]: ("RED", "SHIFT"),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_SCREEN"]: ("SCREEN",),
	KEYIDS["KEY_SEARCH"]: ("WWW",),
	KEYIDS["KEY_SLEEP"]: ("SLEEP",),
	KEYIDS["KEY_STOP"]: ("TV", "SHIFT"),
	KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("PVR",),
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",)
}, {  # id=2 - Everything else.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_ARCHIVE"]: ("HISTORY",),
	KEYIDS["KEY_AUDIO"]: ("AUDIO",),
	KEYIDS["KEY_AUX"]: ("WIZTV",),
	KEYIDS["KEY_BACK"]: ("RECALL",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PLUGIN",),
	KEYIDS["KEY_CALENDAR"]: ("AUTOTIMER",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_CONTEXT_MENU"]: ("CONTEXT",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EJECTCD"]: ("EJECTCD",),
	KEYIDS["KEY_END"]: ("END",),
	KEYIDS["KEY_ENTER"]: ("ENTER", "kbd"),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_F1"]: ("F1",),
	KEYIDS["KEY_F2"]: ("F2",),
	KEYIDS["KEY_F3"]: ("F3",),
	KEYIDS["KEY_FASTFORWARD"]: ("FASTFORWARD",),
	KEYIDS["KEY_FAVORITES"]: ("FAV",),
	KEYIDS["KEY_FILE"]: ("LIST",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_HOME"]: ("HOME",),
	KEYIDS["KEY_HOMEPAGE"]: ("HOMEPAGE",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LAST"]: ("BACK",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_LIST"]: ("PLAYLIST",),
	KEYIDS["KEY_MEDIA"]: ("MEDIA",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MODE"]: ("VKEY",),
	KEYIDS["KEY_MP3"]: ("MP3",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_NEXTSONG"]: ("NEXTSONG",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_OPTION"]: ("OPTION",),
	KEYIDS["KEY_PAGEDOWN"]: ("PAGEDOWN",),
	KEYIDS["KEY_PAGEUP"]: ("PAGEUP",),
	KEYIDS["KEY_PAUSE"]: ("PAUSE",),
	KEYIDS["KEY_PC"]: ("LAN",),
	KEYIDS["KEY_PLAY"]: ("PLAY",),
	KEYIDS["KEY_PLAYPAUSE"]: ("PLAYPAUSE",),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_POWER2"]: ("POWER2",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_PREVIOUSSONG"]: ("PREVIOUSSONG",),
	KEYIDS["KEY_PROGRAM"]: ("TIMER",),
	KEYIDS["KEY_PVR"]: ("PVR",),
	KEYIDS["KEY_QUESTION"]: ("ABOUT",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RECORD",),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_REWIND"]: ("REWIND",),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_SAT"]: ("SAT",),
	KEYIDS["KEY_SCREEN"]: ("SCREEN",),
	KEYIDS["KEY_SEARCH"]: ("WWW",),
	KEYIDS["KEY_SETUP"]: ("SETUP",),
	KEYIDS["KEY_SLEEP"]: ("SLEEP",),
	KEYIDS["KEY_SLOW"]: ("SLOW",),
	KEYIDS["KEY_STOP"]: ("STOP",),
	KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",),
	KEYIDS["KEY_SUSPEND"]: ("SUSPEND",),
	KEYIDS["KEY_SWITCHVIDEOMODE"]: ("VMODE",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TIME"]: ("TIMESHIFT",),
	KEYIDS["KEY_TOUCHPAD_TOGGLE"]: ("TOUCHPAD_TOGGLE",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_TV2"]: ("TV2",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("VIDEO",),
	KEYIDS["KEY_VOD"]: ("VOD",),
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_WAKEUP"]: ("WAKEUP",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",),
	KEYIDS["KEY_ZOOM"]: ("ZOOM",)
}, {  # id=3 - XP1000.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_AUDIO"]: ("AUDIO",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PORTAL",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_FASTFORWARD"]: ("FASTFORWARD",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_NEXTSONG"]: ("NEXTSONG",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_PLAY"]: ("PLAY",),
	KEYIDS["KEY_PLAYPAUSE"]: ("PLAYPAUSE",),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_PREVIOUSSONG"]: ("PREVIOUSSONG",),
	KEYIDS["KEY_PROGRAM"]: ("TIMER",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RECORD",),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_REWIND"]: ("REWIND",),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_SLEEP"]: ("SLEEP",),
	KEYIDS["KEY_STOP"]: ("STOP",),
	KEYIDS["KEY_SUBTITLE"]: ("SUBTITLE",),
	KEYIDS["KEY_SWITCHVIDEOMODE"]: ("VMODE",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("PVR",),
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",)
}, {  # id=4 - Formuler F1/F3.
	KEYIDS["BTN_0"]: ("UP", "fp"),
	KEYIDS["BTN_1"]: ("DOWN", "fp"),
	KEYIDS["KEY_0"]: ("0",),
	KEYIDS["KEY_1"]: ("1",),
	KEYIDS["KEY_2"]: ("2",),
	KEYIDS["KEY_3"]: ("3",),
	KEYIDS["KEY_4"]: ("4",),
	KEYIDS["KEY_5"]: ("5",),
	KEYIDS["KEY_6"]: ("6",),
	KEYIDS["KEY_7"]: ("7",),
	KEYIDS["KEY_8"]: ("8",),
	KEYIDS["KEY_9"]: ("9",),
	KEYIDS["KEY_AUDIO"]: ("AUDIO",),
	KEYIDS["KEY_BACK"]: ("RECALL",),
	KEYIDS["KEY_BLUE"]: ("BLUE",),
	KEYIDS["KEY_BOOKMARKS"]: ("PLAYLIST",),
	KEYIDS["KEY_CHANNELDOWN"]: ("BOUQUET-",),
	KEYIDS["KEY_CHANNELUP"]: ("BOUQUET+",),
	KEYIDS["KEY_CONTEXT_MENU"]: ("CONTEXT",),
	KEYIDS["KEY_DOWN"]: ("DOWN",),
	KEYIDS["KEY_EPG"]: ("EPG",),
	KEYIDS["KEY_EXIT"]: ("EXIT",),
	KEYIDS["KEY_F1"]: ("F1",),
	KEYIDS["KEY_F2"]: ("F2",),
	KEYIDS["KEY_F3"]: ("F3",),
	KEYIDS["KEY_FASTFORWARD"]: ("FASTFORWARD",),
	KEYIDS["KEY_FAVORITES"]: ("FAVORITES",),
	KEYIDS["KEY_GREEN"]: ("GREEN",),
	KEYIDS["KEY_HELP"]: ("HELP",),
	KEYIDS["KEY_INFO"]: ("INFO",),
	KEYIDS["KEY_LEFT"]: ("LEFT",),
	KEYIDS["KEY_MENU"]: ("MENU",),
	KEYIDS["KEY_MUTE"]: ("MUTE",),
	KEYIDS["KEY_NEXT"]: ("ARROWRIGHT",),
	KEYIDS["KEY_OK"]: ("OK",),
	KEYIDS["KEY_PAUSE"]: ("PAUSE",),
	KEYIDS["KEY_PLAY"]: ("PLAY",),
	KEYIDS["KEY_POWER"]: ("POWER",),
	KEYIDS["KEY_PREVIOUS"]: ("ARROWLEFT",),
	KEYIDS["KEY_RADIO"]: ("RADIO",),
	KEYIDS["KEY_RECORD"]: ("RECORD",),
	KEYIDS["KEY_RED"]: ("RED",),
	KEYIDS["KEY_REWIND"]: ("REWIND",),
	KEYIDS["KEY_RIGHT"]: ("RIGHT",),
	KEYIDS["KEY_STOP"]: ("STOP",),
	KEYIDS["KEY_TEXT"]: ("TEXT",),
	KEYIDS["KEY_TV"]: ("TV",),
	KEYIDS["KEY_UP"]: ("UP",),
	KEYIDS["KEY_VIDEO"]: ("PVR",),
	KEYIDS["KEY_VOLUMEDOWN"]: ("VOL-",),
	KEYIDS["KEY_VOLUMEUP"]: ("VOL+",),
	KEYIDS["KEY_YELLOW"]: ("YELLOW",)
}]

labels = {  # This is not currently used anywhere. It is just present to populate the pot file.
	"ABOUT": _("ABOUT"),
	"ARROWLEFT": _("ARROWLEFT"),
	"ARROWRIGHT": _("ARROWRIGHT"),
	"AUDIO": _("AUDIO"),
	"AUTOTIMER": _("AUTOTIMER"),
	"BACK": _("BACK"),
	"BLUE": _("BLUE"),
	"BOUQUET+": _("BOUQUET+"),
	"BOUQUET-": _("BOUQUET-"),
	"CONTEXT": _("CONTEXT"),
	"DOWN": _("DOWN"),
	"EJECTCD": _("EJECTCD"),
	"END": _("END"),
	"ENTER": _("ENTER"),
	"EPG": _("EPG"),
	"EPGSETUP": _("EPGSETUP"),
	"EXIT": _("EXIT"),
	"FASTFORWARD": _("FASTFORWARD"),
	"FAV": _("FAV"),
	"FAVORITES": _("FAVORITES"),
	"FORWARD": _("FORWARD"),
	"GREEN": _("GREEN"),
	"HELP": _("HELP"),
	"HISTORY": _("HISTORY"),
	"HOME": _("HOME"),
	"HOMEPAGE": _("HOMEPAGE"),
	"INFO": _("INFO"),
	"LAN": _("LAN"),
	"LEFT": _("LEFT"),
	"LIST": _("LIST"),
	"MEDIA": _("MEDIA"),
	"MENU": _("MENU"),
	"MUTE": _("MUTE"),
	"NEXTSONG": _("NEXTSONG"),
	"OK": _("OK"),
	"OPTION": _("OPTION"),
	"PAGEDOWN": _("PAGEDOWN"),
	"PAGEUP": _("PAGEUP"),
	"PAUSE": _("PAUSE"),
	"PLAY": _("PLAY"),
	"PLAYLIST": _("PLAYLIST"),
	"PLAYPAUSE": _("PLAYPAUSE"),
	"PLUGIN": _("PLUGIN"),
	"PORTAL": _("PORTAL"),
	"POWER": _("POWER"),
	"POWER2": _("POWER2"),
	"PREVIOUSSONG": _("PREVIOUSSONG"),
	"PVR": _("PVR"),
	"RADIO": _("RADIO"),
	"RECALL": _("RECALL"),
	"RECORD": _("RECORD"),
	"RED": _("RED"),
	"REWIND": _("REWIND"),
	"RIGHT": _("RIGHT"),
	"SAT": _("SAT"),
	"SCREEN": _("SCREEN"),
	"SETUP": _("SETUP"),
	"SLEEP": _("SLEEP"),
	"SLOW": _("SLOW"),
	"STOP": _("STOP"),
	"SUBTITLE": _("SUBTITLE"),
	"SUSPEND": _("SUSPEND"),
	"TEXT": _("TEXT"),
	"TIMER": _("TIMER"),
	"TIMESHIFT": _("TIMESHIFT"),
	"TV": _("TV"),
	"UP": _("UP"),
	"VIDEO": _("VIDEO"),
	"VKEY": _("VKEY"),
	"VMODE": _("VMODE"),
	"VOL+": _("VOL+"),
	"VOL-": _("VOL-"),
	"WAKEUP": _("WAKEUP"),
	"WIZTV": _("WIZTV"),
	"WWW": _("WWW"),
	"YELLOW": _("YELLOW"),
	"ZOOM": _("ZOOM"),
}


def canonicalAction(action):
	"""
	Map an incoming action name to its canonical OpenPLi spelling.

	Resolution is strictly one hop: if 'action' is an alias key, return
	its target; otherwise return 'action' unchanged.  There is NO reverse
	lookup, because that would make the alias relation symmetric and
	cause two spellings to collide inside eActionMap.
	"""
	return ACTION_ALIASES.get(action, action)


def addKeyBinding(domain, key, context, action, flags):
	"""
	Register a key binding under its canonical action name only.

	OpenATV spellings ("keyDown") are normalised to the OpenPLi canonical
	spelling ("down") before storage, so a single binding exists per
	(context, action) pair regardless of which spelling the caller used.
	"""
	keyBindings.setdefault((context, canonicalAction(action)), []).append((key, domain, flags))


def removeKeyBinding(key, context, action, wild=True):
	if wild and action == "*":
		for ctx, ctx_action in list(keyBindings.keys()):
			if ctx == context:
				removeKeyBinding(key, context, ctx_action, False)
		return

	contextAction = (context, canonicalAction(action))
	if contextAction in keyBindings:
		bind = [x for x in keyBindings[contextAction] if x[0] != key]
		if bind:
			keyBindings[contextAction] = bind
		else:
			del keyBindings[contextAction]


def queryKeyBinding(context, action):
	"""
	Return a list of (key, flags) for the given (context, action).

	The lookup normalises 'action' to its canonical spelling, so a caller
	asking for "keyDown" finds a binding registered as "down" and vice
	versa (the binding itself is always stored canonically).
	"""
	binding = keyBindings.get((context, canonicalAction(action)))
	if binding:
		return [(x[0], x[2]) for x in binding]
	return []


def getKeyDescription(key):
	if rc_model.rcIsDefault():
		idx = config.misc.rcused.value
	else:
		rcType = config.plugins.remotecontroltype.rctype.value
		if rcType == 14:  # XP1000
			idx = 3
		elif rcType == 18:  # F1
			idx = 4
		else:
			idx = 2
	return keyDescriptions[idx].get(key)


def getKeyBindingKeys(filterfn=lambda key: True):
	# Python 3 returns a lazy filter object; OpenATV callers expect a
	# subscriptable / len()-able collection, so materialise it.
	return list(filter(filterfn, keyBindings))


def removeKeyBindings(domain):
	# Snapshot the keys so we can safely delete entries while iterating.
	for contextAction in list(keyBindings.keys()):
		remaining = [e for e in keyBindings[contextAction] if e[1] != domain]
		if remaining:
			keyBindings[contextAction] = remaining
		else:
			del keyBindings[contextAction]


def getFpAndKbdKeys():  # used by HelpMenuList
	return {k for i in keyDescriptions for k, v in i.items() if len(v) > 1 and v[1] in ("fp", "kbd")}
