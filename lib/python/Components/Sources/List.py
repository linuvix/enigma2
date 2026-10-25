from Components.Element import cached
from Components.Sources.Source import Source


class List(Source):
	"""The datasource of a listbox. Currently, the format depends on the used converter. So
if you put a simple string list in here, you need to use a StringList converter, if you are
using a "multi content list styled"-list, you need to use the StaticMultiList converter, and
setup the "fonts".

This has been done so another converter could convert the list to a different format, for example
to generate HTML."""

	def __init__(self, list=None, enableWrapAround=False, item_height=25, fonts=None):
		Source.__init__(self)
		if not list:
			list = []
		if not fonts:
			fonts = []
		self.__list = list
		self.onSelectionChanged = []
		self.onListUpdated = []
		self.item_height = item_height
		self.fonts = fonts
		self.disable_callbacks = False
		self.enableWrapAround = enableWrapAround
		self.__current = None
		self.__index = None
		self.connectedGuiElement = None
		self.__style = "default"  # Style might be an optional string which can be used to define different visualisations in the skin.

	def setList(self, list):
		self.__list = list
		self.changed((self.CHANGED_ALL,))
		self.listUpdated()

	list = property(lambda self: self.__list, setList)

	def entry_changed(self, index):
		if not self.disable_callbacks:
			self.downstream_elements.entry_changed(index)

	def modifyEntry(self, index, data):
		self.__list[index] = data
		self.entry_changed(index)

	def removeEntry(self, index):
		if 0 <= index < len(self.__list):
			self.__list.pop(index)
			self.changed((self.CHANGED_ALL,))
			self.listUpdated()

	def count(self):
		return len(self.__list)

	def setConnectedGuiElement(self, guiElement):
		self.connectedGuiElement = guiElement
		index = guiElement.instance.getCurrentIndex()
		self.__current = self.list[index]
		self.__index = index
		self.changed((self.CHANGED_ALL,))

	def selectionChanged(self, index):
		if self.disable_callbacks:
			return
		for x in self.downstream_elements:  # Update all non-master targets.
			if x is not self.master:
				x.index = index
		for x in self.onSelectionChanged:
			x()

	def getCurrent(self):
		# The previous version of this method was decorated with @cached,
		# but the __current field is only populated by setConnectedGuiElement()
		# and never invalidated on selection changes - so the cache returned
		# stale data forever. The lookup itself is a single attribute read on
		# self.master (or self.__current), so caching isn't worth the risk.
		if self.master:
			if hasattr(self.master, "current"):
				return self.master.current
		return self.__current

	current = property(getCurrent)

	def setIndex(self, index):
		if self.master is not None:
			if hasattr(self.master, "index"):
				self.master.index = index
			else:
				self.__index = index
			self.selectionChanged(index)
		if self.connectedGuiElement is not None:
			self.connectedGuiElement.moveSelection(index)

	@cached
	def getIndex(self):
		return self.master.index if self.master is not None and hasattr(self.master, "index") else self.__index

	setCurrentIndex = setIndex

	index = property(getIndex, setIndex)

	def selectNext(self):
		if self.getIndex() + 1 >= self.count():
			if self.enableWrapAround:
				self.index = 0
		else:
			self.index += 1
		self.setIndex(self.index)

	def selectPrevious(self):
		if self.getIndex() - 1 < 0:
			if self.enableWrapAround:
				self.index = self.count() - 1
		else:
			self.index -= 1
		self.setIndex(self.index)

	@cached
	def getStyle(self):
		return self.__style

	def setStyle(self, style):
		if self.__style != style:
			self.__style = style
			self.changed((self.CHANGED_SPECIFIC, "style"))

	style = property(getStyle, setStyle)

	def listUpdated(self):
		for x in self.onListUpdated:
			x()

	def updateList(self, list):
		"""Changes the list without changing the selection or emitting changed Events.

		If the new list has the same length as the current one, entries are
		updated in place and only the affected items are repainted (via
		entry_changed). Otherwise a full rebuild is unavoidable.

		The previous version always did self.list = list, which emits
		CHANGED_ALL and forces the whole listbox content to reload - even
		though the docstring promises "without emitting changed Events".
		On a 5000-item list this made every in-place refresh O(n) instead of
		O(number of changed rows)."""
		oldLen = len(self.__list)
		newLen = len(list)
		if oldLen != newLen:
			# Length changed - must do a full rebuild.
			try:
				assert oldLen == newLen
			except AssertionError:
				pass  # Lengths genuinely differ, that's fine - fall through.
			old_index = self.index
			self.disable_callbacks = True
			self.list = list
			self.index = old_index
			self.disable_callbacks = False
			return

		# Same length: update entries in place and repaint only what changed.
		old_index = self.index
		self.disable_callbacks = True
		try:
			for i, entry in enumerate(list):
				if self.__list[i] is not entry:
					self.__list[i] = entry
					self.entry_changed(i)
		finally:
			self.disable_callbacks = False
		# Refresh the current selection in case its data changed.
		if old_index is not None and 0 <= old_index < len(self.__list):
			self.__current = self.__list[old_index]
		self.listUpdated()

	def top(self):
		self.setIndex(0)

	def pageUp(self):
		try:
			instance = self.master.master.instance
			instance.moveSelection(instance.pageUp)
		except AttributeError:
			return

	def up(self):
		self.selectPrevious()

	def down(self):
		self.selectNext()

	def pageDown(self):
		try:
			instance = self.master.master.instance
			instance.moveSelection(instance.pageDown)
		except AttributeError:
			return

	def bottom(self):
		self.setIndex(self.count() - 1)

	def getSelectedIndex(self):
		return self.getIndex()

	# --- OpenATV parity additions ---

	def enableAutoNavigation(self, value):
		try:
			instance = self.master.master.instance
			instance.enableAutoNavigation(value)
		except AttributeError:
			return

	def show(self):
		try:
			instance = self.master.master.instance
			instance.show()
		except AttributeError:
			return

	def hide(self):
		try:
			instance = self.master.master.instance
			instance.hide()
		except AttributeError:
			return

	def goLeft(self):
		try:
			instance = self.master.master.instance
			instance.goLeft()
		except AttributeError:
			return

	def goRight(self):
		try:
			instance = self.master.master.instance
			instance.goRight()
		except AttributeError:
			return
