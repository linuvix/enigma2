import errno
import xml.etree.ElementTree

from enigma import addFont, eLabel, ePixmap, ePoint, eRect, eSize, eWidget, eWindow, eWindowStyleManager, eWindowStyleSkinned, getDesktop, gFont, getFontFaces, gRGB, setSpinnerOnOff, BT_ALPHATEST, BT_ALPHABLEND, BT_HALIGN_CENTER, BT_HALIGN_LEFT, BT_HALIGN_RIGHT, BT_KEEP_ASPECT_RATIO, BT_SCALE, BT_VALIGN_BOTTOM, BT_VALIGN_CENTER, BT_VALIGN_TOP
from os.path import basename, dirname, isdir, isfile, join
from os import listdir

from Components.config import ConfigSubsection, ConfigText, config
from Components.RcModel import rc_model
from Components.Sources.Source import ObsoleteSource
from Components.SystemInfo import BoxInfo
from Tools.Directories import SCOPE_CURRENT_LCDSKIN, SCOPE_CONFIG, SCOPE_CURRENT_SKIN, SCOPE_FONTS, SCOPE_SKIN, resolveFilename
from Tools.Import import my_import
from Tools.LoadPixmap import LoadPixmap

DEFAULT_SKIN = BoxInfo.getItem("HasFullHDSkinSupport") and "PLi-FullNightHD/skin.xml" or "PLi-HD/skin.xml"
EMERGENCY_SKIN = "skin_default/skin.xml"
EMERGENCY_NAME = "Stone II"
DEFAULT_DISPLAY_SKIN = "skin_default/skin_display.xml"
USER_SKIN = "skin_user.xml"
USER_SKIN_TEMPLATE = "skin_user_%s.xml"
SUBTITLE_SKIN = "skin_subtitles.xml"

GUI_SKIN_ID = 0
DISPLAY_SKIN_ID = 1

domScreens = {}
colors = {
	"key_back": gRGB(0x00313131),
	"key_blue": gRGB(0x0018188b),
	"key_green": gRGB(0x001f771f),
	"key_red": gRGB(0x009f1313),
	"key_text": gRGB(0x00ffffff),
	"key_yellow": gRGB(0x00a08500)
}
gradients = {}
BodyFont = ("Regular", 20, 24, 18)
fonts = {
	"Body": BodyFont
}
menus = {}
menuicons = {}
parameters = {}
screens = {}
setups = {}
switchPixmap = {}
windowStyles = {}

config.skin = ConfigSubsection()
skin = resolveFilename(SCOPE_SKIN, DEFAULT_SKIN)
if not isfile(skin):
	print("[Skin] Error: Default skin '%s' is not readable or is not a file!  Using emergency skin." % skin)
	DEFAULT_SKIN = EMERGENCY_SKIN
config.skin.primary_skin = ConfigText(default=DEFAULT_SKIN)
config.skin.display_skin = ConfigText(default=DEFAULT_DISPLAY_SKIN)

currentPrimarySkin = None
currentDisplaySkin = None
onLoadCallbacks = []
runCallbacks = False


