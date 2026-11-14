from Components.GUIComponent import GUIComponent
from enigma import eListboxPythonStringContent, eListbox


class MenuList(GUIComponent):
	def __init__(self, list, enableWrapAround=True, content=eListboxPythonStringContent):
		GUIComponent.__init__(self)
		self.l = content()
		self.onSelectionChanged = []
		self.setList(list)
		self.enableWrapAround = enableWrapAround

	def getCurrent(self):
		return self.l.getCurrentSelection()

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		if self.enableWrapAround:
			self.instance.setWrapAround(True)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def selectionChanged(self):
		for f in self.onSelectionChanged:
			f()

	def getSelectionIndex(self):
		return self.l.getCurrentSelectionIndex()

	def getSelectedIndex(self):
		return self.l.getCurrentSelectionIndex()

	def setList(self, list):
		self.list = list
		self.l.setList(self.list)

	def moveToIndex(self, idx):
		if self.instance is not None:
			self.instance.moveSelectionTo(idx)

	# --- OpenATV compat: standard go* methods ---
	def goTop(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveTop)

	def goPageUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageUp)

	def goLineUp(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveUp)

	def goLineDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveDown)

	def goPageDown(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.pageDown)

	def goBottom(self):
		if self.instance is not None:
			self.instance.moveSelection(self.instance.moveEnd)

	def getCurrentIndex(self):
		return self.getSelectionIndex()

	def setCurrentIndex(self, idx):
		self.moveToIndex(idx)

	def getTopIndex(self):
		return self.instance.getTopIndex() if self.instance else -1

	def setTopIndex(self, idx):
		if self.instance is not None:
			self.instance.setTopIndex(idx)

	def enableAutoNavigation(self, enabled):
		if self.instance is not None:
			self.instance.enableAutoNavigation(enabled)
	# --- end OpenATV compat ---

	# Old OpenPLi method names (mapped to the new ones)
	def pageUp(self):
		self.goPageUp()

	def pageDown(self):
		self.goPageDown()

	def up(self):
		self.goLineUp()

	def down(self):
		self.goLineDown()

	def top(self):
		self.goTop()

	def bottom(self):
		self.goBottom()

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)
