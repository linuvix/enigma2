from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached


class PliCPU(Converter, object):
	CPU_ALL = -2
	CPU_TOTAL = -1

	def __init__(self, type):
		Converter.__init__(self, type)
		self.percentlist = []
		self.pfmt = "%3d%%"
		if not type or type == "Total":
			self.type = self.CPU_TOTAL
			self.sfmt = "$0"
		elif len(type) == 1 and type[0].isdigit():
			self.type = int(type)
			self.sfmt = "$" + type
			self.pfmt = "%d"
		else:
			self.type = self.CPU_ALL
			self.sfmt = str(type)
			try:
				cpus = cpuUsageMonitor.getCpusCount()
			except Exception:
				cpus = -1
			if cpus > -1:
				pos = 0
				while True:
					pos = self.sfmt.find("$", pos)
					if pos == -1:
						break
					if pos < len(self.sfmt) - 1 and self.sfmt[pos + 1].isdigit() and int(self.sfmt[pos + 1]) > cpus:
						self.sfmt = self.sfmt.replace("$" + self.sfmt[pos + 1], "")
					pos += 1

	def doSuspend(self, suspended):
		try:
			if suspended:
				cpuUsageMonitor.disconnectCallback(self.gotPercentage)
			else:
				cpuUsageMonitor.connectCallback(self.gotPercentage)
		except Exception:
			pass

	def gotPercentage(self, list):
		# Normalise to a plain list of ints, regardless of what the monitor passes.
		try:
			self.percentlist = [int(x) for x in list]
		except Exception:
			self.percentlist = []
		self.changed((self.CHANGED_POLL,))

	@cached
	def getText(self):
		res = self.sfmt[:]
		plist = self.percentlist if self.percentlist else [0, 0, 0]
		for i in range(len(plist)):
			try:
				val = int(plist[i])
			except Exception:
				val = 0
			if val < 0:
				val = 0
			elif val > 100:
				val = 100
			res = res.replace("$" + str(i), self.pfmt % val)

		res = res.replace("$?", "%d" % (len(plist) - 1))
		return res

	@cached
	def getValue(self):
		plist = self.percentlist
		if self.type in range(len(plist)):
			i = self.type
		else:
			i = 0
		try:
			value = int(plist[i])
		except (IndexError, ValueError, TypeError):
			value = 0
		if value < 0:
			value = 0
		elif value > 100:
			value = 100
		return value

	text = property(getText)
	value = property(getValue)
	range = 100


class CpuUsageMonitor(Poll, object):

	def __init__(self):
		Poll.__init__(self)
		self.__callbacks = []
		self.__curr_info = self.getCpusInfo()
		self.poll_interval = 1000

	def getCpusCount(self):
		return len(self.__curr_info) - 1

	def getCpusInfo(self):
		res = []
		try:
			with open("/proc/stat", "r", errors="ignore") as fd:
				for l in fd:
					if not l.startswith("cpu"):
						continue
					tmp = l.split()
					# Need at least cpu,user,nice,system,idle -> 5 tokens + label
					if len(tmp) < 6:
						continue
					nums = []
					ok = True
					for x in tmp[1:]:
						try:
							nums.append(int(x))
						except (ValueError, TypeError):
							ok = False
							break
					if not ok or len(nums) < 4:
						continue
					total = sum(nums)
					idle = nums[3]
					iowait = nums[4] if len(nums) > 4 else 0
					busy = total - idle - iowait
					res.append([tmp[0], total, busy])
		except Exception:
			pass
		return res

	def poll(self):
		prev_info, self.__curr_info = self.__curr_info, self.getCpusInfo()
		if not len(self.__callbacks):
			return
		info = []
		for i in range(len(self.__curr_info)):
			try:
				delta_total = self.__curr_info[i][1] - prev_info[i][1]
				delta_busy = self.__curr_info[i][2] - prev_info[i][2]
				if delta_total <= 0:
					p = 0
				else:
					p = (100 * delta_busy) // delta_total
					if p < 0:
						p = 0
					elif p > 100:
						p = 100
			except (ZeroDivisionError, IndexError):
				p = 0
			info.append(p)

		# Snapshot callbacks so a callback can disconnect safely.
		for f in list(self.__callbacks):
			try:
				f(info)
			except Exception:
				pass

	def connectCallback(self, func):
		if func not in self.__callbacks:
			self.__callbacks.append(func)
		if not self.poll_enabled:
			self.poll()
			self.poll_enabled = True

	def disconnectCallback(self, func):
		if func in self.__callbacks:
			self.__callbacks.remove(func)
		if not len(self.__callbacks) and self.poll_enabled:
			self.poll_enabled = False


cpuUsageMonitor = CpuUsageMonitor()