def InitSkins():
	global currentPrimarySkin, currentDisplaySkin, runCallbacks
	loadSkin(EMERGENCY_SKIN, scope=SCOPE_CURRENT_SKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	loadSkin(SUBTITLE_SKIN, scope=SCOPE_CURRENT_SKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	result = []
	for skin, name in [(config.skin.display_skin.value, "current"), (DEFAULT_DISPLAY_SKIN, "default")]:
		if skin in result:
			continue
		config.skin.display_skin.value = skin
		if loadSkin(config.skin.display_skin.value, scope=SCOPE_CURRENT_LCDSKIN, desktop=getDesktop(DISPLAY_SKIN_ID), screenID=DISPLAY_SKIN_ID):
			currentDisplaySkin = config.skin.display_skin.value
			break
		print("[Skin] Error: Adding %s display skin '%s' has failed!" % (name, config.skin.display_skin.value))
		result.append(skin)
	result = []
	for skin, name in [(config.skin.primary_skin.value, "current"), (DEFAULT_SKIN, "default")]:
		if skin in result:
			continue
		if loadSkin(skin, scope=SCOPE_CURRENT_SKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID):
			currentPrimarySkin = skin
			break
		print("[Skin] Error: Adding %s GUI skin '%s' has failed!" % (name, config.skin.primary_skin.value))
		result.append(skin)
	if isdir(userFolder := join(resolveFilename(SCOPE_CONFIG), dirname(config.skin.primary_skin.value))):
		for file in listdir(userFolder):
			if file.lower().endswith(".xml"):
				loadSkin(join(dirname(config.skin.primary_skin.value), file), scope=SCOPE_CONFIG, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	result = None
	if isfile(resolveFilename(SCOPE_SKIN, config.skin.primary_skin.value)):
		name = USER_SKIN_TEMPLATE % dirname(config.skin.primary_skin.value)
		if isfile(resolveFilename(SCOPE_CURRENT_SKIN, name)):
			result = loadSkin(name, scope=SCOPE_CURRENT_SKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	if result is None:
		loadSkin(USER_SKIN, scope=SCOPE_CURRENT_SKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID)
	if not runCallbacks:
		runCallbacks = True
		for method in onLoadCallbacks:
			if callable(method):
				method()


def loadSkinData(desktop):
	InitSkins()


def loadSkin(filename, scope=SCOPE_SKIN, desktop=getDesktop(GUI_SKIN_ID), screenID=GUI_SKIN_ID):
	global windowStyles
	filename = resolveFilename(scope, filename)
	print("[Skin] Loading skin file '%s'." % filename)
	spinner_suspended = False
	try:
		setSpinnerOnOff(0)
		spinner_suspended = True
	except Exception:
		pass
	try:
		try:
			with open(filename, "r") as fd:
				try:
					domSkin = xml.etree.ElementTree.parse(fd).getroot()
					loadSingleSkinData(desktop, screenID, domSkin, filename, scope=scope)
					for element in domSkin:
						if element.tag == "screen":
							name = element.attrib.get("name", None)
							if name:
								scrnID = element.attrib.get("id", None)
								if scrnID is None or scrnID == screenID:
									domScreens[name] = (element, "%s/" % dirname(filename))
						elif element.tag == "windowstyle":
							scrnID = element.attrib.get("id", None)
							if scrnID is not None:
								scrnID = int(scrnID)
								domStyle = xml.etree.ElementTree.ElementTree(xml.etree.ElementTree.Element("skin"))
								domStyle.getroot().append(element)
								windowStyles[scrnID] = (desktop, screenID, domStyle.getroot(), filename, scope)
					reloadWindowStyles()
					print("[Skin] Loading skin file '%s' complete." % filename)
					return True
				except xml.etree.ElementTree.ParseError as err:
					fd.seek(0)
					content = fd.readlines()
					line, column = err.position
					print("[Skin] XML Parse Error: '%s' in '%s'!" % (err, filename))
					data = content[line - 1].replace("\t", " ").rstrip()
					print("[Skin] XML Parse Error: '%s'" % data)
					print("[Skin] XML Parse Error: '%s^%s'" % ("-" * column, " " * (len(data) - column - 1)))
				except Exception as err:
					print("[Skin] Error: Unable to parse skin data in '%s' - '%s'!" % (filename, err))
		except (IOError, OSError) as err:
			if err.errno == errno.ENOENT:
				print("[Skin] Warning: Skin file '%s' does not exist!" % filename)
			else:
				print("[Skin] Error %d: Opening skin file '%s'! (%s)" % (err.errno, filename, err.strerror))
		except Exception as err:
			print("[Skin] Error: Unexpected error opening skin file '%s'! (%s)" % (filename, err))
	finally:
		if spinner_suspended:
			try:
				setSpinnerOnOff(1)
			except Exception:
				pass
	return False


def reloadSkins():
	global domScreens, colors, gradients, fonts, menus, menuicons, parameters, screens, setups, switchPixmap
	domScreens.clear()
	colors = {
		"key_back": gRGB(0x00313131),
		"key_blue": gRGB(0x0018188b),
		"key_green": gRGB(0x001f771f),
		"key_red": gRGB(0x009f1313),
		"key_text": gRGB(0x00ffffff),
		"key_yellow": gRGB(0x00a08500)
	}
	gradients.clear()
	fonts = {
		"Body": BodyFont
	}
	menus.clear()
	menuicons.clear()
	parameters.clear()
	screens.clear()
	setups.clear()
	switchPixmap.clear()
	InitSkins()


def addCallback(callback):
	if callback not in onLoadCallbacks:
		onLoadCallbacks.append(callback)


def removeCallback(callback):
	if callback in onLoadCallbacks:
		onLoadCallbacks.remove(callback)


class SkinError(Exception):
	def __init__(self, message):
		self.msg = message

	def __str__(self):
		return "[Skin] {%s}: %s!  Please contact the skin's author!" % (config.skin.primary_skin.value, self.msg)


def parseCoordinate(s, e, size=0, font=None, scale=(1, 1)):
	orig = s = s.strip()
	if s.isdigit():
		val = int(s)
	elif s == "center":
		return 0 if not size else (e - size) // 2
	elif s == "e":
		return e
	elif s == "*":
		return None
	else:
		if scale[0] != scale[1]:
			e *= scale[1] / scale[0]
			size *= scale[1] / scale[0]
		if font is None and ("w" in s or "h" in s):
			print("[Skin] Error: 'w' or 'h' is being used in a field where neither is valid. Input string: '%s'" % orig)
			return 0
		if "center" in s:
			center = (e - size) / 2
		if "c" in s:
			c = e / 2
		if "w" in s:
			s = s.replace("w", "*w")
			w = float(fonts[font][3] * scale[1] / scale[0] if font in fonts else 0)
		if "h" in s:
			s = s.replace("h", "*h")
			h = float(fonts[font][2] * scale[1] / scale[0] if font in fonts else 0)
		if "%" in s:
			s = s.replace("%", "*e / 100")
		if "f" in s:
			f = getSkinFactor() if scale[0] == scale[1] else 1
		try:
			val = eval(s)
		except Exception as err:
			print("[Skin] %s '%s': Coordinate '%s', processed to '%s', cannot be evaluated!" % (type(err).__name__, err, orig, s))
			val = 0
	return int(val * scale[0] / scale[1] if scale[0] != scale[1] else val)


def getParentSize(object, desktop):
	if object:
		parent = object.getParent()
		if parent and parent.size().isEmpty():
			parent = parent.getParent()
		if parent:
			return parent.size()
		elif desktop:
			return desktop.size()
	return eSize()


def parseValuePair(s, scale, object=None, desktop=None, size=None):
	x, y = s.split(",")
	parentsize = eSize()
	if object and ("c" in x or "c" in y or "e" in x or "e" in y or "%" in x or "%" in y):
		parentsize = getParentSize(object, desktop)
	xval = parseCoordinate(x, parentsize.width(), size and size.width() or 0)
	yval = parseCoordinate(y, parentsize.height(), size and size.height() or 0)
	return (xval * scale[0][0] // scale[0][1], yval * scale[1][0] // scale[1][1])


def parsePosition(s, scale, object=None, desktop=None, size=None):
	return ePoint(*parseValuePair(s, scale, object, desktop, size))

def parseRadius(value):
	data = [x.strip() for x in value.split(";")]
	if len(data) == 2:
		edges = [x.strip() for x in data[1].split(",")]
		edgesMask = {
			"topLeft": eWidget.RADIUS_TOP_LEFT,
			"topRight": eWidget.RADIUS_TOP_RIGHT,
			"top": eWidget.RADIUS_TOP,
			"bottomLeft": eWidget.RADIUS_BOTTOM_LEFT,
			"bottomRight": eWidget.RADIUS_BOTTOM_RIGHT,
			"bottom": eWidget.RADIUS_BOTTOM,
			"left": eWidget.RADIUS_LEFT,
			"right": eWidget.RADIUS_RIGHT,
		}
		edgeValue = 0
		for e in edges:
			edgeValue += edgesMask.get(e, 0)
		return int(data[0]), edgeValue
	else:
		return int(data[0]), eWidget.RADIUS_ALL

def parseSize(s, scale, object=None, desktop=None):
	return eSize(*[max(0, x) for x in parseValuePair(s, scale, object, desktop)])


def parseFont(s, scale=((1, 1), (1, 1))):
	if ";" in s:
		name, size = s.split(";")
		orig = size
		try:
			size = int(size)
		except ValueError:
			try:
				size = size.replace("f", str(getSkinFactor()))
				size = int(eval(size))
			except Exception as err:
				print("[Skin] %s '%s': font size formula '%s', processed to '%s', cannot be evaluated!" % (type(err).__name__, err, orig, s))
				size = 0
	else:
		name = s
		size = 0
	try:
		f = fonts[name]
		name = f[0]
		size = f[1] if size == 0 else size
	except KeyError:
		if name not in getFontFaces():
			f = fonts["Body"]
			print("[Skin] Error: Font '%s' (in '%s') is not defined!  Using 'Body' font ('%s') instead." % (name, s, f[0]))
			name = f[0]
			size = f[1] if size == 0 else size
	return gFont(name, size * scale[0][0] // scale[0][1])


def parseColor(s):
	if s[0] != "#":
		if s in colors:
			return colors[s]
		raise SkinError("Color '%s' must be #aarrggbb or valid named color" % s)
	return gRGB(int(s[1:], 0x10))


def parseGradient(value):
	def resolveColor(v):
		if v and v[0] == "#" and len(v) in (9, 7):
			try:
				return gRGB(int(v[1:], 0x10))
			except Exception:
				return gRGB(0x00000000)
		if v in colors:
			return colors[v]
		return gRGB(0x00000000)

	value = gradients.get(value, value)
	data = [x.strip() for x in value.split(",")]

	gradientColors = [gRGB(0x00000000), gRGB(0x00000000), gRGB(0x00000000)]
	consumed = 0

	for i, color in enumerate(data):
		if i > 2:
			break
		if (color and color[0] == "#" and len(color) in (9, 7)) or color in colors:
			gradientColors[i] = resolveColor(color)
			consumed = i + 1
		else:
			break

	# alphaBlend MUST be a Python bool - SWIG-typed setBackgroundGradient() /
	# setForegroundGradient() / setGradient() reject int for the alphablend
	# argument with "TypeError: argument N of type 'bool'".
	if consumed < 2:
		return (gRGB(0x00000000), gRGB(0x00000000), gRGB(0x00000000), eWidget.GRADIENT_VERTICAL, False)

	if consumed == 2:
		gradientColors[2] = gradientColors[1]

	remaining = data[consumed:]
	direction = eWidget.GRADIENT_VERTICAL
	alphaBlend = False

	if remaining:
		direction = {
			"horizontal": eWidget.GRADIENT_HORIZONTAL,
			"vertical": eWidget.GRADIENT_VERTICAL
		}.get(remaining[0].lower(), eWidget.GRADIENT_VERTICAL)

		if len(remaining) > 1:
			alphaBlend = True if parseBoolean("alphablend", remaining[1]) else False

	return (gradientColors[0], gradientColors[1], gradientColors[2], direction, alphaBlend)


def parseBoolean(attribute, value):
	return value.lower() in ("1", attribute, "enabled", "on", "true", "yes")

def parseParameter(s):
	if s[0] == "*":
		return s[1:]
	elif s[0] == "#":
		return int(s[1:], 16)
	elif s[:2] == "0x":
		return int(s, 16)
	elif "." in s:
		return float(s)
	elif s in colors:
		return colors[s].argb()
	elif s.find(";") != -1:
		font, size = [x.strip() for x in s.split(";", 1)]
		return [font, parseScale(size)]
	else:
		return parseScale(s)


def parseScale(s):
	orig = s
	try:
		val = int(s)
	except ValueError:
		f = getSkinFactor()
		try:
			val = int(eval(s))
		except Exception as err:
			print("[Skin] parseScale: %s '%s': formula '%s' cannot be evaluated!" % (type(err).__name__, err, s))
			val = 0
	return val


def mergeScale(s1, s2):
	return ((s1[0][0] * s2[0][0], s1[0][1] * s2[0][1]), (s1[1][0] * s2[1][0], s1[1][1] * s2[1][1]))


def loadPixmap(path, desktop, width=0, height=0):
	option = path.find("#")
	if option != -1:
		path = path[:option]
	if not rc_model.rcIsDefault() and basename(path) in ("rc.png", "rc0.png", "rc1.png", "rc2.png", "oldrc.png"):
		path = rc_model.getRcImg()

	pixmap = LoadPixmap(path, desktop, None, width, height)
	if pixmap is not None:
		return pixmap

	if not path.startswith("/"):
		for scope in (SCOPE_CURRENT_SKIN, SCOPE_SKIN, SCOPE_CONFIG, SCOPE_CURRENT_LCDSKIN):
			try:
				resolved = resolveFilename(scope, path)
			except Exception:
				continue
			if isfile(resolved):
				pixmap = LoadPixmap(resolved, desktop, None, width, height)
				if pixmap is not None:
					return pixmap

	raise SkinError("Pixmap file '%s' not found" % path)


def collectAttributes(skinAttributes, node, context, skinPath=None, ignore=(), filenames=frozenset(("pixmap", "pointer", "seek_pointer", "backgroundPixmap", "selectionPixmap", "selectionPixmapLarge", "sliderPixmap", "scrollbarSliderPicture", "scrollbarbackgroundPixmap", "scrollbarBackgroundPicture"))):
	size = None
	pos = None
	font = None
	for attrib, value in node.items():
		if attrib not in ignore:
			if attrib in filenames:
				value = resolveFilename(SCOPE_CURRENT_SKIN, value, path_prefix=skinPath)
			if attrib == "size":
				size = value
			elif attrib == "position":
				pos = value
			elif attrib == "font":
				font = value
				skinAttributes.append((attrib, font))
			else:
				skinAttributes.append((attrib, value))
	if pos is not None:
		pos, size = context.parse(pos, size, font)
		skinAttributes.append(("position", pos))
	if size is not None:
		skinAttributes.append(("size", size))


class AttributeParser:
	def __init__(self, guiObject, desktop, scale=((1, 1), (1, 1))):
		self.guiObject = guiObject
		self.desktop = desktop
		self.scaleTuple = scale

	def applyOne(self, attrib, value):
		try:
			getattr(self, attrib)(value)
		except AttributeError:
			print("[Skin] Attribute '%s' (with value of '%s') in object of type '%s' is not implemented!" % (attrib, value, self.guiObject.__class__.__name__))
		except SkinError as err:
			print("[Skin] Error: %s" % str(err))
		except Exception:
			print("[Skin] Attribute '%s' with wrong (or unknown) value '%s' in object of type '%s'!" % (attrib, value, self.guiObject.__class__.__name__))

	def applyAll(self, attrs):
		attrs.sort(key=lambda a: {"pixmap": 1, "scale": -1}.get(a[0], 0))
		if attrs and attrs[-1][0] == "pixmap" and (self.scaleTuple[0][0] != self.scaleTuple[0][1] or self.scaleTuple[1][0] != self.scaleTuple[1][1]) and attrs[0][0] != "scale":
			attrs.insert(0, ("scale", "1"))
		for attrib, value in attrs:
			self.applyOne(attrib, value)

	def applyHorizontalScale(self, value):
		return int(value) if self.scaleTuple[0][0] == self.scaleTuple[0][1] else int(int(value) * self.scaleTuple[0][0] / self.scaleTuple[0][1])

	def applyVerticalScale(self, value):
		return int(value) if self.scaleTuple[1][0] == self.scaleTuple[1][1] else int(int(value) * self.scaleTuple[1][0] / self.scaleTuple[1][1])

	def conditional(self, value):
		pass

	def objectTypes(self, value):
		pass

	def position(self, value):
		self.guiObject.move(ePoint(*value) if isinstance(value, tuple) else parsePosition(value, self.scaleTuple, self.guiObject, self.desktop, self.guiObject.csize()))

	def size(self, value):
		self.guiObject.resize(eSize(*value) if isinstance(value, tuple) else parseSize(value, self.scaleTuple, self.guiObject, self.desktop))

	def animationPaused(self, value):
		pass

	def title(self, value):
		self.guiObject.setTitle(_(value))

	def text(self, value):
		self.guiObject.setText(_(value))

	def font(self, value):
		self.guiObject.setFont(parseFont(value, self.scaleTuple))

	def secondfont(self, value):
		self.guiObject.setSecondFont(parseFont(value, self.scaleTuple))

	def widgetBorderColor(self, value):
		self.guiObject.setWidgetBorderColor(parseColor(value))

	def widgetBorderWidth(self, value):
		self.guiObject.setWidgetBorderWidth(self.applyVerticalScale(parseScale(value)))

	def zPosition(self, value):
		self.guiObject.setZPosition(int(value))

	def itemHeight(self, value):
		self.guiObject.setItemHeight(self.applyVerticalScale(parseScale(value)))

	def itemWidth(self, value):
		self.guiObject.setItemWidth(self.applyHorizontalScale(parseScale(value)))

	def itemCornerRadius(self, value):
		radius, edgeValue = parseRadius(value)
		self.guiObject.setItemCornerRadius(radius, edgeValue)

	def itemCornerRadiusSelected(self, value):
		radius, edgeValue = parseRadius(value)
		self.guiObject.setItemCornerRadiusSelected(radius, edgeValue)

	def pixmap(self, value):
		if value.endswith(".svg"):
			self.guiObject.setAlphatest(BT_ALPHABLEND)
		self.guiObject.setPixmap(loadPixmap(value, self.desktop, self.guiObject.size().width(), self.guiObject.size().height()))

	def backgroundPixmap(self, value):
		self.guiObject.setBackgroundPicture(loadPixmap(value, self.desktop))

	def selectionPixmap(self, value):
		self.guiObject.setSelectionPicture(loadPixmap(value, self.desktop))

	def selectionPixmapLarge(self, value):
		self.guiObject.setSelectionPictureLarge(loadPixmap(value, self.desktop))

	def sliderPixmap(self, value):
		self.guiObject.setSliderPicture(loadPixmap(value, self.desktop))

	def scrollbarbackgroundPixmap(self, value):
		self.guiObject.setScrollbarBackgroundPicture(loadPixmap(value, self.desktop))

	def scrollbarSliderPicture(self, value):
		self.guiObject.setSliderPicture(loadPixmap(value, self.desktop))

	def scrollbarBackgroundPicture(self, value):
		self.guiObject.setScrollbarBackgroundPicture(loadPixmap(value, self.desktop))

	def alphatest(self, value):
		# 'alphatest' only makes sense on widgets that actually handle it (e.g.
		# ePixmap). Skins sometimes set it on containers by mistake - skip
		# quietly instead of printing a spurious error for every such widget.
		if not hasattr(self.guiObject, "setAlphatest"):
			return
		try:
			self.guiObject.setAlphatest({
				"on": BT_ALPHATEST,
				"off": 0,
				"blend": BT_ALPHABLEND
			}[value])
		except KeyError:
			print("[Skin] Error: Invalid alphatest '%s'!  Must be one of 'on', 'off' or 'blend'." % value)

	def scale(self, value):
		self.guiObject.setScale(int(parseBoolean("scale", value)))

	def scaleFlags(self, value):
		base = BT_SCALE | BT_KEEP_ASPECT_RATIO
		try:
			self.guiObject.setPixmapScale({
				"none": 0,
				"scale": BT_SCALE,
				"scaleKeepAspect": base,
				"scaleLeftTop": base | BT_HALIGN_LEFT | BT_VALIGN_TOP,
				"scaleLeftCenter": base | BT_HALIGN_LEFT | BT_VALIGN_CENTER,
				"scaleLeftBottom": base | BT_HALIGN_LEFT | BT_VALIGN_BOTTOM,
				"scaleCenterTop": base | BT_HALIGN_CENTER | BT_VALIGN_TOP,
				"scaleCenter": base | BT_HALIGN_CENTER | BT_VALIGN_CENTER,
				"scaleCenterBottom": base | BT_HALIGN_CENTER | BT_VALIGN_BOTTOM,
				"scaleRightTop": base | BT_HALIGN_RIGHT | BT_VALIGN_TOP,
				"scaleRightCenter": base | BT_HALIGN_RIGHT | BT_VALIGN_CENTER,
				"scaleRightBottom": base | BT_HALIGN_RIGHT | BT_VALIGN_BOTTOM,
				"moveLeftTop": BT_HALIGN_LEFT | BT_VALIGN_TOP,
				"moveLeftCenter": BT_HALIGN_LEFT | BT_VALIGN_CENTER,
				"moveLeftBottom": BT_HALIGN_LEFT | BT_VALIGN_BOTTOM,
				"moveCenterTop": BT_HALIGN_CENTER | BT_VALIGN_TOP,
				"moveCenter": BT_HALIGN_CENTER | BT_VALIGN_CENTER,
				"moveCenterBottom": BT_HALIGN_CENTER | BT_VALIGN_BOTTOM,
				"moveRightTop": BT_HALIGN_RIGHT | BT_VALIGN_TOP,
				"moveRightCenter": BT_HALIGN_RIGHT | BT_VALIGN_CENTER,
				"moveRightBottom": BT_HALIGN_RIGHT | BT_VALIGN_BOTTOM
			}[value])
		except KeyError:
			print("[Skin] Error: Invalid scale '%s'!  Must be one of 'none', 'scale', 'scaleKeepAspect', 'scaleLeftTop', 'scaleLeftCenter', 'scaleLeftBotton', 'scaleCenterTop', 'scaleCenter', 'scaleCenterBotton', 'scaleRightTop', 'scaleRightCenter', 'scaleRightBottom', 'moveLeftTop', 'moveLeftCenter', 'moveLeftBotton', 'moveCenterTop', 'moveCenter', 'moveCenterBottom', 'moveRightTop', 'moveRightCenter', 'moveRightBottom' ('Center'/'Centre'/'Middle' are equivalent)." % value)

	def orientation(self, value):
		try:
			self.guiObject.setOrientation(*{
				"orVertical": (self.guiObject.orVertical, False),
				"orTopToBottom": (self.guiObject.orVertical, False),
				"orBottomToTop": (self.guiObject.orVertical, True),
				"orHorizontal": (self.guiObject.orHorizontal, False),
				"orLeftToRight": (self.guiObject.orHorizontal, False),
				"orRightToLeft": (self.guiObject.orHorizontal, True)
			}[value])
		except KeyError:
			print("[Skin] Error: Invalid orientation '%s'!  Must be one of 'orVertical', 'orTopToBottom', 'orBottomToTop', 'orHorizontal', 'orLeftToRight' or 'orRightToLeft'." % value)

	def listOrientation(self, value):  # Used by eListbox.
		# eListbox enum in OpenPLi: orHorizontal=0, orVertical=1, orGrid=2.
		# Do NOT copy the OpenATV numeric values (OpenATV uses orVertical=1, orHorizontal=2, orGrid=3).
		options = {
			"orVertical": self.guiObject.orVertical,
			"vertical": self.guiObject.orVertical,
			"orTopToBottom": self.guiObject.orVertical,
			"orHorizontal": self.guiObject.orHorizontal,
			"horizontal": self.guiObject.orHorizontal,
			"orLeftToRight": self.guiObject.orHorizontal,
			"orGrid": self.guiObject.orGrid,
			"grid": self.guiObject.orGrid,
		}
		if value in options:
			self.guiObject.setOrientation(options[value])
			return
		print("[Skin] Error: Invalid listOrientation '%s'!  Must be one of %s.  Using 'orVertical'." % (value, ", ".join("'%s'" % k for k in options)))
		self.guiObject.setOrientation(self.guiObject.orVertical)

	def valign(self, value):
		if hasattr(self.guiObject, "setVAlign"):
			align_map = {"top": 0, "center": 1, "bottom": 2}
			if value in align_map:
				try:
					self.guiObject.setVAlign(align_map[value])
					return
				except Exception:
					pass
		print("[Skin] Attribute 'valign' with value '%s' not supported by %s" % (value, self.guiObject.__class__.__name__))

	def halign(self, value):
		if hasattr(self.guiObject, "setHAlign"):
			align_map = {"left": 0, "center": 1, "right": 2, "block": 3}
			if value in align_map:
				try:
					self.guiObject.setHAlign(align_map[value])
					return
				except Exception:
					pass
		print("[Skin] Attribute 'halign' with value '%s' not supported by %s" % (value, self.guiObject.__class__.__name__))

	def textOffset(self, value):
		if hasattr(self.guiObject, "setTextOffset"):
			x, y = value.split(",")
			self.guiObject.setTextOffset(ePoint(int(x), int(y)))

	def padding(self, value):
		if hasattr(self.guiObject, "setPadding"):
			l, t, r, b = [int(x.strip()) for x in value.split(",")]
			self.guiObject.setPadding(eRect(l, t, r, b))

	def render(self, value):
		pass

	def flags(self, value):
		flags = value.split(",")
		for f in flags:
			try:
				fv = eWindow.__dict__[f]
				self.guiObject.setFlag(fv)
			except KeyError:
				print("[Skin] Error: Invalid flag '%s'!" % f)

	def backgroundColor(self, value):
		if "," in value or value in gradients:
			start, mid, end, direction, blend = parseGradient(value)
			# eLabel inherits setBackgroundGradient() from eWidget but does not
			# render a gradient - it is a flat label.  Use the flat start
			# colour so the skin's intended look is preserved.
			if isinstance(self.guiObject, eLabel) or not hasattr(self.guiObject, "setBackgroundGradient"):
				self.guiObject.setBackgroundColor(start)
			else:
				self.guiObject.setBackgroundGradient(start, mid, end, direction, bool(blend))
		else:
			self.guiObject.setBackgroundColor(parseColor(value))

	def foregroundColor(self, value):
		if "," in value or value in gradients:
			start, mid, end, direction, blend = parseGradient(value)
			if isinstance(self.guiObject, eLabel) or not hasattr(self.guiObject, "setForegroundGradient"):
				self.guiObject.setForegroundColor(start)
			else:
				self.guiObject.setForegroundGradient(start, mid, end, direction, bool(blend))
		else:
			self.guiObject.setForegroundColor(parseColor(value))

	def backgroundColorGradient(self, value):
		start, mid, end, direction, blend = parseGradient(value)
		self.guiObject.setBackgroundGradient(start, mid, end, direction, bool(blend))

	def itemGradient(self, value):
		start, mid, end, direction, blend = parseGradient(value)
		self.guiObject.setItemGradient(start, mid, end, direction, bool(blend))

	def itemGradientSelected(self, value):
		start, mid, end, direction, blend = parseGradient(value)
		self.guiObject.setItemGradientSelected(start, mid, end, direction, bool(blend))

	def foregroundColorGradient(self, value):
		start, mid, end, direction, blend = parseGradient(value)
		self.guiObject.setForegroundGradient(start, mid, end, direction, bool(blend))

	def windowStyleColorGradient(self, value):
		what, spec = value.split(":", 1)
		what = what.strip()
		start, mid, end, direction, blend = parseGradient(spec.strip())
		self.guiObject.setGradient(getattr(self.guiObject, "col" + what), [start, mid, end], direction, bool(blend))

	def backgroundColorSelected(self, value):
		self.guiObject.setBackgroundColorSelected(parseColor(value))

	def foregroundColorSelected(self, value):
		self.guiObject.setForegroundColorSelected(parseColor(value))

	def foregroundNotCrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value))

	def backgroundNotCrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value))

	def foregroundCrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value))

	def backgroundCrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value))

	def foregroundEncrypted(self, value):
		self.guiObject.setForegroundColor(parseColor(value))

	def backgroundEncrypted(self, value):
		self.guiObject.setBackgroundColor(parseColor(value))

	def shadowColor(self, value):
		self.guiObject.setShadowColor(parseColor(value))

	def selectionDisabled(self, value):
		self.guiObject.setSelectionEnable(int(not parseBoolean("selectiondisabled", value)))

	def transparent(self, value):
		self.guiObject.setTransparent(int(parseBoolean("transparent", value)))

	def borderColor(self, value):
		self.guiObject.setBorderColor(parseColor(value))

	def borderWidth(self, value):
		self.guiObject.setBorderWidth(self.applyVerticalScale(parseScale(value)))

	def cornerRadius(self, value):
		radius, edgeValue = parseRadius(value)
		self.guiObject.setCornerRadius(radius, edgeValue)

	def scrollbarSliderBorderWidth(self, value):
		self.guiObject.setScrollbarBorderWidth(self.applyHorizontalScale(parseScale(value)))

	def scrollbarWidth(self, value):
		self.guiObject.setScrollbarWidth(self.applyHorizontalScale(parseScale(value)))

	def scrollbarSliderBorderColor(self, value):
		if hasattr(self.guiObject, "setScrollbarBorderColor"):
			self.guiObject.setScrollbarBorderColor(parseColor(value))
		else:
			self.guiObject.setSliderBorderColor(parseColor(value))

	def scrollbarSliderForegroundColor(self, value):
		if hasattr(self.guiObject, "setScrollbarForegroundColor"):
			self.guiObject.setScrollbarForegroundColor(parseColor(value))
		else:
			self.guiObject.setSliderForegroundColor(parseColor(value))

	def scrollbarMode(self, value):
		try:
			self.guiObject.setScrollbarMode({
				"showOnDemand": self.guiObject.showOnDemand,
				"showAlways": self.guiObject.showAlways,
				"showNever": self.guiObject.showNever,
				"showLeft": self.guiObject.showLeft,
				"showTop": self.guiObject.showTop
			}[value])
		except KeyError:
			print("[Skin] Error: Invalid scrollbarMode '%s'!  Must be one of 'showOnDemand', 'showAlways', 'showNever', 'showLeft' or 'showTop'." % value)

	def enableWrapAround(self, value):
		self.guiObject.setWrapAround(parseBoolean("enablewraparound", value))

	def pointer(self, value):
		(name, pos) = value.split(":")
		pos = parsePosition(pos, self.scaleTuple)
		ptr = loadPixmap(name, self.desktop)
		self.guiObject.setPointer(0, ptr, pos)

	def seek_pointer(self, value):
		(name, pos) = value.split(":")
		pos = parsePosition(pos, self.scaleTuple)
		ptr = loadPixmap(name, self.desktop)
		self.guiObject.setPointer(1, ptr, pos)

	def hidePointerOnZeroLength(self, value):
		self.guiObject.setHidePointerOnZeroLength(int(parseBoolean("hidePointerOnZeroLength", value)))

	def shadowOffset(self, value):
		self.guiObject.setShadowOffset(parsePosition(value, self.scaleTuple))

	def noWrap(self, value):
		self.guiObject.setNoWrap(int(parseBoolean("nowrap", value)))

	def split(self, value):
		pass

	def colposition(self, value):
		pass

	def dividechar(self, value):
		pass

	def resolution(self, value):
		pass


