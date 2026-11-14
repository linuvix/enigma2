from enigma import RT_HALIGN_CENTER, loadJPG, loadPNG, loadSVG
try:
    from enigma import detectImageType, loadGIF, loadWEBP
    _HAVE_DETECT = True
except ImportError:
    _HAVE_DETECT = False

def LoadPixmap(path, desktop=None, cached=None, width=0, height=0,
               scaletoFit=0, align=RT_HALIGN_CENTER, autoDetect=False):
    extension = path[-4:]
    if autoDetect and _HAVE_DETECT:
        detection = {0: ".png", 1: ".jpg", 3: ".gif", 4: ".svg", 5: ".webp"}
        extension = detection.get(detectImageType(path), extension)

    if extension == ".png":
        ptr = loadPNG(path, 0, 0 if cached is False else 1)
    elif extension == ".jpg":
        ptr = loadJPG(path, 1 if cached is True else 0)
    elif extension == ".gif" and _HAVE_DETECT:
        ptr = loadGIF(path, 1 if cached is True else 0)
    elif extension == ".webp" and _HAVE_DETECT:
        ptr = loadWEBP(path, 1 if cached is True else 0)
    elif extension == ".svg":
        from skin import parameters, getSkinFactor
        autoscale = int(parameters.get("AutoscaleSVG", -1))
        scale = height == 0 and (autoscale == -1 and "/skin_default/" in path or autoscale == 1) and getSkinFactor() or 0
        ptr = loadSVG(path, 0 if cached is False else 1, width, height, scale, scaletoFit, align)
    elif path[-1:] == ".":
        alpha = loadPNG(path + "a.png", 0, 0)
        ptr = loadJPG(path + "rgb.jpg", alpha, 0)
    else:
        raise Exception("Neither .png nor .jpg nor .svg, please fix file extension")
    if ptr and desktop:
        desktop.makeCompatiblePixmap(ptr)
    return ptr


# --- OpenATV compatibility shim -------------------------------------------
# OpenATV plugins call ePixmap.setPixmapFromFile(path, autoDetect). Our SWIG
# bindings only expose the 1-arg overload (SWIG merged the two C++ signatures),
# so accept and ignore the extra argument here. loadImage() already dispatches
# by file extension, so autoDetect was never needed in this build.
import enigma as _enigma_mod

_orig_epixmap_setPixmapFromFile = _enigma_mod.ePixmap.setPixmapFromFile

def _epixmap_setPixmapFromFile_compat(self, filename, autoDetect=False):
    return _orig_epixmap_setPixmapFromFile(self, filename)

_enigma_mod.ePixmap.setPixmapFromFile = _epixmap_setPixmapFromFile_compat
# ---------------------------------------------------------------------------
