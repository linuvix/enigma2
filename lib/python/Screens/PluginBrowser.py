from Screens.Screen import Screen
from Screens.ParentalControlSetup import ProtectedScreen
from enigma import eConsoleAppContainer, eDVBDB, eTimer, eSize, ePoint, getDesktop

from Components.ActionMap import ActionMap, NumberActionMap
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigText
from Components.PluginComponent import plugins
from Components.PluginList import *
from Components.Label import Label
from Components.Language import language
from Components.ServiceList import refreshServiceList
from Components.Harddisk import harddiskmanager
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
try:
    from Components.SystemInfo import hassoftcaminstalled
except ImportError:
    def hassoftcaminstalled():
        return False
from Components.Pixmap import Pixmap
from Components import Opkg
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.Console import Console
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

from skin import parseColor
from time import time
import os
import math
import shlex
import re

language.addCallback(plugins.reloadPlugins)


if not hasattr(config.misc, "plugin_style"):
    config.misc.plugin_style = ConfigSelection(
        default="list",
        choices=[("list", "List")]
    )

if not hasattr(config.misc, "pluginbrowser"):
    config.misc.pluginbrowser = ConfigSubsection()
if not hasattr(config.misc.pluginbrowser, "plugin_order"):
    config.misc.pluginbrowser.plugin_order = ConfigText(default="")


REF_W = 1920.0
REF_H = 1080.0


def getDesktopSize():
    s = getDesktop(0).size()
    return (s.width(), s.height())


_desktop_scale = None


def getScale():
    """Return (x_scale, y_scale) relative to 1920x1080 reference."""
    global _desktop_scale
    if _desktop_scale is None:
        w, h = getDesktopSize()
        _desktop_scale = (w / REF_W, h / REF_H)
    return _desktop_scale


def sx(v):
    """Scale a horizontal value from 1920-reference space."""
    return int(round(v * getScale()[0]))


def sy(v):
    """Scale a vertical value from 1080-reference space."""
    return int(round(v * getScale()[1]))


def isFullHD():
    """Kept for backward compatibility; true for HD-class and above."""
    return getDesktopSize()[0] >= 1920


class PluginBrowserSummary(Screen):
    def __init__(self, session, parent):
        Screen.__init__(self, session, parent=parent)
        self["entry"] = StaticText("")
        self["desc"] = StaticText("")
        self.onShow.append(self.addWatcher)
        self.onHide.append(self.removeWatcher)

    def addWatcher(self):
        self.parent.onChangedEntry.append(self.selectionChanged)
        self.parent.selectionChanged()

    def removeWatcher(self):
        try:
            self.parent.onChangedEntry.remove(self.selectionChanged)
        except ValueError:
            pass

    def selectionChanged(self, name, desc):
        self["entry"].text = name
        self["desc"].text = desc