def applySingleAttribute(guiObject, desktop, attrib, value, scale=((1, 1), (1, 1))):
	AttributeParser(guiObject, desktop, scale).applyOne(attrib, value)


def applyAllAttributes(guiObject, desktop, attributes, scale):
	AttributeParser(guiObject, desktop, scale).applyAll(attributes)


def reloadWindowStyles():
	for screenID in windowStyles:
		desktop, screenID, domSkin, pathSkin, scope = windowStyles[screenID]
		loadSingleSkinData(desktop, screenID, domSkin, pathSkin, scope)


def loadSingleSkinData(desktop, screenID, domSkin, pathSkin, scope=SCOPE_CURRENT_SKIN):
	assert domSkin.tag == "skin", "root element in skin must be 'skin'!"
	global colors, gradients, fonts, menus, parameters, screens, setups, switchPixmap
	for tag in domSkin.findall("output"):
		scrnID = int(tag.attrib.get("id", GUI_SKIN_ID))
		if scrnID == GUI_SKIN_ID:
			for res in tag.findall("resolution"):
				xres = res.attrib.get("xres")
				xres = int(xres) if xres else 720
				yres = res.attrib.get("yres")
				yres = int(yres) if yres else 576
				bpp = res.attrib.get("bpp")
				bpp = int(bpp) if bpp else 32
				from enigma import gMainDC
				gMainDC.getInstance().setResolution(xres, yres)
				desktop.resize(eSize(xres, yres))
				if bpp != 32:
					pass

				fonts["Body"] = applySkinFactor(*BodyFont)

				fonts["Dreamexplorer"] = fonts["Body"]
				fonts["ExpandableList"] = fonts["Body"]
				fonts["ImsSelectionList"] = applySkinFactor("Regular", 22, 30)
				fonts["PartnerBoxBouquetList0"] = applySkinFactor("Regular", 20, 30)
				fonts["PartnerBoxBouquetList1"] = applySkinFactor("Regular", 18)
				fonts["PartnerBoxChannelList0"] = applySkinFactor("Regular", 20, 70)
				fonts["PartnerBoxChannelList1"] = applySkinFactor("Regular", 18)
				fonts["PartnerBoxChannelEPGList0"] = applySkinFactor("Regular", 22, 30)
				fonts["PartnerBoxE2TimerMenu0"] = applySkinFactor("Regular", 20, 70)
				fonts["PartnerBoxE2TimerMenu1"] = applySkinFactor("Regular", 18)
				fonts["PartnerBoxEntryList0"] = applySkinFactor("Regular", 20, 30)
				fonts["PartnerBoxEntryList1"] = applySkinFactor("Regular", 18)

				parameters["AutotimerListChannels"] = applySkinFactor(2, 40, 3, 21)
				parameters["AutotimerListDays"] = applySkinFactor(1, 26, 3, 17)
				parameters["AutotimerListHasTimespan"] = applySkinFactor(103, 3, 100, 17)
				parameters["AutotimerListIcon"] = applySkinFactor(2, -1, 24, 24)
				parameters["AutotimerListRectypeicon"] = applySkinFactor(26, 3, 20, 20)
				parameters["AutotimerListTimerName"] = applySkinFactor(50, 3, 18, 21)
				parameters["AutotimerListTimespan"] = applySkinFactor(2, 26, 3, 17)
				parameters["DreamexplorerIcon"] = applySkinFactor(12, 3, 20, 20)
				parameters["DreamexplorerName"] = applySkinFactor(40, 2, 1000, 22)
				parameters["ExpandableListCategory"] = applySkinFactor(45, 0, 655, 25)
				parameters["ExpandableListIcon"] = applySkinFactor(5, 0, 30, 25)
				parameters["ExpandableListItem"] = applySkinFactor(80, 3, 620, 25)
				parameters["ExpandableListLock"] = applySkinFactor(45, 1, 25, 24)
				parameters["PartnerBoxBouquetListName"] = applySkinFactor(0, 0, 30)
				parameters["PartnerBoxChannelListName"] = applySkinFactor(0, 0, 30)
				parameters["PartnerBoxChannelListTime"] = applySkinFactor(0, 50, 150, 20)
				parameters["PartnerBoxChannelListTitle"] = applySkinFactor(0, 30, 20)
				parameters["PartnerBoxE1TimerState"] = applySkinFactor(170, 50, 170, 20)
				parameters["PartnerBoxE1TimerTime"] = applySkinFactor(0, 50, 170, 20)
				parameters["PartnerBoxE2TimerIcon"] = applySkinFactor(510, 5, 20, 20)
				parameters["PartnerBoxE2TimerIconRepeat"] = applySkinFactor(510, 30, 20, 20)
				parameters["PartnerBoxE2TimerState"] = applySkinFactor(150, 50, 150, 22)
				parameters["PartnerBoxE2TimerTime"] = applySkinFactor(0, 50, 150, 20)
				parameters["PartnerBoxEntryListName"] = applySkinFactor(5, 0, 150, 25)
				parameters["PartnerBoxEntryListIP"] = applySkinFactor(120, 0, 150, 25)
				parameters["PartnerBoxEntryListPort"] = applySkinFactor(270, 0, 100, 25)
				parameters["PartnerBoxEntryListType"] = applySkinFactor(410, 0, 100, 25)
				parameters["PartnerBoxTimerName"] = applySkinFactor(0, 30, 20)
				parameters["PartnerBoxTimerServicename"] = applySkinFactor(0, 0, 30)
				parameters["SHOUTcastListItem"] = applySkinFactor(20, 18, 22, 69, 20, 23, 43, 22)

	for tag in domSkin.findall("include"):
		filename = tag.attrib.get("filename")
		conditional = not (c := tag.attrib.get("conditional")) or eval(c)
		if filename and conditional:
			resolved = resolveFilename(scope, filename, path_prefix=pathSkin)
			if isfile(resolved):
				loadSkin(resolved, scope=scope, desktop=desktop, screenID=screenID)
			else:
				raise SkinError("Included file '%s' not found" % filename)
	for tag in domSkin.findall("switchpixmap"):
		for pixmap in tag.findall("pixmap"):
			name = pixmap.attrib.get("name")
			if not name:
				raise SkinError("Pixmap needs name attribute")
			filename = pixmap.attrib.get("filename")
			if not filename:
				raise SkinError("Pixmap needs filename attribute")
			resolved = resolveFilename(scope, filename, path_prefix=pathSkin)
			if isfile(resolved):
				switchPixmap[name] = LoadPixmap(resolved, cached=True)
			else:
				raise SkinError("The switchpixmap pixmap filename='%s' (%s) not found" % (filename, resolved))
	for tag in domSkin.findall("colors"):
		for color in tag.findall("color"):
			name = color.attrib.get("name")
			color = color.attrib.get("value")
			if name and color:
				if "," in color:
					gradients[name] = color
				else:
					colors[name] = parseColor(color)
			else:
				raise SkinError("Tag 'color' needs a name and color, got name='%s' and color='%s'" % (name, color))
	for tag in domSkin.findall("fonts"):
		for font in tag.findall("font"):
			filename = font.attrib.get("filename", "<NONAME>")
			name = font.attrib.get("name", "Regular")
			scale = font.attrib.get("scale")
			scale = int(scale) if scale else 100
			isReplacement = font.attrib.get("replacement") and True or False
			render = font.attrib.get("render")
			if render:
				render = int(render)
			else:
				render = 0
			filename = resolveFilename(SCOPE_FONTS, filename, path_prefix=pathSkin)
			if isfile(filename):
				addFont(filename, name, scale, isReplacement, render)
			else:
				raise SkinError("Font file '%s' not found" % filename)
		fallbackFont = resolveFilename(SCOPE_FONTS, "fallback.font", path_prefix=pathSkin)
		if isfile(fallbackFont):
			addFont(fallbackFont, "Fallback", 100, -1, 0)
		for alias in tag.findall("alias"):
			try:
				name = alias.attrib.get("name")
				font = alias.attrib.get("font")
				size = parseScale(alias.attrib.get("size"))
				height = parseScale(alias.attrib.get("height", size))
				width = parseScale(alias.attrib.get("width", size))
				fonts[name] = (font, size, height, width)
			except Exception as err:
				raise SkinError("Bad font alias: '%s'" % str(err))
	for tag in domSkin.findall("parameters"):
		for parameter in tag.findall("parameter"):
			try:
				name = parameter.attrib.get("name")
				value = parameter.attrib.get("value")
				parameters[name] = list(map(parseParameter, [x.strip() for x in value.split(",")])) if "," in value else parseParameter(value)
			except Exception as err:
				raise SkinError("Bad parameter: '%s'" % str(err))
	for tag in domSkin.findall("menus"):
		for menu in tag.findall("menu"):
			key = menu.attrib.get("key")
			image = menu.attrib.get("image")
			if key and image:
				menus[key] = image
			else:
				raise SkinError("Tag menu needs key and image, got key='%s' and image='%s'" % (key, image))
	for tag in domSkin.findall("menuicons"):
		for menuicon in tag.findall("menuicon"):
			key = menuicon.attrib.get("key")
			image = menuicon.attrib.get("image")
			if key and image:
				menuicons[key] = image
			else:
				raise SkinError("Tag 'menuicon' needs key and image, got key='%s' and image='%s'" % (key, image))
	for tag in domSkin.findall("screens"):
		for screen in tag.findall("screen"):
			key = screen.attrib.get("key")
			image = screen.attrib.get("image")
			if key and image:
				screens[key] = image
			else:
				raise SkinError("Tag 'screen' needs key and image, got key='%s' and image='%s'" % (key, image))
	for tag in domSkin.findall("setups"):
		for setup in tag.findall("setup"):
			key = setup.attrib.get("key")
			image = setup.attrib.get("image")
			if key and image:
				setups[key] = image
			else:
				raise SkinError("Tag setup needs key and image, got key='%s' and image='%s'" % (key, image))
	for tag in domSkin.findall("subtitles"):
		from enigma import eSubtitleWidget
		scale = ((1, 1), (1, 1))
		for substyle in tag.findall("sub"):
			font = parseFont(substyle.attrib.get("font"), scale)
			col = substyle.attrib.get("foregroundColor")
			if col:
				foregroundColor = parseColor(col)
				haveColor = 1
			else:
				foregroundColor = gRGB(0xFFFFFF)
				haveColor = 0
			col = substyle.attrib.get("borderColor")
			if col:
				borderColor = parseColor(col)
			else:
				borderColor = gRGB(0)
			borderwidth = substyle.attrib.get("borderWidth")
			if borderwidth is None:
				borderWidth = 3
			else:
				borderWidth = int(borderwidth)
			face = eSubtitleWidget.__dict__[substyle.attrib.get("name")]
			eSubtitleWidget.setFontStyle(face, font, haveColor, foregroundColor, borderColor, borderWidth)
	for tag in domSkin.findall("windowstyle"):
		style = eWindowStyleSkinned()
		scrnID = int(tag.attrib.get("id", GUI_SKIN_ID))
		font = gFont("Regular", 20)
		offset = eSize(20, 5)
		for title in tag.findall("title"):
			offset = parseSize(title.attrib.get("offset"), ((1, 1), (1, 1)))
			font = parseFont(title.attrib.get("font"), ((1, 1), (1, 1)))
		style.setTitleFont(font)
		style.setTitleOffset(offset)
		for borderset in tag.findall("borderset"):
			bsName = str(borderset.attrib.get("name"))
			for pixmap in borderset.findall("pixmap"):
				bpName = pixmap.attrib.get("pos")
				filename = pixmap.attrib.get("filename")
				if filename and bpName:
					png = loadPixmap(resolveFilename(scope, filename, path_prefix=pathSkin), desktop)
					try:
						style.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], png)
					except Exception:
						pass
		for color in tag.findall("color"):
			colorType = color.attrib.get("name")
			rawColor = color.attrib.get("color")
			try:
				flatColor = parseColor(rawColor)
			except SkinError:
				if "," in rawColor:
					flatColor = parseGradient(rawColor)[0]
				else:
					raise
			try:
				style.setColor(eWindowStyleSkinned.__dict__["col" + colorType], flatColor)
			except Exception:
				raise SkinError("Unknown color type '%s'" % colorType)
		for cg in tag.findall("colorgradient"):
			cgType = cg.attrib.get("name")
			cgValue = cg.attrib.get("value")
			if cgType and cgValue:
				start, mid, end, direction, blend = parseGradient(cgValue)
				try:
					style.setGradient(eWindowStyleSkinned.__dict__["col" + cgType], [start, mid, end], direction, bool(blend))
				except Exception as err:
					print("[Skin] Error: windowstyle colorgradient '%s' failed: %s" % (cgType, err))
			else:
				raise SkinError("Tag 'colorgradient' needs name and value, got name='%s' and value='%s'" % (cgType, cgValue))
		x = eWindowStyleManager.getInstance()
		x.setStyle(scrnID, style)
	for tag in domSkin.findall("margin"):
		scrnID = int(tag.attrib.get("id", GUI_SKIN_ID))
		r = eRect(0, 0, 0, 0)
		v = tag.attrib.get("left")
		if v:
			r.setLeft(int(v))
		v = tag.attrib.get("top")
		if v:
			r.setTop(int(v))
		v = tag.attrib.get("right")
		if v:
			r.setRight(int(v))
		v = tag.attrib.get("bottom")
		if v:
			r.setBottom(int(v))
		getDesktop(scrnID).setMargins(r)


