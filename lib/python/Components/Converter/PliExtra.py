from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll
from enigma import eConsoleAppContainer
import os
import shutil


class PliExtra(Poll, Converter):
	TEMPERATURE = 0
	HDDTEMP = 1
	CPULOAD = 2
	CPUSPEED = 3
	FANINFO = 4
	UPTIME = 5

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.container = None
		type = type.split(",")
		self.short_list = True
		self.list = []
		self.shortFormat = "Short" in type
		if "CPULoad" in type:
			self.type = self.CPULOAD
		elif "CPUSpeed" in type:
			self.type = self.CPUSPEED
		elif "Temperature" in type:
			self.type = self.TEMPERATURE
		elif "Uptime" in type:
			self.type = self.UPTIME
		elif "HDDTemp" in type:
			self.type = self.HDDTEMP
			self.hddtemp_output = b""
			self.hddtemp = "Waiting for HDD Temp Data..."
			self._start_hddtemp()
		elif "FanInfo" in type:
			self.type = self.FANINFO
		else:
			self.type = self.CPULOAD  # safe default

		if "HDDTemp" in type:
			self.poll_interval = 500
		else:
			self.poll_interval = 7000
		self.poll_enabled = True

	# ------------------------------------------------------------------ HDD temp
	def _start_hddtemp(self):
		# Reset buffer each run so a stale failure cannot poison the next one.
		self.hddtemp_output = b""
		if not shutil.which("hddtemp"):
			self.hddtemp = "HDD Temp: N/A"
			return
		try:
			self.container = eConsoleAppContainer()
			self.container.appClosed.append(self.runFinished)
			self.container.dataAvail.append(self.dataAvail)
			self.container.execute("hddtemp -n -q /dev/sda")
		except Exception:
			self.container = None
			self.hddtemp = "HDD Temp: N/A"

	def dataAvail(self, data):
		# Enigma2 builds may pass bytes or str. Normalise to bytes.
		try:
			if isinstance(data, str):
				data = data.encode("utf-8", "ignore")
			elif not isinstance(data, (bytes, bytearray)):
				data = bytes(data)
		except Exception:
			return
		if not isinstance(self.hddtemp_output, (bytes, bytearray)):
			self.hddtemp_output = b""
		self.hddtemp_output += bytes(data)

	def runFinished(self, retval):
		try:
			raw = self.hddtemp_output
			if not isinstance(raw, (bytes, bytearray)):
				raw = b""
			temp = bytes(raw).decode("utf-8", "ignore").strip()
		except Exception:
			temp = ""
		self.hddtemp_output = b""
		self.container = None

		if not temp:
			self.hddtemp = "HDD Temp: N/A"
			self.changed((self.CHANGED_POLL,))
			return
		low = temp.lower()
		if "no such file" in low or "not found" in low or "command not found" in low or "error" in low:
			self.hddtemp = "HDD Temp: N/A"
			self.changed((self.CHANGED_POLL,))
			return
		# hddtemp -n may output "34" or "34 C" or "34*C"
		num = ""
		for ch in temp:
			if ch.isdigit() or ch == "-":
				num += ch
			elif num:
				break
		try:
			t = int(num)
		except (ValueError, TypeError):
			self.hddtemp = "HDD Temp: N/A"
			self.changed((self.CHANGED_POLL,))
			return
		if t > 0:
			self.hddtemp = "HDD Temp: %s\u00b0C" % t
		else:
			self.hddtemp = "HDD idle or N/A"
		self.changed((self.CHANGED_POLL,))

	# ------------------------------------------------------------------ helpers
	def _read_file(self, path):
		try:
			with open(path, "r", errors="ignore") as f:
				return f.read().strip()
		except Exception:
			return ""

	def _to_int(self, s, base=10, default=None):
		try:
			return int(s, base)
		except (ValueError, TypeError):
			return default

	# ------------------------------------------------------------------ text
	@cached
	def getText(self):
		try:
			if self.type == self.CPULOAD:
				load = self._read_file("/proc/loadavg")
				if load:
					cpuload = load[:4].replace("\n", "").replace(" ", "")
					return "CPU Load: %s" % cpuload
				return ""

			elif self.type == self.TEMPERATURE:
				systemp = ""
				cputemp = ""
				thermal = self._read_file("/sys/class/thermal/thermal_zone0/temp")
				if thermal:
					v = self._to_int(thermal)
					if v is not None:
						cputemp = "%d\u00b0C" % (v // 1000)
				if not cputemp:
					val = self._read_file("/proc/stb/sensors/temp0/value")
					if val:
						systemp = "Sys Temp: %s\u00b0C" % val
					else:
						val = self._read_file("/proc/stb/fp/temp_sensor")
						if val:
							systemp = "Board: %s\u00b0C" % val
				if not cputemp:
					val = self._read_file("/proc/stb/fp/temp_sensor_avs")
					if val:
						cputemp = "%s\u00b0C" % val
				if systemp == "" and cputemp == "":
					return "Temperature: N/A"
				if systemp == "":
					return "CPU Temp: %s" % cputemp
				if cputemp == "":
					return systemp
				return "%s CPU: %s" % (systemp, cputemp)

			elif self.type == self.HDDTEMP:
				return self.hddtemp

			elif self.type == self.CPUSPEED:
				cpuspeed = None
				for line in self._read_file("/proc/cpuinfo").splitlines():
					parts = [x.strip() for x in line.split(":")]
					if len(parts) >= 2 and parts[0] == "cpu MHz":
						try:
							cpuspeed = "%1.0f" % float(parts[1])
							break
						except (ValueError, TypeError):
							pass
				if cpuspeed is None:
					freq = self._read_file("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")
					if not freq:
						freq = self._read_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
					if freq:
						v = self._to_int(freq)
						cpuspeed = str(v // 1000) if v is not None else "-"
					else:
						cpuspeed = "-"
				return "CPU Speed: %s MHz" % cpuspeed

			elif self.type == self.FANINFO:
				fs = self._read_file("/proc/stb/fp/fan_speed")
				fv_raw = self._read_file("/proc/stb/fp/fan_vlt")
				fp_raw = self._read_file("/proc/stb/fp/fan_pwm")
				fv = ""
				fp = ""
				if fv_raw:
					v = self._to_int(fv_raw, 16)
					if v is not None:
						fv = str(v)
				if fp_raw:
					v = self._to_int(fp_raw, 16)
					if v is not None:
						fp = str(v)
				if not fs:
					return "Fan Info: N/A"
				if self.shortFormat:
					return "%s - %sV - P:%s" % (fs, fv, fp)
				return "Speed: %s V: %s PWM: %s" % (fs, fv, fp)

			elif self.type == self.UPTIME:
				uptime_info = self._read_file("/proc/uptime").split()
				if not uptime_info:
					return "Uptime: N/A"
				try:
					total_seconds = float(uptime_info[0])
				except (ValueError, TypeError):
					return "Uptime: N/A"
				MINUTE = 60
				HOUR = MINUTE * 60
				DAY = HOUR * 24
				days = int(total_seconds // DAY)
				hours = int(total_seconds % DAY // HOUR)
				minutes = int(total_seconds % HOUR // MINUTE)
				seconds = int(total_seconds % MINUTE)
				if self.shortFormat:
					return "Uptime: %sd %sh %sm %ss" % (days, hours, minutes, seconds)
				uptime = ""
				if days > 0:
					uptime += "%d %s, " % (days, "day" if days == 1 else "days")
				if uptime or hours > 0:
					uptime += "%d %s, " % (hours, "hr" if hours == 1 else "hrs")
				if uptime or minutes > 0:
					uptime += "%d %s" % (minutes, "min" if minutes == 1 else "mins")
				return "Uptime: %s" % uptime

			return ""
		except Exception:
			return ""

	text = property(getText)

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			try:
				self.downstream_elements.changed(what)
			except Exception:
				pass
