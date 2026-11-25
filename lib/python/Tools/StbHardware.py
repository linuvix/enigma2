from os import path
from fcntl import ioctl
from struct import pack, unpack
from time import time, localtime, gmtime


def _dbg(msg):
    # Route to eTrace/eDebug if available, otherwise print
    try:
        from enigma import eDebug
        eDebug("[StbHardware] %s" % msg)
    except Exception:
        print("[StbHardware] %s" % msg)


def getFPVersion():
    """
    Return the front-processor version as a string, or None if unavailable.
    Always returns str (or None) so callers don't get mixed int/str types.
    """
    ret = None
    # 1) Standard STB path
    try:
        with open("/proc/stb/fp/version", "r") as f:
            ret = f.read().strip()
            if not ret:
                ret = None
    except (IOError, OSError):
        pass
    # 2) Legacy DMM ioctl
    if ret is None:
        try:
            fp = open("/dev/dbox/fp0")
            try:
                ret = str(ioctl(fp.fileno(), 0))
            finally:
                fp.close()
        except (IOError, OSError):
            pass
    # 3) DM920 devicetree tag
    if ret is None:
        try:
            with open("/sys/firmware/devicetree/base/bolt/tag", "r") as f:
                ret = f.read().rstrip("\0").strip() or None
        except (IOError, OSError):
            pass
    if ret is None:
        _dbg("getFPVersion not available on this box")
    return ret


def setFPWakeuptime(wutime):
    wutime = int(wutime)
    # 1) Standard STB path
    try:
        with open("/proc/stb/fp/wakeup_time", "w") as f:
            f.write(str(wutime))
        return
    except (IOError, OSError):
        pass
    # 2) Legacy DMM ioctl
    try:
        fp = open("/dev/dbox/fp0")
        try:
            ioctl(fp.fileno(), 6, pack('L', wutime))
        finally:
            fp.close()
        return
    except (IOError, OSError):
        pass
    # 3) DM920 uses RTC wakealarm via /sys/class/rtc/rtc0
    try:
        with open("/sys/class/rtc/rtc0/wakealarm", "w") as f:
            f.write(str(wutime))
        return
    except (IOError, OSError):
        pass
    _dbg("setFPWakeuptime not available on this box")


def setRTCoffset(forsleep=None):
    """
    Write the RTC offset in seconds.

    If forsleep is not supplied, compute it from localtime vs gmtime:
        offset = (local_hour - gm_hour) * 3600  (sign-corrected for half-hour
        zones and DST because we use the actual UTC/LT delta, not a fixed
        constant).
    """
    if forsleep is None:
        # Seconds east of UTC (positive = local clock ahead of UTC).
        now = time()
        forsleep = int(round((localtime(now).tm_hour - gmtime(now).tm_hour) * 3600))
        # Guard against day-boundary wrapping (e.g. UTC 23:xx, local 00:xx).
        if forsleep > 12 * 3600:
            forsleep -= 24 * 3600
        elif forsleep < -12 * 3600:
            forsleep += 24 * 3600
    try:
        with open("/proc/stb/fp/rtc_offset", "w") as f:
            f.write(str(int(forsleep)))
        _dbg("set RTC offset to %s sec." % forsleep)
    except (IOError, OSError):
        _dbg("setRTCoffset not available on this box")


def setRTCtime(wutime):
    wutime = int(wutime)
    if path.exists("/proc/stb/fp/rtc_offset"):
        setRTCoffset()
    # 1) Standard STB path
    try:
        with open("/proc/stb/fp/rtc", "w") as f:
            f.write(str(wutime))
        return
    except (IOError, OSError):
        pass
    # 2) Legacy DMM ioctl
    try:
        fp = open("/dev/dbox/fp0")
        try:
            ioctl(fp.fileno(), 0x101, pack('L', wutime))
        finally:
            fp.close()
        return
    except (IOError, OSError):
        pass
    # 3) DM920 kernel RTC
    try:
        with open("/sys/class/rtc/rtc0/since_epoch", "w") as f:
            f.write(str(wutime))
        return
    except (IOError, OSError):
        pass
    _dbg("setRTCtime not available on this box")


def getFPWakeuptime():
    ret = 0
    # 1) Standard STB path
    try:
        with open("/proc/stb/fp/wakeup_time", "r") as f:
            ret = int(f.read().strip() or 0)
        return ret
    except (IOError, OSError, ValueError):
        pass
    # 2) Legacy DMM ioctl
    try:
        fp = open("/dev/dbox/fp0")
        try:
            ret = unpack('L', ioctl(fp.fileno(), 5, '    '))[0]
        finally:
            fp.close()
        return ret
    except (IOError, OSError):
        pass
    # 3) DM920 kernel RTC
    try:
        with open("/sys/class/rtc/rtc0/wakealarm", "r") as f:
            ret = int(f.read().strip() or 0)
        return ret
    except (IOError, OSError, ValueError):
        pass
    _dbg("getFPWakeuptime not available on this box")
    return ret


wasTimerWakeup = None


def getFPWasTimerWakeup():
    """
    Returns True if the last boot was caused by the RTC/FP alarm.

    DM920 fallback: read /sys/class/rtc/rtc0/wakealarm. The kernel clears the
    alarm once it fires, so a non-empty value here means an alarm is *still
    pending* — i.e. it did NOT wake us. We therefore treat a value whose
    timestamp is <= now (within a small grace window) as a timer wakeup, and
    anything else as a normal power-on. The result is memoised and the hardware
    flag is cleared on read so subsequent calls return False until re-armed.
    """
    global wasTimerWakeup
    if wasTimerWakeup is not None:
        return wasTimerWakeup
    wasTimerWakeup = False
    # 1) Standard STB path
    try:
        with open("/proc/stb/fp/was_timer_wakeup", "r") as f:
            wasTimerWakeup = bool(int(f.read().strip() or 0))
    except (IOError, OSError, ValueError):
        # 2) Legacy DMM ioctl
        try:
            fp = open("/dev/dbox/fp0")
            try:
                wasTimerWakeup = bool(unpack('B', ioctl(fp.fileno(), 9, ' '))[0])
            finally:
                fp.close()
        except (IOError, OSError):
            # 3) DM920 kernel RTC
            try:
                with open("/sys/class/rtc/rtc0/wakealarm", "r") as f:
                    alarm = int(f.read().strip() or 0)
                # If an alarm was scheduled and is now in the past (with a
                # 5-minute grace window for boot delay), assume it fired.
                now = int(time())
                wasTimerWakeup = bool(alarm) and (alarm <= now + 300)
            except (IOError, OSError, ValueError):
                _dbg("getFPWasTimerWakeup not available on this box")
    if wasTimerWakeup:
        clearFPWasTimerWakeup()
    return wasTimerWakeup


def clearFPWasTimerWakeup():
    # 1) Standard STB path
    try:
        with open("/proc/stb/fp/was_timer_wakeup", "w") as f:
            f.write('0')
        return
    except (IOError, OSError):
        pass
    # 2) Legacy DMM ioctl
    try:
        fp = open("/dev/dbox/fp0")
        try:
            ioctl(fp.fileno(), 10)
        finally:
            fp.close()
        return
    except (IOError, OSError):
        pass
    # 3) DM920 kernel RTC — clear wakealarm
    try:
        with open("/sys/class/rtc/rtc0/wakealarm", "w") as f:
            f.write('0')
        return
    except (IOError, OSError):
        pass
    _dbg("clearFPWasTimerWakeup not available on this box")