class additionalWidget:
	def __init__(self):
		pass


class SizeTuple(tuple):
	def split(self, *args):
		return str(self[0]), str(self[1])

	def strip(self, *args):
		return "%s,%s" % self

	def __str__(self):
		return "%s,%s" % self


class SkinContext:
	def __init__(self, parent=None, pos=None, size=None, font=None):
		if parent is not None and pos is not None:
			pos, size = parent.parse(pos, size, font)
			self.x, self.y = pos
			self.w, self.h = size
			self.scale = parent.scale
		else:
			self.x = None
			self.y = None
			self.w = None
			self.h = None
			self.scale = ((1, 1), (1, 1))

	def __str__(self):
		return "Context (%s,%s)+(%s,%s)" % (self.x, self.y, self.w, self.h)

	def parse(self, pos, size, font):
		if pos == "fill":
			pos = (self.x, self.y)
			size = (self.w, self.h)
			self.w = 0
			self.h = 0
		else:
			w, h = size.split(",")
			w = parseCoordinate(w, self.w, 0, font, self.scale[0])
			h = parseCoordinate(h, self.h, 0, font, self.scale[1])
			if pos == "bottom":
				pos = (self.x, self.y + self.h - h)
				size = (self.w, h)
				self.h -= h
			elif pos == "top":
				pos = (self.x, self.y)
				size = (self.w, h)
				self.h -= h
				self.y += h
			elif pos == "left":
				pos = (self.x, self.y)
				size = (w, self.h)
				self.x += w
				self.w -= w
			elif pos == "right":
				pos = (self.x + self.w - w, self.y)
				size = (w, self.h)
				self.w -= w
			else:
				size = (w, h)
				pos = pos.split(",")
				pos = (self.x + parseCoordinate(pos[0], self.w, size[0], font, self.scale[0]), self.y + parseCoordinate(pos[1], self.h, size[1], font, self.scale[1]))
		return (SizeTuple(pos), SizeTuple(size))


