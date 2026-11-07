from Components.Converter.Converter import Converter
from Components.Element import cached


class Combine(Converter):
	SINGLE_SOURCE = False

	def __init__(self, arg=None, func=None):
		Converter.__init__(self, arg)
		# No assert: if func is missing (skin misconfiguration) fall back
		# to a no-op callable so getValue returns None instead of raising
		# AssertionError during skin parse (fatal under Py 3.14 / OE-master).
		self.func = func if callable(func) else (lambda sources: None)

	@cached
	def getValue(self):
		try:
			return self.func(self.sources)
		except Exception:
			return None

	value = property(getValue)