class PluginBrowser(Screen, ProtectedScreen):
    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle(_("Plugin browser"))
        ProtectedScreen.__init__(self)

        self.firsttime = True
        self.current_style = getattr(config.misc.plugin_style, "value", "list")
        self.is_grid_mode = self.current_style in (
            "grid1", "grid2", "grid3", "grid4", "grid5",
            "grid6", "grid7", "grid8", "grid9",
        )


        if self.is_grid_mode:
            self.skinName = "PluginBrowserNew"
        else:
            self.skinName = "PluginBrowser"


        self["key_red"] = self["red"] = Label(_("Remove plugins"))
        self["key_green"] = self["green"] = Label(_("Download plugins"))
        if self.is_grid_mode:
            self["key_yellow"] = Label(_("Move plugins"))
        self["key_menu"] = StaticText(_("MENU"))
        self["help_text"] = Label(_("0: default order  |  MENU: options" if self.is_grid_mode else "0: default order  |  MENU: view styles"))


        self['pages'] = Label()
        self['plugin_description'] = Label()


        self.list = []
        self["list"] = PluginList(self.list)


        self["actions"] = ActionMap(["WizardActions", "MenuActions"],
        {
            "ok": self.ok,
            "back": self.back,
            "menu": self.openViewMenu,
        })

        color_actions = {
            "red": self.delete,
            "green": self.download,
        }
        if self.is_grid_mode:
            color_actions["yellow"] = self.startGridMoveMode
        self["PluginDownloadActions"] = ActionMap(["ColorActions"], color_actions)


        self["DirectionActions"] = ActionMap(["DirectionActions"],
        {
            "moveUp": self.moveUp,
            "moveDown": self.moveDown
        })


        self["NumberActions"] = NumberActionMap(["NumberActions"],
        {
            "1": self.keyNumberGlobal,
            "2": self.keyNumberGlobal,
            "3": self.keyNumberGlobal,
            "4": self.keyNumberGlobal,
            "5": self.keyNumberGlobal,
            "6": self.keyNumberGlobal,
            "7": self.keyNumberGlobal,
            "8": self.keyNumberGlobal,
            "9": self.keyNumberGlobal,
            "0": self.keyNumberGlobal
        })


        self["HelpActions"] = ActionMap(["HelpActions"],
        {
            "displayHelp": self.showHelp,
        })


        self["NavigationActions"] = ActionMap(["DirectionActions"],
        {
            "up": self.keyUp,
            "down": self.keyDown,
            "left": self.keyLeft,
            "right": self.keyRight,
        })

        self.help = False
        self.number = 0
        self.nextNumberTimer = eTimer()
        self.nextNumberTimer.callback.append(self.okbuttonClick)


        self.warningTimer = eTimer()
        self.warningTimer.callback.append(self.checkWarnings)
        self._warning_retries = 0
        self._reopening = False
        self.onClose.append(self.stopWarningTimer)


        self.mainlist = []
        self.plugins_pos = []
        self.plugins = []
        self.current = 0
        self.current_page = 0
        self.grid_move_mode = False
        self.grid_move_original = None
        self.grid_plugin_picked = False


        self.setColors()


        if self.is_grid_mode:
            self.skin = self.buildGridSkin()
        else:
            self.skin = self.buildListSkin()

        self.onFirstExecBegin.append(self.scheduleWarnings)
        self.onShown.append(self.updateView)
        self.onChangedEntry = []
        self["list"].onSelectionChanged.append(self.selectionChanged)
        self.onLayoutFinish.append(self.saveListsize)

    def showHelp(self):
        """Show help information - required for HelpActions"""
        if self.is_grid_mode:
            return
        if config.usage.menu_show_numbers.value not in ("menu&plugins", "plugins"):
            self.help = not self.help
            self.updateList(self.help)

    def setColors(self):
        """Set colors based on current grid style"""

        if config.misc.plugin_style.value == "grid1":
            self.backgroundColor = "#44000000"
            self.primaryColor = "#282D33"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#53616F"
            self.secondaryColorLabel = "#FFFFFF"

        elif config.misc.plugin_style.value == "grid2":
            self.backgroundColor = "#101E22"
            self.primaryColor = "#22383D"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#347C78"
            self.secondaryColorLabel = "#FFFFFF"

        elif config.misc.plugin_style.value == "grid3":
            self.backgroundColor = "#44000000"
            self.primaryColor = "#20000000"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#3B3B3B"
            self.secondaryColorLabel = "#FFFFFF"

        elif config.misc.plugin_style.value == "grid4":
            self.backgroundColor = "#0B1B2B"
            self.primaryColor = "#173B5E"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#287FA3"
            self.secondaryColorLabel = "#FFFFFF"

        elif config.misc.plugin_style.value == "grid5":
            self.backgroundColor = "#241711"
            self.primaryColor = "#493027"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#B85C42"
            self.secondaryColorLabel = "#FFFFFF"

        elif config.misc.plugin_style.value == "grid6":
            self.backgroundColor = "#10251C"
            self.primaryColor = "#24513A"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#38865B"
            self.secondaryColorLabel = "#FFFFFF"

        elif config.misc.plugin_style.value == "grid7":
            self.backgroundColor = "#440000"
            self.primaryColor = "#2D5A8C"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#3A7B9F"
            self.secondaryColorLabel = "#FFFFFF"

        elif config.misc.plugin_style.value == "grid8":
            self.backgroundColor = "#211A0B"
            self.primaryColor = "#493814"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#A17B25"
            self.secondaryColorLabel = "#FFFFFF"

        elif config.misc.plugin_style.value == "grid9":
            self.backgroundColor = "#1D1225"
            self.primaryColor = "#452653"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#80509A"
            self.secondaryColorLabel = "#FFFFFF"
        else:

            self.backgroundColor = "#44000000"
            self.primaryColor = "#282828"
            self.primaryColorLabel = "#FFFFFF"
            self.secondaryColor = "#4E4E4E"
            self.secondaryColorLabel = "#FFFFFF"


    def buildListSkin(self):
        W, H = getDesktopSize()

        title_x, title_y = sx(50), sy(12)
        title_w, title_h = sx(900), sy(100)
        title_font = sy(75)

        desc_x, desc_y = sx(50), sy(105)
        desc_w, desc_h = sx(900), sy(100)
        desc_font = sy(40)

        right_margin = sx(50)

        clock_w, clock_h = sx(273), sy(100)
        clock_x, clock_y = W - right_margin - clock_w, sy(12)
        clock_font = sy(80)

        date_w, date_h = sx(762), sy(50)
        date_x, date_y = W - right_margin - date_w, sy(105)
        date_font = sy(40)


        help_x, help_y = sx(740), sy(1013)
        help_w, help_h = sx(800), sy(50)
        help_font = sy(32)

        list_x, list_y = sx(50), sy(190)
        list_w, list_h = sx(1820), sy(800)

        bar1_x, bar1_y = sx(67), sy(1065)
        bar2_x, bar2_y = sx(393), sy(1065)
        bar_w, bar_h = sx(300), sy(8)

        key1_x, key2_x = sx(67), sx(393)
        key_y = sy(1013)
        key_w, key_h = sx(300), sy(50)
        key_font = sy(32)

        return """
        <screen name="PluginBrowser" position="0,0" size="%d,%d" flags="wfNoBorder" backgroundColor="#44000000">
            <eLabel text="Plugin Browser" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00ffffff" backgroundColor="#44000000" transparent="1" zPosition="2" />
            <widget name="plugin_description" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00b0f7e4" backgroundColor="#44000000" transparent="1" zPosition="2" />
            <widget source="global.CurrentTime" render="Label" position="%d,%d" size="%d,%d" font="Regular;%d" halign="right" backgroundColor="#44000000" transparent="1" foregroundColor="#00ffffff">
                <convert type="ClockToText"/>
            </widget>
            <widget backgroundColor="#44000000" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00b0f7e4" halign="right" render="Label" source="global.CurrentTime" transparent="1">
                <convert type="ClockToText">FullDate</convert>
            </widget>
            <widget name="help_text" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00b0f7e4" backgroundColor="#44000000" transparent="1" zPosition="2" halign="left" valign="center" />
            <widget name="list" position="%d,%d" size="%d,%d" zPosition="1" />
            <eLabel position="%d,%d" size="%d,%d" backgroundColor="#00ff2525" foregroundColor="#00ff2525" zPosition="4"/>
            <eLabel position="%d,%d" size="%d,%d" backgroundColor="#00389416" foregroundColor="#00389416" zPosition="4"/>
            <widget name="key_red" position="%d,%d" size="%d,%d" font="Regular;%d" zPosition="1" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1"/>
            <widget name="key_green" position="%d,%d" size="%d,%d" font="Regular;%d" zPosition="1" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1"/>
        </screen>
        """ % (
            W, H,
            title_x, title_y, title_w, title_h, title_font,
            desc_x, desc_y, desc_w, desc_h, desc_font,
            clock_x, clock_y, clock_w, clock_h, clock_font,
            date_x, date_y, date_w, date_h, date_font,
            help_x, help_y, help_w, help_h, help_font,
            list_x, list_y, list_w, list_h,
            bar1_x, bar1_y, bar_w, bar_h,
            bar2_x, bar2_y, bar_w, bar_h,
            key1_x, key_y, key_w, key_h, key_font,
            key2_x, key_y, key_w, key_h, key_font,
        )

    def getOrderedPlugins(self):
        """Return plugin-menu descriptors in the user's saved order."""
        pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)[:]
        by_basename = {
            os.path.basename(plugin.path): plugin
            for plugin in pluginlist
        }
        ordered = []
        seen = set()
        for name in config.misc.pluginbrowser.plugin_order.value.split(","):
            plugin = by_basename.get(name)
            if plugin is not None and name not in seen:
                ordered.append(plugin)
                seen.add(name)
        ordered.extend(
            plugin for plugin in pluginlist
            if os.path.basename(plugin.path) not in seen
        )
        return ordered


    def buildGridSkin(self):
        W, H = getDesktopSize()


        REF_COLS = 7
        REF_ROWS = 3
        REF_GRID_Y = 190
        REF_TILE_H = 250
        REF_TILE_GAP_Y = 260


        OPTICAL_NUDGE = sx(0)
        grid_margin_l = sx(50) + OPTICAL_NUDGE
        grid_margin_r = sx(50) - OPTICAL_NUDGE

        avail_w = W - grid_margin_l - grid_margin_r


        pitch_f = avail_w / float(REF_COLS)
        tile_w = int(round(pitch_f * 0.96))
        tile_w = max(tile_w, 40)
        tile_h = sy(REF_TILE_H)


        span_w = int(round(pitch_f * REF_COLS))
        slack = avail_w - span_w
        grid_margin_l += slack // 2
        grid_margin_r += slack - (slack // 2)

        posxstart = grid_margin_l
        posystart = sy(REF_GRID_Y)
        posxplus = int(round(pitch_f))
        posyplus = sy(REF_TILE_GAP_Y)
        iconsize = "%d,%d" % (tile_w, tile_h)


        label_h    = int(round(tile_h * 0.34))
        label_w    = int(round(tile_w * 0.88))
        label_off_x = (tile_w - label_w) // 2
        label_off_y = int(round(tile_h * 0.56))
        label_font  = sy(32)

        icon_h    = int(round(tile_h * 0.32))
        icon_w    = int(round(tile_w * 0.72))
        icon_off_x = (tile_w - icon_w) // 2
        icon_off_y = int(round(tile_h * 0.22))


        self.tile_w = tile_w
        self.tile_h = tile_h
        self.sel_lift_x = max(2, int(round(tile_w * 0.04)))
        self.sel_lift_y = max(2, int(round(tile_h * 0.04)))
        self.sel_w  = tile_w + 2 * self.sel_lift_x
        self.sel_h  = tile_h + 2 * self.sel_lift_y
        self.norm_w = tile_w
        self.norm_h = tile_h


        self.lab_off_x = (tile_w - label_w) // 2
        self.lab_off_y = int(round(tile_h * 0.56))


        self.sel_lab_off_x = self.lab_off_x - (self.sel_lift_x // 2)
        self.sel_lab_off_y = (self.lab_off_y - self.sel_lift_y)


        positionx1, positiony1 = sx(50), sy(12)
        sizex1, sizey1 = sx(900), sy(100)
        font1 = sy(75)


        positionx2, positiony2 = sx(50), sy(105)
        sizex2, sizey2 = sx(900), sy(100)
        font2 = sy(40)


        right_margin = sx(50)
        sizex3, sizey3 = sx(273), sy(100)
        positionx3, positiony3 = W - right_margin - sizex3, sy(12)
        font3 = sy(80)


        sizex4, sizey4 = sx(762), sy(50)
        positionx4, positiony4 = W - right_margin - sizex4, sy(105)
        font4 = sy(40)


        sizex5, sizey5 = sx(220), sy(50)
        positionx5, positiony5 = W - right_margin - sizex5, sy(1013)
        font5 = sy(32)


        eLabelx1, eLabely1 = sx(67), sy(1065)
        eLabelx2, eLabely2 = sx(393), sy(1065)
        eLabelw, eLabelh = sx(300), sy(8)

        positionxkey1 = sx(67)
        positionxkey2 = sx(393)
        positionykey = sy(1013)
        sizekeysx, sizekeysy = sx(300), sy(50)
        fontkey = sy(32)


        help_x, help_y = sx(1019), sy(1013)
        help_w, help_h = (W - right_margin - sizex5) - help_x, sy(50)
        help_font = sy(30)

        skin = """
            <screen name="PluginBrowserNew" position="0,0" size="%d,%d" flags="wfNoBorder" backgroundColor="%s">
                <eLabel text="Plugin Browser" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00ffffff" backgroundColor="#44000000" transparent="1" zPosition="2" />
                <widget name="plugin_description" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00b0f7e4" backgroundColor="#44000000" transparent="1" zPosition="2" />
                <widget source="global.CurrentTime" render="Label" position="%d,%d" size="%d,%d" font="Regular;%d" halign="right" backgroundColor="#44000000" transparent="1" foregroundColor="#00ffffff">
                    <convert type="ClockToText"/>
                </widget>
                <widget backgroundColor="#44000000" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00b0f7e4" halign="right" render="Label" source="global.CurrentTime" transparent="1">
                    <convert type="ClockToText">FullDate</convert>
                </widget>
                <widget name="pages" foregroundColor="#00ffffff" position="%d,%d" size="%d,%d" font="Regular;%d" zPosition="2" halign="right" valign="center" transparent="1" />
                <widget name="help_text" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00b0f7e4" backgroundColor="#44000000" transparent="1" zPosition="2" halign="center" valign="center" />
                <eLabel position="%d,%d" size="%d,%d" backgroundColor="#00ff2525" foregroundColor="#00ff2525" zPosition="4"/>
                <eLabel position="%d,%d" size="%d,%d" backgroundColor="#00389416" foregroundColor="#00389416" zPosition="4"/>
                <eLabel position="%d,%d" size="%d,%d" backgroundColor="#00e5c900" foregroundColor="#00e5c900" zPosition="4"/>
                <widget name="key_red" position="%d,%d" size="%d,%d" font="Regular;%d" zPosition="1" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1"/>
                <widget name="key_green" position="%d,%d" size="%d,%d" font="Regular;%d" zPosition="1" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1"/>
                <widget name="key_yellow" position="%d,%d" size="%d,%d" font="Regular;%d" zPosition="1" halign="center" valign="center" foregroundColor="#00ffffff" backgroundColor="#16000000" transparent="1"/>
        """ % (
            W, H, self.backgroundColor,
            positionx1, positiony1, sizex1, sizey1, font1,
            positionx2, positiony2, sizex2, sizey2, font2,
            positionx3, positiony3, sizex3, sizey3, font3,
            positionx4, positiony4, sizex4, sizey4, font4,
            positionx5, positiony5, sizex5, sizey5, font5,
            help_x, help_y, help_w, help_h, help_font,
            eLabelx1, eLabely1, eLabelw, eLabelh,
            eLabelx2, eLabely2, eLabelw, eLabelh,
            sx(719), sy(1065), eLabelw, eLabelh,
            positionxkey1, positionykey, sizekeysx, sizekeysy, fontkey,
            positionxkey2, positionykey, sizekeysx, sizekeysy, fontkey,
            sx(719), positionykey, sizekeysx, sizekeysy, fontkey,
        )


        posx = posxstart
        posy = posystart
        list_dummy = []
        skincontent = ""
        count = 0

        for x, p in enumerate(self.getOrderedPlugins()):
            x += 1
            count += 1

            skincontent += (
                '<widget backgroundColor="%s" name="plugin_%d" position="%d,%d" size="%s" cornerRadius="24" />'
                % (self.primaryColor, x, posx, posy, iconsize)
            )
            skincontent += (
                '<widget foregroundColor="%s" name="label_%d" position="%d,%d" size="%d,%d" '
                'zPosition="3" font="Regular;%d" halign="center" valign="center" transparent="1" />'
                % (self.primaryColorLabel, x,
                   posx + label_off_x, posy + label_off_y,
                   label_w, label_h, label_font)
            )
            skincontent += (
                '<widget name="icon_%d" position="%d,%d" size="%d,%d" '
                'zPosition="3" alphatest="on" transparent="1" />'
                % (x, posx + icon_off_x, posy + icon_off_y, icon_w, icon_h)
            )

            self.plugins_pos.append((posx, posy))
            self.plugins.append((p.name, p.description, p, p.icon))
            self["plugin_%d" % x] = Label()
            self["label_%d" % x] = Label()
            self["icon_%d" % x] = Pixmap()
            self["label_%d" % x].setText(p.name)

            posx += posxplus
            list_dummy.append(x)
            if len(list_dummy) == REF_COLS:
                list_dummy[:] = []
                posx = posxstart
                posy += posyplus
            if count == REF_COLS * REF_ROWS:
                posx = posxstart
                posy = posystart
                count = 0

        skin += skincontent
        skin += '</screen>'
        self.grid_widget_count = len(self.plugins)


        per_page = REF_COLS * REF_ROWS
        self.total_pages = max(1, (len(self.plugins) + per_page - 1) // per_page)
        self.mainlist = [
            list(range(page * per_page + 1, min((page + 1) * per_page, len(self.plugins)) + 1))
            for page in range(self.total_pages)
        ]

        return skin

    def updateView(self):
        """Update the view based on current mode"""
        if self.is_grid_mode:
            self.updateGrid()
            self["list"].hide()
        else:
            self.updateList(False)
            self['pages'].hide()
            self['plugin_description'].hide()
            for i in range(1, len(self.plugins) + 1):
                if hasattr(self, "plugin_" + str(i)):
                    self["plugin_" + str(i)].hide()
                    self["label_" + str(i)].hide()
                    self["icon_" + str(i)].hide()

    def updateGrid(self):
        self.setIcons()
        self.activeBox()

    def refreshGridPlugins(self):
        current_plugins = self.getOrderedPlugins()
        refreshed = [
            (plugin.name, plugin.description, plugin, plugin.icon)
            for plugin in current_plugins
        ]

        if len(refreshed) > len(self.plugins_pos):
            self._reopening = True
            self.close()
            self.reopenTimer = eTimer()
            self.reopenTimer.callback.append(self.reopenBrowser)
            self.reopenTimer.start(100, True)
            return

        self.plugins = refreshed
        for index, plugin in enumerate(self.plugins, 1):
            self["label_%d" % index].setText(plugin[0])
            self["plugin_%d" % index].show()
            self["label_%d" % index].show()
            self["icon_%d" % index].show()


        for index in range(len(self.plugins) + 1, len(self.plugins_pos) + 1):
            self["plugin_%d" % index].hide()
            self["label_%d" % index].hide()
            self["icon_%d" % index].hide()

        per_page = 21
        self.total_pages = max(1, (len(self.plugins) + per_page - 1) // per_page)
        self.mainlist = [
            list(range(page * per_page + 1, min((page + 1) * per_page, len(self.plugins)) + 1))
            for page in range(self.total_pages)
        ]
        self.current = min(self.current, max(0, len(self.plugins) - 1))
        self.current_page = self.current // per_page if self.plugins else 0

        self.setIcons()
        if self.plugins:
            self.activeBox()
        else:
            self["plugin_description"].setText("")
            self["pages"].setText("Page 1/1")

    def updateList(self, showHelp=False):
        self.list = []
        ordered = self.getOrderedPlugins()
        self.list = [PluginEntryComponent(plugin, self.listWidth) for plugin in ordered]
        if config.usage.menu_show_numbers.value in ("menu&plugins", "plugins") or showHelp:
            for x in enumerate(self.list):
                tmp = list(x[1][1])
                tmp[7] = "%s %s" % (x[0] + 1, tmp[7])
                x[1][1] = tuple(tmp)
        self["list"].l.setList(self.list)

    def openViewMenu(self):
        if self.grid_move_mode:
            return
        menu_list = [
            (_("View as list"), "list"),
            (_("Grid 1 - Graphite"), "grid1"),
            (_("Grid 2 - Teal"), "grid2"),
            (_("Grid 3 - Transparent"), "grid3"),
            (_("Grid 4 - Blue"), "grid4"),
            (_("Grid 5 - Copper"), "grid5"),
            (_("Grid 6 - Emerald"), "grid6"),
            (_("Grid 7 - Arctic Blue"), "grid7"),
            (_("Grid 8 - Golden Amber"), "grid8"),
            (_("Grid 9 - Purple"), "grid9"),
        ]

        if self.is_grid_mode:
            menu_list.append((_("Move plugins"), "move"))

        current_idx = 0
        for i, (name, style) in enumerate(menu_list):
            if style == config.misc.plugin_style.value:
                current_idx = i
                break

        if self.is_grid_mode:
            title = _(
                "Choose a view style or rearrange plugins\n\n"
                "Move: arrows select/move, OK pick/place, EXIT save."
            )
        else:
            title = _("Choose a view style\n\nChanges take effect immediately.")

        self.session.openWithCallback(
            self.viewMenuCallback,
            ChoiceBox,
            title=title,
            list=menu_list,
            selection=current_idx
        )

    def viewMenuCallback(self, choice):
        if choice:
            new_style = choice[1]
            if new_style == "move":
                self.startGridMoveMode()
                return
            if new_style != config.misc.plugin_style.value:
                config.misc.plugin_style.value = new_style
                config.misc.plugin_style.save()
                self.close()
                self.reopenTimer = eTimer()
                self.reopenTimer.callback.append(self.reopenBrowser)
                self.reopenTimer.start(100, True)

    def reopenBrowser(self):
        self.session.open(PluginBrowser)


    def saveListsize(self):
        listsize = self["list"].instance.size()
        self.listWidth = listsize.width()
        self.listHeight = listsize.height()

    def createSummary(self):
        return PluginBrowserSummary

    def selectionChanged(self):
        if self.is_grid_mode:
            return

        item = self["list"].getCurrent()

        if item:
            p = item[0]
            name = p.name
            desc = p.description
            self["plugin_description"].setText(desc)
        else:
            name = "-"
            desc = ""

        for cb in self.onChangedEntry:
            cb(name, desc)

    def updateGridSummary(self):
        if not self.is_grid_mode:
            return

        if self.plugins and self.current < len(self.plugins):
            plugin = self.plugins[self.current]
            name = plugin[0]
            desc = plugin[1] or ""
        else:
            name = "-"
            desc = ""

        for cb in self.onChangedEntry:
            cb(name, desc)

    def scheduleWarnings(self):
        """Show plugin warnings after Enigma2 has restored this screen."""
        try:
            self.warningTimer.stop()
            self.warningTimer.start(250, True)
        except Exception as error:
            print("[PluginBrowser] Unable to schedule plugin warnings:", error)

    def stopWarningTimer(self):
        """Prevent a delayed dialog from opening after this screen closes."""
        try:
            self.warningTimer.stop()
        except Exception:
            pass

    def checkWarnings(self):
        """Display warnings only from the active PluginBrowser screen."""
        warnings = getattr(plugins, "warnings", None) or []
        if not warnings or self._reopening:
            return

        text = _("Some plugins are not available:\\n")
        for pluginname, error in warnings:
            text += "%s (%s)\\n" % (pluginname, error)

        try:
            self.session.open(
                MessageBox, text=text, type=MessageBox.TYPE_WARNING
            )
            plugins.resetWarnings()
            self._warning_retries = 0
        except RuntimeError as error:
            print("[PluginBrowser] Warning dialog deferred:", error)
            self._warning_retries += 1
            if self._warning_retries <= 5:
                self.warningTimer.start(500, True)

    def ok(self):
        if self.grid_move_mode:

            self.grid_plugin_picked = not self.grid_plugin_picked
            if self.grid_plugin_picked:
                self["help_text"].setText(
                    _("Picked: arrows move | OK: place | EXIT: save")
                )
            else:
                self["help_text"].setText(
                    _("Arrows: select | OK: pick up | EXIT: save")
                )
            self.activeBox()
            return
        if self.is_grid_mode:
            if self.plugins and self.current < len(self.plugins):
                plugin = self.plugins[self.current][2]
                try:
                    plugin(session=self.session)
                except Exception as e:
                    print("[PluginBrowser] Plugin failed:", e)
        else:
            current = self["list"].l.getCurrentSelection()
            if current:
                plugin = current[0]
                try:
                    plugin(session=self.session)
                except Exception as e:
                    print("[PluginBrowser] Plugin failed:", e)
        self.help = False

    def setDefaultList(self, answer):
        if answer:
            config.misc.pluginbrowser.plugin_order.value = ""
            config.misc.pluginbrowser.plugin_order.save()
            if self.is_grid_mode:


                self.current = 0
                self.current_page = 0
                self.refreshGridPlugins()
            else:
                self.updateList(False)

    def keyNumberGlobal(self, number):
        if number == 0 and self.number == 0:
            has_plugins = bool(self.plugins) if self.is_grid_mode else bool(self.list)
            if has_plugins and config.misc.pluginbrowser.plugin_order.value != "":
                self.session.openWithCallback(
                    self.setDefaultList,
                    MessageBox,
                    _("Restore the default plugin order?"),
                    MessageBox.TYPE_YESNO
                )
            return
        if self.is_grid_mode:
            return
        else:
            self.number = self.number * 10 + number
            if self.number and self.number <= len(self.list):
                if number * 10 > len(self.list) or self.number >= 10:
                    self.okbuttonClick()
                else:
                    self.nextNumberTimer.start(1400, True)
            else:
                self.resetNumberKey()

    def okbuttonClick(self):
        if self.is_grid_mode:
            return
        self["list"].moveToIndex(self.number - 1)
        self.resetNumberKey()
        self.ok()

    def resetNumberKey(self):
        self.nextNumberTimer.stop()
        self.number = 0

    def moveUp(self):
        if self.is_grid_mode:
            self.startGridMoveMode()
        else:
            self.move(-1)

    def moveDown(self):
        if self.is_grid_mode:
            self.startGridMoveMode()
        else:
            self.move(1)

    def move(self, direction):
        if self.is_grid_mode:
            return
        if len(self.list) > 1:
            currentIndex = self["list"].getSelectionIndex()
            swapIndex = (currentIndex + direction) % len(self.list)

            if currentIndex == 0 and swapIndex != 1:
                self.list = self.list[1:] + [self.list[0]]
            elif swapIndex == 0 and currentIndex != 1:
                self.list = [self.list[-1]] + self.list[:-1]
            else:
                self.list[currentIndex], self.list[swapIndex] = self.list[swapIndex], self.list[currentIndex]

            self["list"].l.setList(self.list)

            if direction == 1:
                self["list"].down()
            else:
                self["list"].up()

            plugin_order = []
            for x in self.list:
                try:
                    plugin_order.append(os.path.basename(x[0].path))
                except Exception:
                    continue
            config.misc.pluginbrowser.plugin_order.value = ",".join(plugin_order)
            config.misc.pluginbrowser.plugin_order.save()

    def keyLeft(self):
        if self.is_grid_mode:
            if self.grid_move_mode and self.grid_plugin_picked:
                self.reorderGrid(-1)
            else:
                self.moveGrid(1, 'backwards')

    def keyRight(self):
        if self.is_grid_mode:
            if self.grid_move_mode and self.grid_plugin_picked:
                self.reorderGrid(1)
            else:
                self.moveGrid(1, 'forward')

    def keyUp(self):
        if self.is_grid_mode:
            if self.grid_move_mode and self.grid_plugin_picked:
                self.reorderGrid(-7)
            else:
                self.moveGrid(7, 'backwards')

    def keyDown(self):
        if self.is_grid_mode:
            if self.grid_move_mode and self.grid_plugin_picked:
                self.reorderGrid(7)
            else:
                self.moveGrid(7, 'forward')

    def back(self):
        if self.grid_move_mode:

            self.finishGridMoveMode(save=True)
        else:
            self.close()

    def startGridMoveMode(self):
        if not self.is_grid_mode or self.grid_move_mode or len(self.plugins) < 2:
            return
        self.grid_move_original = list(self.plugins)
        self.grid_move_mode = True
        self.grid_plugin_picked = False
        self["help_text"].setText(
            _("Arrows: select | OK: pick up | EXIT: save")
        )
        self.activeBox()

    def finishGridMoveMode(self, save):
        if not self.grid_move_mode:
            return
        if save:
            order = []
            for plugin in self.plugins:
                try:
                    order.append(os.path.basename(plugin[2].path))
                except Exception:
                    continue
            config.misc.pluginbrowser.plugin_order.value = ",".join(order)
            config.misc.pluginbrowser.plugin_order.save()
        elif self.grid_move_original is not None:
            self.plugins = list(self.grid_move_original)
            for index, plugin in enumerate(self.plugins, 1):
                self["label_%d" % index].setText(plugin[0])
        self.grid_move_mode = False
        self.grid_move_original = None
        self.grid_plugin_picked = False
        self["help_text"].setText(
            _("0: default order  |  MENU: options")
            if self.is_grid_mode else _("0: default order  |  MENU: view styles")
        )
        self.setIcons()
        self.activeBox()

    def reorderGrid(self, delta):
        if not self.grid_move_mode or not self.grid_plugin_picked or len(self.plugins) < 2:
            return
        count = len(self.plugins)
        target = self.current + delta
        if target < 0 or target >= count:
            return


        if delta == -1 and self.current % 7 == 0 and self.current % 21 != 0:
            return
        if delta == 1 and self.current % 7 == 6 and (self.current + 1) % 21 != 0:
            return

        self.plugins[self.current], self.plugins[target] = (
            self.plugins[target], self.plugins[self.current]
        )
        self.current = target


        selected = self.current + 1
        for page_index, page_items in enumerate(self.mainlist):
            if selected in page_items:
                self.current_page = page_index
                break

        for index, plugin in enumerate(self.plugins, 1):
            self["label_%d" % index].setText(plugin[0])
        self.setIcons()
        self.activeBox()


    def setIcons(self):
        fallback_icon = None
        for x, elem in enumerate(self.plugins):
            x += 1
            widget_name = 'icon_' + str(x)
            if not hasattr(self[widget_name], "instance") or self[widget_name].instance is None:
                continue
            icon = elem[3]
            if icon is None:
                if fallback_icon is None:
                    fallback_icon = LoadPixmap(
                        resolveFilename(SCOPE_CURRENT_SKIN, "icons/plugin.png")
                    )
                icon = fallback_icon
            self[widget_name].instance.setScale(1)
            self[widget_name].instance.setPixmap(icon)

    def activeBox(self):
        if not self.plugins:
            return


        sel_w, sel_h = self.sel_w, self.sel_h
        sel_off_x, sel_off_y = self.sel_lift_x, self.sel_lift_y
        sel_lab_off_x, sel_lab_off_y = self.sel_lab_off_x, self.sel_lab_off_y

        norm_w, norm_h = self.norm_w, self.norm_h
        norm_lab_off_x, norm_lab_off_y = self.lab_off_x, self.lab_off_y

        for index, plugin in enumerate(self.plugins):
            index += 1
            pos = self.plugins_pos[index - 1]
            if index == self.current + 1:
                self["plugin_description"].setText(plugin[1])
                self["plugin_%d" % index].instance.resize(eSize(sel_w, sel_h))
                self["plugin_%d" % index].instance.move(
                    ePoint(pos[0] - sel_off_x, pos[1] - sel_off_y))
                self["label_%d" % index].instance.move(
                    ePoint(pos[0] + sel_lab_off_x, pos[1] + sel_lab_off_y))
                self["plugin_%d" % index].instance.setBackgroundColor(parseColor(self.secondaryColor))
                self["plugin_%d" % index].instance.invalidate()
                self["label_%d" % index].instance.setBackgroundColor(parseColor(self.secondaryColor))
                self["label_%d" % index].instance.setForegroundColor(parseColor(self.secondaryColorLabel))
            else:
                self["plugin_%d" % index].instance.resize(eSize(norm_w, norm_h))
                self["plugin_%d" % index].instance.move(ePoint(pos[0], pos[1]))
                self["label_%d" % index].instance.move(
                    ePoint(pos[0] + norm_lab_off_x, pos[1] + norm_lab_off_y))
                self["plugin_%d" % index].instance.setBackgroundColor(parseColor(self.primaryColor))
                self["plugin_%d" % index].instance.invalidate()
                self["label_%d" % index].instance.setBackgroundColor(parseColor(self.primaryColor))
                self["label_%d" % index].instance.setForegroundColor(parseColor(self.primaryColorLabel))

        self.paint_hide()
        self.currentPage()
        self.updateGridSummary()

    def currentPage(self):
        self['pages'].setText("Page {}/{}".format(self.current_page + 1, self.total_pages))

    def moveGrid(self, step, direction):
        if not self.is_grid_mode or not self.plugins:
            return

        count = len(self.plugins)
        if step == 1:
            delta = -1 if direction == "backwards" else 1
            self.current = (self.current + delta) % count
        else:


            columns = 7
            row, column = divmod(self.current, columns)
            rows = (count + columns - 1) // columns
            target_row = row + (-1 if direction == "backwards" else 1)
            if target_row < 0:
                target_row = rows - 1
            elif target_row >= rows:
                target_row = 0
            row_start = target_row * columns
            row_length = min(columns, count - row_start)
            self.current = row_start + min(column, row_length - 1)

        selected = self.current + 1
        for page_index, page_items in enumerate(self.mainlist):
            if selected in page_items:
                self.current_page = page_index
                break
        self.activeBox()

    def paint_hide(self):
        for i in range(self.total_pages):
            if i != self.current_page:
                for x in self.mainlist[i]:
                    self["plugin_" + str(x)].hide()
                    self["label_" + str(x)].hide()
                    self['icon_' + str(x)].hide()
            else:
                for x in self.mainlist[i]:
                    self["plugin_" + str(x)].show()
                    self["label_" + str(x)].show()
                    self["icon_" + str(x)].show()


    def isProtected(self):
        return config.ParentalControl.setuppinactive.value and (
            not config.ParentalControl.config_sections.main_menu.value
            or hasattr(self.session, 'infobar') and self.session.infobar is None
        ) and config.ParentalControl.config_sections.plugin_browser.value

    def exit(self):
        self.close(True)

    def delete(self):
        self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.REMOVE)

    def download(self):
        self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginDownloadBrowser, PluginDownloadBrowser.DOWNLOAD, self.firsttime)
        self.firsttime = False

    def PluginDownloadBrowserClosed(self, returnValue):
        if returnValue is None:
            if self.is_grid_mode:
                self.refreshGridPlugins()
            else:
                self.updateList(False)
            if not self._reopening:
                self.scheduleWarnings()
        elif returnValue == 0:
            self.download()
        else:
            self.delete()

    def openExtensionmanager(self):
        if fileExists(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/plugin.py")):
            try:
                from Plugins.SystemPlugins.SoftwareManager.plugin import PluginManager
            except ImportError:
                self.session.open(MessageBox, _("The software management extension is not installed!\nPlease install it."), type=MessageBox.TYPE_INFO, timeout=10)
            else:
                self.session.openWithCallback(self.PluginDownloadBrowserClosed, PluginManager)


class PluginDownloadBrowser(Screen):
    DOWNLOAD = 0
    REMOVE = 1
    PLUGIN_PREFIX = 'enigma2-plugin-'
    lastDownloadDate = None

    def __init__(self, session, type=0, needupdate=True):
        Screen.__init__(self, session)

        self.type = type
        self.needupdate = needupdate

        self.container = eConsoleAppContainer()
        self.container.appClosed.append(self.runFinished)
        self.container.dataAvail.append(self.dataAvail)
        self.onLayoutFinish.append(self.startRun)
        self.setTitle(_("Downloadable new plugins") if self.type == self.DOWNLOAD else _("Remove plugins"))
        self.list = []
        self["list"] = PluginList(self.list)
        self.pluginlist = []
        self.expanded = []
        self.installedplugins = []
        self.plugins_changed = False
        self.reload_settings = False
        self.check_softcams = False
        self.check_settings = False
        self.install_settings_name = ''
        self.remove_settings_name = ''
        self["text"] = Label(_("Downloading plugin information. Please wait...") if self.type == self.DOWNLOAD else _("Getting plugin information. Please wait..."))
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Expand"))
        self["key_blue"] = Label(_("Remove plugins") if self.type == self.DOWNLOAD else _("Download plugins"))
        self.run = 0
        self.remainingdata = ""
        self["actions"] = ActionMap(["WizardActions"],
        {
            "ok": self.go,
            "back": self.requestClose,
        })
        self["PluginDownloadActions"] = ActionMap(["ColorActions"], {
            "blue": self.delete if self.type == self.DOWNLOAD else self.download,
            "red": self.requestClose,
            "green": self.go}
        )
        if os.path.isfile('/usr/bin/opkg'):
            self.opkg = '/usr/bin/opkg'
            self.opkg_install = self.opkg + ' install'
            self.opkg_remove = self.opkg + ' remove --autoremove'
        else:
            self.opkg = 'opkg'
            self.opkg_install = 'opkg install -force-defaults'
            self.opkg_remove = self.opkg + ' remove'
        self["list"].onSelectionChanged.append(self.selectionChanged)

    def selectionChanged(self):
        selection = self["list"].l.getCurrentSelection()
        if selection:
            selection = selection[0]
            if isinstance(selection, str):
                self["key_green"].text = _("Collapse") if selection in self.expanded else _("Expand")
            else:
                self["key_green"].text = _("Install plugin") if self.type == self.DOWNLOAD else _("Remove plugin")

    def go(self):
        selection = self["list"].l.getCurrentSelection()
        if selection:
            selection = selection[0]
            if isinstance(selection, str):
                if selection in self.expanded:
                    self.expanded.remove(selection)
                else:
                    self.expanded.append(selection)
                self.updateList()
            else:
                if self.type == self.DOWNLOAD:
                    self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to download\nthe plugin \"%s\"?") % selection.name)
                elif self.type == self.REMOVE:
                    self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to remove\nthe plugin \"%s\"?") % selection.name)

    def delete(self):
        self.requestClose(1)

    def download(self):
        self.requestClose(0)

    def requestClose(self, returnValue=None):
        if self.plugins_changed:
            plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
        if self.reload_settings:
            self["text"].setText(_("Reloading bouquets and services..."))
            eDVBDB.getInstance().reloadBouquets()
            eDVBDB.getInstance().reloadServicelist()
            from Components.ParentalControl import parentalControl
            parentalControl.open()
            refreshServiceList()
        if self.check_softcams:
            BoxInfo.setItem("HasSoftcamInstalled", hassoftcaminstalled())
        plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
        try:
            self.container.appClosed.remove(self.runFinished)
        except (ValueError, AttributeError):
            pass
        try:
            self.container.dataAvail.remove(self.dataAvail)
        except (ValueError, AttributeError):
            pass
        self.close(returnValue)

    def resetPostInstall(self):
        try:
            del self.postInstallCall
        except Exception:
            pass

    @staticmethod
    def _validPackageName(pkgname):
        return bool(pkgname and re.match(r"^[A-Za-z0-9][A-Za-z0-9+_.:-]*$", pkgname))

    def _selectedPackageName(self):
        selection = self["list"].l.getCurrentSelection()
        if not selection:
            return None
        item = selection[0]
        return getattr(item, "name", None)

    def installDestinationCallback(self, result):
        if result is None:
            self.resetPostInstall()
            self.pending_package = None
            return

        dest = result[1]
        if not isinstance(dest, str) or not dest:
            self.resetPostInstall()
            self.pending_package = None
            return

        if dest.startswith('/'):
            dest = os.path.normpath(dest)
            extra = '--add-dest %s:%s -d %s' % (
                shlex.quote(dest), shlex.quote(dest), shlex.quote(dest)
            )
            Opkg.opkgAddDestination(dest)
        else:
            if not re.match(r"^[A-Za-z0-9_.-]+$", dest):
                self.session.open(
                    MessageBox, _("Invalid installation destination."),
                    type=MessageBox.TYPE_ERROR, timeout=8
                )
                self.resetPostInstall()
                self.pending_package = None
                return
            extra = '-d %s' % shlex.quote(dest)

        self.doInstall(self.installFinished, self.pending_package, extra)

    def runInstall(self, val):
        if not val:
            self.resetPostInstall()
            self.pending_package = None
            return

        pkgname = self._selectedPackageName()
        if not self._validPackageName(pkgname):
            self.session.open(
                MessageBox, _("No valid plugin is selected."),
                type=MessageBox.TYPE_ERROR, timeout=8
            )
            return

        self.pending_package = pkgname
        if self.type == self.DOWNLOAD:
            if pkgname.startswith("picons-"):
                supported_filesystems = frozenset((
                    'ext4', 'ext3', 'ext2', 'reiser', 'reiser4',
                    'jffs2', 'ubifs', 'rootfs'
                ))
                candidates = []
                import Components.Harddisk
                mounts = Components.Harddisk.getProcMounts()
                for partition in harddiskmanager.getMountedPartitions(False, mounts):
                    if partition.filesystem(mounts) in supported_filesystems:
                        candidates.append((partition.description, partition.mountpoint))
                if candidates:
                    from Components.Renderer import Picon
                    self.postInstallCall = Picon.initPiconPaths
                    self.session.openWithCallback(
                        self.installDestinationCallback, ChoiceBox,
                        title=_("Install picons on"), list=candidates
                    )
                else:
                    self.session.open(
                        MessageBox,
                        _("No supported mounted filesystem was found for picon installation."),
                        type=MessageBox.TYPE_INFO, timeout=10
                    )
                    self.pending_package = None
                return

            self.install_settings_name = pkgname
            if pkgname.startswith('settings-'):
                self.check_settings = True
                self.startOpkgListInstalled(self.PLUGIN_PREFIX + 'settings-*')
            else:
                self.runSettingsInstall()
        elif self.type == self.REMOVE:
            self.doRemove(self.installFinished, pkgname)

    def doRemove(self, callback, pkgname):
        if not self._validPackageName(pkgname):
            return
        full_name = self.PLUGIN_PREFIX + pkgname
        command = "%s%s %s" % (
            self.opkg_remove, Opkg.opkgExtraDestinations(),
            shlex.quote(full_name)
        )
        self.session.openWithCallback(
            callback, Console, cmdlist=[command, "sync"], skin="Console_Pig"
        )

    def doInstall(self, callback, pkgname, extra=""):
        if not self._validPackageName(pkgname):
            return
        full_name = self.PLUGIN_PREFIX + pkgname
        command = "%s %s %s" % (
            self.opkg_install, extra, shlex.quote(full_name)
        )
        self.session.openWithCallback(
            callback, Console, cmdlist=[command, "sync"], skin="Console_Pig"
        )

    def runSettingsRemove(self, val):
        if val:
            self.doRemove(self.runSettingsInstall, self.remove_settings_name)
        else:
            self.pending_package = None

    def runSettingsInstall(self):
        if self.install_settings_name:
            self.doInstall(self.installFinished, self.install_settings_name)

    def startOpkgListInstalled(self, pkgname=PLUGIN_PREFIX + '*'):
        self.container.execute(self.opkg + Opkg.opkgExtraDestinations() + " list_installed '%s'" % pkgname)

    def startOpkgListAvailable(self):
        self.container.execute(self.opkg + Opkg.opkgExtraDestinations() + " list '" + self.PLUGIN_PREFIX + "*'")

    def startRun(self):
        listsize = self["list"].instance.size()
        self["list"].instance.hide()
        self.listWidth = listsize.width()
        self.listHeight = listsize.height()
        if self.type == self.DOWNLOAD:
            last_update = PluginDownloadBrowser.lastDownloadDate
            should_update = self.needupdate and (
                last_update is None or time() - last_update > 3600
            )
            if should_update:
                self.run = 0
                self.update_started = True
                self.container.execute(self.opkg + " update")
            else:
                self.run = 1
                self.update_started = False
                self.startOpkgListInstalled()
        elif self.type == self.REMOVE:
            self.run = 1
            self.startOpkgListInstalled()

    def installFinished(self, *args):
        pkgname = self.pending_package
        if hasattr(self, 'postInstallCall'):
            try:
                self.postInstallCall()
            except Exception as ex:
                print("[PluginBrowser] postInstallCall failed:", ex)
            self.resetPostInstall()

        try:
            os.unlink('/tmp/opkg.conf')
        except OSError:
            pass

        if pkgname:
            self.pluginlist = [
                plugin for plugin in self.pluginlist
                if len(plugin) > 3 and plugin[3] != pkgname
            ]
            self.plugins_changed = True
            if pkgname.startswith("settings-"):
                self.reload_settings = True
            if pkgname.startswith("softcams-"):
                self.check_softcams = True

        self.pending_package = None
        self.expanded = []
        self.updateList()
        self["list"].moveToIndex(0)

    def runFinished(self, retval):
        if self.remainingdata:
            final_fragment = self.remainingdata
            self.remainingdata = ""
            self.dataAvail((final_fragment + "\n").encode("utf-8"))

        if self.run == 0 and getattr(self, "update_started", False):
            self.update_started = False
            if retval == 0:
                PluginDownloadBrowser.lastDownloadDate = time()
            else:
                self["text"].setText(_("Unable to update plugin information (error %s).") % retval)
                return
        if self.check_settings:
            self.check_settings = False
            self.runSettingsInstall()
            return
        self.remainingdata = ""
        if self.run == 0:
            self.run = 1
            if self.type == self.DOWNLOAD:
                self.startOpkgListInstalled()
        elif self.run == 1 and self.type == self.DOWNLOAD:
            self.run = 2
            pluginlist = []
            self.pluginlist = pluginlist
            for plugin in Opkg.enumPlugins(self.PLUGIN_PREFIX):
                if plugin[0] not in self.installedplugins:
                    pluginlist.append(plugin + (plugin[0][15:],))
            if pluginlist:
                pluginlist.sort()
                self.updateList()
                self["text"].instance.hide()
                self["list"].instance.show()
            else:
                self["text"].setText(_("No new plugins found"))
        else:
            if self.pluginlist:
                self.updateList()
                self["text"].instance.hide()
                self["list"].instance.show()
            else:
                empty_message = _("No new plugins found") if self.type == self.DOWNLOAD else _("No installed plugins found")
                self["text"].setText(empty_message)

    def dataAvail(self, data):
        if isinstance(data, (bytes, bytearray)):
            chunk = data.decode("utf-8", errors="replace")
        else:
            chunk = str(data)
        output = self.remainingdata + chunk
        lines = output.split("\n")
        self.remainingdata = lines.pop() if lines else ""

        if self.check_settings:
            complete = next((line for line in lines if " - " in line), None)
            if complete:
                self.check_settings = False
                self.remove_settings_name = complete.split(" - ", 1)[0].replace(
                    self.PLUGIN_PREFIX, "", 1
                )
                self.session.openWithCallback(
                    self.runSettingsRemove, MessageBox,
                    _('You already have a channel list installed,\nwould you like to remove\n"%s"?')
                    % self.remove_settings_name
                )
            return

        if self.run == 1:
            for line in lines:
                plugin = line.split(" - ", 2)
                if len(plugin) < 2:
                    continue
                package_name = plugin[0].strip()
                if package_name.endswith(('-dev', '-staticdev', '-dbg', '-doc', '-src')):
                    continue
                if package_name in self.installedplugins:
                    continue
                if self.type == self.DOWNLOAD:
                    self.installedplugins.append(package_name)
                else:
                    if len(plugin) == 2:
                        plugin.append("")
                    plugin.append(package_name[len(self.PLUGIN_PREFIX):])
                    self.pluginlist.append(plugin)

    def updateList(self):
        list = []
        expandableIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/expandable-plugins.png"))
        expandedIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/expanded-plugins.png"))
        verticallineIcon = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/verticalline-plugins.png"))

        self.plugins = {}
        for x in self.pluginlist:
            split = x[3].split('-', 1)
            if len(split) < 2:
                continue
            if split[0] not in self.plugins:
                self.plugins[split[0]] = []

            self.plugins[split[0]].append((PluginDescriptor(name=x[3], description=x[2], icon=verticallineIcon), split[1], x[1]))

        for x in self.plugins.keys():
            if x in self.expanded:
                list.append(PluginCategoryComponent(x, expandedIcon, self.listWidth))
                list.extend([PluginDownloadComponent(plugin[0], plugin[1], plugin[2], self.listWidth) for plugin in self.plugins[x]])
            else:
                list.append(PluginCategoryComponent(x, expandableIcon, self.listWidth))
        self.list = list
        self["list"].l.setList(list)