class SkinContextStack(SkinContext):
	def parse(self, pos, size, font):
		if pos == "fill":
			pos = (self.x, self.y)
			size = (self.w, self.h)
		else:
			w, h = size.split(",")
			w = parseCoordinate(w, self.w, 0, font, self.scale[0])
			h = parseCoordinate(h, self.h, 0, font, self.scale[1])
			if pos == "bottom":
				pos = (self.x, self.y + self.h - h)
				size = (self.w, h)
			elif pos == "top":
				pos = (self.x, self.y)
				size = (self.w, h)
			elif pos == "left":
				pos = (self.x, self.y)
				size = (w, self.h)
			elif pos == "right":
				pos = (self.x + self.w - w, self.y)
				size = (w, self.h)
			else:
				size = (w, h)
				pos = pos.split(",")
				pos = (self.x + parseCoordinate(pos[0], self.w, size[0], font, self.scale[0]), self.y + parseCoordinate(pos[1], self.h, size[1], font, self.scale[1]))
		return (SizeTuple(pos), SizeTuple(size))


def readSkin(screen, skin, names, desktop):
	if not isinstance(names, list):
		names = [names]
	for n in names:
		myScreen, path = domScreens.get(n, (None, None))
		if myScreen is not None:
			if screen.mandatoryWidgets is None:
				screen.mandatoryWidgets = []
			else:
				widgets = findWidgets(n)
			if screen.mandatoryWidgets == [] or all(item in widgets for item in screen.mandatoryWidgets):
				name = n
				break
			else:
				print("[Skin] Warning: Skin screen '%s' rejected as it does not offer all the mandatory widgets '%s'!" % (n, ", ".join(screen.mandatoryWidgets)))
				myScreen = None
	else:
		name = "<embedded-in-%s>" % screen.__class__.__name__
	if myScreen is None:
		myScreen = getattr(screen, "parsedSkin", None)
	if myScreen is None and getattr(screen, "skin", None):
		if isinstance(screen.skin, list):
			print("[Skin] Resizable embedded skin template found in '%s'." % name)
			skin = screen.skin[0] % tuple([int(x * getSkinFactor()) for x in screen.skin[1:]])
		else:
			skin = screen.skin
		print("[Skin] Parsing embedded skin '%s'." % name)
		if isinstance(skin, tuple):
			for s in skin:
				candidate = xml.etree.ElementTree.fromstring(s)
				if candidate.tag == "screen":
					screenID = candidate.attrib.get("id", None)
					if (not screenID) or (int(screenID) == DISPLAY_SKIN_ID):
						myScreen = candidate
						break
			else:
				print("[Skin] No suitable screen found!")
		else:
			myScreen = xml.etree.ElementTree.fromstring(skin)
		if myScreen:
			screen.parsedSkin = myScreen
	if myScreen is None:
		print("[Skin] No skin to read or screen to display.")
		myScreen = screen.parsedSkin = xml.etree.ElementTree.fromstring("<screen></screen>")
	screen.skinAttributes = []
	skinPath = getattr(screen, "skin_path", path)
	context = SkinContextStack()
	s = desktop.bounds()
	context.x = s.left()
	context.y = s.top()
	context.w = s.width()
	context.h = s.height()
	resolution = tuple([int(x.strip()) for x in myScreen.attrib.get("resolution", f"{context.w},{context.h}").split(",")])
	context.scale = ((context.w, resolution[0]), (context.h, resolution[1]))
	del s
	collectAttributes(screen.skinAttributes, myScreen, context, skinPath, ignore=("name",))
	context = SkinContext(context, myScreen.attrib.get("position"), myScreen.attrib.get("size"))
	screen.additionalWidgets = []
	screen.renderer = []
	usedComponents = set()

	def processNone(widget, context):
		pass

	def processWidget(widget, context):
		wname = widget.attrib.get("name")
		wsource = widget.attrib.get("source")
		wconnection = widget.attrib.get("connection")
		wclass = widget.attrib.get("addon")
		source = None
		if wname is None and wsource is None and wclass is None:
			raise SkinError("The widget has no name, no source and no addon type specified")

		if wname:
			usedComponents.add(wname)
			try:
				attributes = screen[wname].skinAttributes = []
			except Exception:
				raise SkinError("Component with name '%s' was not found in skin of screen '%s'" % (wname, name))
			collectAttributes(attributes, widget, context, skinPath, ignore=("name",))
		elif wsource:
			while True:
				scr = screen
				path = wsource.split(".")
				while len(path) > 1:
					scr = screen.getRelatedScreen(path[0])
					if scr is None:
						raise SkinError("Specified related screen '%s' was not found in screen '%s'" % (wsource, name))
					path = path[1:]
				source = scr.get(path[0])
				if isinstance(source, ObsoleteSource):
					print("[Skin] WARNING: SKIN '%s' USES OBSOLETE SOURCE '%s', USE '%s' INSTEAD!" % (name, wsource, source.newSource))
					print("[Skin] OBSOLETE SOURCE WILL BE REMOVED %s, PLEASE UPDATE!" % source.removalDate)
					if source.description:
						print("[Skin] Source description: '%s'." % source.description)
					wsource = source.new_source
				else:
					break
			if source is None:
				raise SkinError("The source '%s' was not found in screen '%s'" % (wsource, name))

			wrender = widget.attrib.get("render")
			if not wrender:
				if wsource:
					raise SkinError("For source '%s' a renderer must be defined with a 'render=' attribute" % wsource)
				elif wconnection:
					raise SkinError("For connection '%s' a renderer must be defined with a 'render=' attribute" % wconnection)
			for converter in widget.findall("convert"):
				ctype = converter.get("type")
				nostrip = converter.get("nostrip") and parseBoolean("nostrip", converter.get("nostrip"))
				assert ctype, "[Skin] The 'convert' tag needs a 'type' attribute!"
				try:
					parms = converter.text if nostrip else converter.text.strip()
				except Exception:
					parms = ""
				try:
					converterClass = my_import(".".join(("Components", "Converter", ctype))).__dict__.get(ctype)
				except ImportError:
					raise SkinError("Converter '%s' not found" % ctype)
				c = None
				for i in source.downstream_elements:
					if isinstance(i, converterClass) and i.converter_arguments == parms:
						c = i
				if c is None:
					c = converterClass(parms)
					c.connect(source)
				source = c
			try:
				rendererClass = my_import(".".join(("Components", "Renderer", wrender))).__dict__.get(wrender)
			except ImportError:
				raise SkinError("Renderer '%s' not found" % wrender)
			renderer = rendererClass()
			if source:
				renderer.connect(source)
				renderer.label_name = wsource or wname
			attributes = renderer.skinAttributes = []
			collectAttributes(attributes, widget, context, skinPath, ignore=("render", "source"))
			screen.renderer.append(renderer)
		elif wclass:
			try:
				addonClass = my_import(".".join(("Components", "Addons", wclass))).__dict__.get(wclass)
			except ImportError:
				raise SkinError("GUI Addon '%s' not found" % wclass)

			if not wconnection:
				raise SkinError("The widget is from addon type: %s , but no connection is specified." % wclass)

			i = 0
			wclassname_base = name + "_" + wclass + "_" + wconnection + "_"
			while wclassname_base + str(i) in usedComponents:
				i += 1
			wclassname = wclassname_base + str(i)

			usedComponents.add(wclassname)

			screen[wclassname] = addonClass()
			screen[wclassname].connectRelatedElement(wconnection, screen)
			attributes = screen[wclassname].skinAttributes = []
			collectAttributes(attributes, widget, context, skinPath, ignore=("addon",))

	def processApplet(widget, context):
		try:
			codeText = widget.text.strip()
			widgetType = widget.attrib.get("type")
			code = compile(codeText, "skin applet", "exec")
		except Exception as err:
			raise SkinError("Applet failed to compile: '%s'" % str(err))
		if widgetType == "onLayoutFinish":
			screen.onLayoutFinish.append(code)
		elif widgetType == "onContentChanged":
			screen.onContentChanged.append(code)
		else:
			raise SkinError("Applet type '%s' is unknown" % widgetType)

	def processLabel(widget, context):
		w = additionalWidget()
		w.widget = eLabel
		w.skinAttributes = []
		collectAttributes(w.skinAttributes, widget, context, skinPath, ignore=("name",))
		screen.additionalWidgets.append(w)

	def processPixmap(widget, context):
		w = additionalWidget()
		w.widget = ePixmap
		w.skinAttributes = []
		collectAttributes(w.skinAttributes, widget, context, skinPath, ignore=("name",))
		screen.additionalWidgets.append(w)

	def processScreen(widget, context):
		for w in widget:
			conditional = w.attrib.get("conditional")
			if conditional and not [i for i in conditional.split(",") if i in screen.keys()]:
				continue
			objecttypes = w.attrib.get("objectTypes", "").split(",")
			if len(objecttypes) > 1 and (objecttypes[0] not in screen.keys() or not [i for i in objecttypes[1:] if i == screen[objecttypes[0]].__class__.__name__]):
				continue
			p = processors.get(w.tag, processNone)
			try:
				p(w, context)
			except SkinError as err:
				print("[Skin] Error in screen '%s' widget '%s' %s!" % (name, w.tag, str(err)))

	def processPanel(widget, context):
		n = widget.attrib.get("name")
		if n:
			try:
				s = domScreens[n]
			except KeyError:
				print("[Skin] Error: Unable to find screen '%s' referred in screen '%s'!" % (n, name))
			else:
				processScreen(s[0], context)
		layout = widget.attrib.get("layout")
		cc = SkinContextStack if layout == "stack" else SkinContext
		try:
			c = cc(context, widget.attrib.get("position"), widget.attrib.get("size"), widget.attrib.get("font"))
		except Exception as err:
			raise SkinError("Failed to create skin context (position='%s', size='%s', font='%s') in context '%s': %s" % (widget.attrib.get("position"), widget.attrib.get("size"), widget.attrib.get("font"), context, err))
		processScreen(widget, c)

	processors = {
		None: processNone,
		"widget": processWidget,
		"applet": processApplet,
		"eLabel": processLabel,
		"ePixmap": processPixmap,
		"panel": processPanel
	}

	try:
		msg = " from list '%s'" % ", ".join(names) if len(names) > 1 else ""
		posX = "?" if context.x is None else str(context.x)
		posY = "?" if context.y is None else str(context.y)
		sizeW = "?" if context.w is None else str(context.w)
		sizeH = "?" if context.h is None else str(context.h)
		print("[Skin] Processing screen '%s'%s, position=(%s, %s), size=(%s x %s) for module '%s'." % (name, msg, posX, posY, sizeW, sizeH, screen.__class__.__name__))
		context.x = 0
		context.y = 0
		processScreen(myScreen, context)
	except Exception as err:
		import traceback
		print("[Skin] Error in screen '%s': %s: %s" % (name, type(err).__name__, repr(err)))
		traceback.print_exc()

	from Components.GUIComponent import GUIComponent
	unusedComponents = [x for x in set(screen.keys()) - usedComponents if isinstance(x, GUIComponent)]
	assert not unusedComponents, "[Skin] The following components in '%s' don't have a skin entry: %s" % (name, ", ".join(unusedComponents))
	screen = None
	usedComponents = None


