from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Components.NimManager import nimmanager
from skin import parameters


# Enigma2's skin engine expects literal "\c<argb>" escape sequences inside
# converter text.  Python >= 3.12 turns "\c" into an invalid-escape warning
# (and 3.14 may make it a hard error in some builds), so the string MUST be
# built from a raw literal or the skin renderer receives the wrong bytes.
COLOR_ESC = r"\c%08x"

_DEFAULT_COLORS = (0x0000FF00, 0x00FFFF00, 0x007F7F7F)

# Dreambox frontends that report a bogus small non-zero AGC even without lock.
# Only these are allowed to fall back to an SNR-derived display value.
_BOGUS_AGC_FRONTENDS = ("Si2166D", "Si2169D")


def _tr(s):
	# gettext shortcut, safe if _ is not yet installed in __builtins__
	try:
		return _(s)
	except NameError:
		return s


class FrontendInfo(Converter):
	BER = 0
	SNR = 1
	AGC = 2
	LOCK = 3
	SNRdB = 4
	SLOT_NUMBER = 5
	TUNER_TYPE = 6
	STRING = 7
	USE_TUNERS_STRING = 8

	def __init__(self, type):
		Converter.__init__(self, type)
		self.space_for_tuners = 10
		self.space_for_tuners_with_spaces = 6
		self.show_all_non_link_tuners = True
		if type == "BER":
			self.type = self.BER
		elif type == "SNR":
			self.type = self.SNR
		elif type == "SNRdB":
			self.type = self.SNRdB
		elif type == "AGC":
			self.type = self.AGC
		elif type == "NUMBER":
			self.type = self.SLOT_NUMBER
		elif type == "TYPE":
			self.type = self.TUNER_TYPE
		elif type.startswith("STRING"):
			self.type = self.STRING
			parts = type.split(",")
			if len(parts) > 1 and parts[1].strip():
				try:
					self.space_for_tuners = int(parts[1])
				except (ValueError, TypeError):
					pass
			if len(parts) > 2 and parts[2].strip():
				try:
					self.space_for_tuners_with_spaces = int(parts[2])
				except (ValueError, TypeError):
					pass
			if len(parts) > 3:
				self.show_all_non_link_tuners = (parts[3] == "True")
		elif type == "USE_TUNERS_STRING":
			self.type = self.USE_TUNERS_STRING
		else:
			self.type = self.LOCK

	# ------------------------------------------------------------------ helpers
	@staticmethod
	def _swap_snr():
		try:
			return bool(config.usage.swap_snr_on_osd.value)
		except Exception:
			return False

	@staticmethod
	def _colors():
		try:
			c = parameters.get("FrontendInfoColors", _DEFAULT_COLORS)
			if not c or len(c) < 3:
				return _DEFAULT_COLORS
			return c
		except Exception:
			return _DEFAULT_COLORS

	def _src(self):
		# Some Python 3.14 / OE-master builds instantiate converters during
		# the very first skin parse, before a service is assigned.
		return getattr(self, "source", None)

	def _tuner_mask(self):
		s = self._src()
		if s is None:
			return 0
		mask = getattr(s, "tuner_mask", None)
		if mask is None:
			return 0
		try:
			return int(mask)
		except (ValueError, TypeError):
			return 0

	def _slot_number(self):
		s = self._src()
		if s is None:
			return None
		return getattr(s, "slot_number", None)

	# ------------------------------------------------------------------ AGC
	def getAGC(self):
		s = self._src()
		if s is None:
			return None
		agc = getattr(s, "agc", None)
		if agc:
			try:
				agc = int(agc)
			except (ValueError, TypeError):
				agc = 0
			# Only the known Dreambox Si2166D/Si2169D frontends report a
			# bogus small non-zero AGC (seen: 89-124) without lock.  Any
			# other frontend that reports an AGC value is trusted as-is.
			ft = getattr(s, "frontend_type", None) or ""
			if not (ft in _BOGUS_AGC_FRONTENDS and 89 <= agc <= 124):
				return agc
		else:
			agc = 0

		# Derive a display value from SNR for the affected Dreambox tuners
		# (and for frontends that report no AGC at all).
		snr = getattr(s, "snr", None)
		if not snr:
			return agc if agc else None
		try:
			snr = int(snr)
		except (ValueError, TypeError):
			return None
		snrPercent = snr * 100.0 / 65535.0
		if snrPercent < 35:
			agcPercent = snrPercent * 1.8
		elif snrPercent < 70:
			agcPercent = 63 + ((snrPercent - 35) * 0.8)
		else:
			agcPercent = 91 + ((snrPercent - 70) * 0.3)
		return round(min(100, agcPercent) * 65535 / 100.0)

	# ------------------------------------------------------------------ text
	@cached
	def getText(self):
		s = self._src()
		if s is None:
			return _tr("N/A")

		percent = None
		swapsnr = self._swap_snr()
		colors = self._colors()

		if self.type == self.BER:
			count = getattr(s, "ber", None)
			if count is not None:
				try:
					return str(int(count))
				except (ValueError, TypeError):
					pass
			return _tr("N/A")

		elif self.type == self.AGC:
			percent = self.getAGC()

		elif (self.type == self.SNR and not swapsnr) or (self.type == self.SNRdB and swapsnr):
			percent = getattr(s, "snr", None)

		elif self.type == self.SNR or self.type == self.SNRdB:
			snr_db = getattr(s, "snr_db", None)
			if snr_db is not None:
				try:
					return _tr("%3.01f dB") % (float(snr_db) / 100.0)
				except (ValueError, TypeError):
					pass
			percent = getattr(s, "snr", None)

		elif self.type == self.TUNER_TYPE:
			return getattr(s, "frontend_type", None) or _tr("Unknown")

		elif self.type == self.STRING:
			string = ""
			current = self._slot_number()
			mask = self._tuner_mask()
			total = len(nimmanager.nim_slots)
			for n in nimmanager.nim_slots:
				if n.type and n.enabled:
					if n.slot == current:
						color = COLOR_ESC % colors[0]
					elif mask & (1 << n.slot):
						color = COLOR_ESC % colors[1]
					elif total <= self.space_for_tuners or n.isFBCRoot() or (self.show_all_non_link_tuners and not (n.isFBCLink() or n.config_mode == "loopthrough")):
						color = COLOR_ESC % colors[2]
					else:
						continue
					if string and total <= self.space_for_tuners_with_spaces:
						string += " "
					string += color + chr(ord("A") + n.slot)
			return string

		elif self.type == self.USE_TUNERS_STRING:
			string = ""
			current = self._slot_number()
			mask = self._tuner_mask()
			for n in nimmanager.nim_slots:
				if n.type and n.enabled:
					if n.slot == current:
						color = COLOR_ESC % colors[0]
					elif mask & (1 << n.slot):
						color = COLOR_ESC % colors[1]
					else:
						continue
					if string:
						string += " "
					string += color + chr(ord("A") + n.slot)
			return string

		if percent is None:
			return _tr("N/A")
		try:
			percent = int(percent)
		except (ValueError, TypeError):
			return _tr("N/A")
		if percent < 0:
			percent = 0
		elif percent > 65535:
			percent = 65535
		return "%d %%" % (percent * 100 // 65535)

	# ------------------------------------------------------------------ bool
	@cached
	def getBool(self):
		s = self._src()
		if s is None:
			return False
		swapsnr = self._swap_snr()
		if self.type == self.LOCK:
			lock = getattr(s, "lock", None)
			return bool(lock) if lock is not None else False
		elif self.type == self.BER:
			return getattr(s, "ber", None) is not None
		elif (self.type == self.SNR and not swapsnr) or (self.type == self.SNRdB and swapsnr):
			return getattr(s, "snr", None) is not None
		elif self.type == self.SNR or self.type == self.SNRdB:
			return getattr(s, "snr_db", None) is not None or getattr(s, "snr", None) is not None
		elif self.type == self.AGC:
			return self.getAGC() is not None
		elif self.type in (self.STRING, self.USE_TUNERS_STRING):
			try:
				return bool(self.getText())
			except Exception:
				return False
		return False

	# ------------------------------------------------------------------ value
	@cached
	def getValue(self):
		s = self._src()
		if s is None:
			return 0
		if self.type == self.AGC:
			agc = self.getAGC()
			return 0 if agc is None else int(agc)
		elif self.type == self.SNR:
			v = getattr(s, "snr", None) or 0
			try:
				return int(v)
			except (ValueError, TypeError):
				return 0
		elif self.type == self.BER:
			ber = getattr(s, "ber", None) or 0
			try:
				ber = int(ber)
			except (ValueError, TypeError):
				ber = 0
			return ber if ber < self.range else self.range
		elif self.type == self.TUNER_TYPE:
			t = getattr(s, "frontend_type", None)
			if t == "DVB-S":
				return 0
			elif t == "DVB-C":
				return 1
			elif t == "DVB-T":
				return 2
			elif t == "ATSC":
				return 3
			return -1
		elif self.type == self.SLOT_NUMBER:
			num = self._slot_number()
			if num is None:
				return -1
			try:
				return int(num)
			except (ValueError, TypeError):
				return -1
		return 0

	text = property(getText)
	boolean = property(getBool)
	value = property(getValue)
	range = 65535