def findWidgets(name):
	widgetSet = set()
	element, path = domScreens.get(name, (None, None))
	if element is not None:
		widgets = element.findall("widget")
		if widgets is not None:
			for widget in widgets:
				name = widget.get("name", None)
				if name is not None:
					widgetSet.add(name)
				source = widget.get("source", None)
				if source is not None:
					widgetSet.add(source)
				addonConnection = widget.get("connection", None)
				if addonConnection is not None:
					for x in addonConnection.split(","):
						widgetSet.add(x)
		panels = element.findall("panel")
		if panels is not None:
			for panel in panels:
				name = panel.get("name", None)
				if name:
					widgetSet.update(findWidgets(name))
	return widgetSet


def getSkinFactor():
	skinfactor = getDesktop(GUI_SKIN_ID).size().height() / 720.0
	return skinfactor


def applySkinFactor(*d):
	if len(d) == 1:
		return int(d[0] * getSkinFactor())
	return tuple(int(value * getSkinFactor()) if isinstance(value, (int, float)) else value for value in d)


def findSkinScreen(names):
	if not isinstance(names, list):
		names = [names]
	for name in names:
		screen, path = domScreens.get(name, (None, None))
		if screen is not None:
			return name
	return None


def dump(x, i=0):
	print(" " * i + str(x))
	try:
		for n in x.childNodes:
			dump(n, i + 1)
	except Exception:
		None
