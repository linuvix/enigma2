# -*- coding: utf-8 -*-

from enigma import iServiceInformation, iPlayableService, eDVBCI_UI
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Components.SystemInfo import SystemInfo
from Tools.Transponder import ConvertToHumanReadable
from Tools.GetEcmInfo import GetEcmInfo
from Components.Converter.Poll import Poll
from Tools.Directories import pathExists
from skin import parameters
import os
import re
from urllib.parse import urlparse

# Fix: Import gettext for _() function
try:
    from gettext import gettext as _
except ImportError:
    def _(text):
        return text

# Get CI instance
try:
    dvbCIUI = eDVBCI_UI.getInstance()
except Exception:
    dvbCIUI = None

# Detect DreamBox (lazy: evaluated once at import, safe for DM920)
IS_DREAMBOX = False
try:
    with open("/proc/stb/info/model", "r") as f:
        model = f.read().strip().upper()
        if "DM" in model or "DREAM" in model:
            IS_DREAMBOX = True
except Exception:
    pass

# CAID data - complete list
caid_data = (
    ("0x4a30", "0x4a30", "DVN-JET", "TB", "DVN", False),
    ("0x4ad2", "0x4ad3", "STREAMGUARD", "SM", "SMG", False),
    ("0x4a02", "0x4a02", "TONGFANG", "TF", "TGF", False),
    ("0x100", "0x1ff", "Seca", "S", "SECA", True),
    ("0x500", "0x5ff", "Via", "V", "VIA", True),
    ("0x600", "0x6ff", "Irdeto", "I", "IRD", True),
    ("0x900", "0x9ff", "NDS", "Nd", "NDS", True),
    ("0xb00", "0xbff", "Conax", "Co", "CONAX", True),
    ("0xd00", "0xdff", "CryptoW", "Cw", "CRW", True),
    ("0xe00", "0xeff", "PowerVU", "P", "PV", False),
    ("0x1000", "0x10FF", "Tandberg", "TB", "TAND", False),
    ("0x1700", "0x17ff", "Beta", "B", "BETA", True),
    ("0x1800", "0x18ff", "Nagra", "N", "NAGRA", True),
    ("0x2600", "0x2600", "Biss", "Bi", "BiSS", False),
    ("0x2700", "0x2710", "Dre3", "D3", "DRE3", False),
    ("0x4ae0", "0x4ae1", "Dre", "D", "DRE", False),
    ("0x4aee", "0x4aee", "BulCrypt", "B1", "BUL", False),
    ("0x5581", "0x5581", "BulCrypt", "B2", "BUL", False),
    ("0x5601", "0x5604", "Verimatrix", "Vm", "VER", False)
)

# Stream type to codec map
codec_data = {
    -1: "N/A",
    0: "MPEG2",
    1: "AVC",
    2: "H263",
    3: "VC1",
    4: "MPEG4-VC",
    5: "VC1-SM",
    6: "MPEG1",
    7: "HEVC",
    8: "VP8",
    9: "VP9",
    10: "XVID",
    11: "N/A 11",
    12: "N/A 12",
    13: "DIVX 3.11",
    14: "DIVX 4",
    15: "DIVX 5",
    16: "AVS",
    17: "N/A 17",
    18: "VP6",
    19: "N/A 19",
    20: "N/A 20",
    21: "SPARK",
    22: "HEVC",
    40: "AVS2",
    41: "AVS3",
    42: "N/A 42",
    43: "N/A 43",
    44: "N/A 44",
    45: "N/A 45",
    46: "N/A 46",
    47: "N/A 47",
    48: "N/A 48",
    49: "N/A 49",
    50: "N/A 50",
}

# Gamma data
gamma_data = {
    -1: "",
    0: "SDR",
    1: "HDR",
    2: "HDR10",
    3: "HLG",
}

# IPTV protocol prefixes (used by both detection and parsing)
IPTV_PROTOCOLS = ('http://', 'https://', 'rtsp://', 'rtmp://', 'udp://', 'rtp://', 'mms://')

# Precompiled regexes (avoid recompiling every poll)
_RE_IPTV_TRIM_CHANNEL = re.compile(r'^(.*):[^:/\\]+$')
_RE_IPTV_TRIM_CHANNEL2 = re.compile(r'^(.*)(:[^:/\\?]+)$')
_RE_URL_PATTERNS = (
    re.compile(r'(https?://[^\s]+)', re.IGNORECASE),
    re.compile(r'(rtsp://[^\s]+)', re.IGNORECASE),
    re.compile(r'(rtmp://[^\s]+)', re.IGNORECASE),
    re.compile(r'(udp://[^\s]+)', re.IGNORECASE),
    re.compile(r'(rtp://[^\s]+)', re.IGNORECASE),
    re.compile(r'(mms://[^\s]+)', re.IGNORECASE),
)

# Extended stream-type / container hints (used by IPTV parsing)
_RE_STREAM_HINTS = (
    ("m3u8", "HLS"),
    ("hls", "HLS"),
    ("mpd", "DASH"),
    ("dash", "DASH"),
    ("ism", "SmoothStreaming"),
    ("type=ts", "TS"),
    ("format=ts", "TS"),
)

_RE_CONTAINER_HINTS = (
    (".m3u8", "HLS"),
    (".mpd", "DASH"),
    (".ism", "ISM"),
    (".ts", "TS"),
    (".mp4", "MP4"),
    (".mkv", "MKV"),
    (".flv", "FLV"),
    (".avi", "AVI"),
    (".webm", "WebM"),
)

# Audio codec names. NOTE: sAudioType is NOT present in this tree's
# iServiceInformation enum, so _audio_codec_name() returns "".
_AUDIO_CODEC_NAMES = {
    0: "MPEG",
    1: "AC3",
    2: "AC4",
    3: "DDP",
    4: "AAC",
    5: "AACHE",
    6: "DTS",
    7: "DTSHD",
    8: "LPCM",
    9: "DRA",
}


def addspace(text):
    if text:
        text += " "
    return text


def _safe_int(value, default=0):
    """Safely convert to int"""
    if value is None:
        return default
    if isinstance(value, bytes):
        try:
            if value.startswith(b'0x') or value.startswith(b'0X'):
                return int(value, 16)
            return int(value)
        except Exception:
            return default
    if isinstance(value, str):
        try:
            if value.startswith('0x') or value.startswith('0X'):
                return int(value, 16)
            return int(value)
        except Exception:
            return default
    try:
        return int(value)
    except Exception:
        return default


def _safe_str(value, default=""):
    """Safely convert to string"""
    if value is None:
        return default
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8', errors='ignore')
        except Exception:
            return str(value)
    return str(value)


def _read_proc_int(path, base=10):
    """Read a single int from a /proc or /sys file, returning None on any failure."""
    try:
        with open(path, "r") as f:
            return int(f.read().strip(), base)
    except Exception:
        return None


class PliExtraInfo(Poll, Converter):
    """Full featured PliExtraInfo for DreamBox DM920 with IPTV support.

    Crypto fixes ported from OpenViX commits:
      4bd6d69 - reject /tmp/ecm.info that belongs to another service (ECM PID check)
      2a9c832 - don't display encrypted data for an FTA service (sIsCrypted gate)
      a53015a - match ecm.info to its service by (CAID, ECM PID) pair, FIFO-capped
                cache, distinguish "missing" from a real 0x0000
    """

    # Type constants - crypto
    CryptoInfo = "CryptoInfo"
    CryptoBar = "CryptoBar"
    CryptoSpecial = "CryptoSpecial"
    CurrentCrypto = "CurrentCrypto"
    CryptoNameCaid = "CryptoNameCaid"

    # Video
    Resolution = "Resolution"
    ResolutionString = "ResolutionString"
    VideoCodec = "VideoCodec"
    Gamma = "Gamma"

    # Aggregate
    Settings = "Settings"
    All = "All"
    PIDInfo = "PIDInfo"
    ServiceInfo = "ServiceInfo"

    # Transponder
    TransponderInfo = "TransponderInfo"
    TransponderFrequency = "TransponderFrequency"
    TransponderSymbolRate = "TransponderSymbolRate"
    TransponderPolarization = "TransponderPolarization"
    TransponderFEC = "TransponderFEC"
    TransponderModulation = "TransponderModulation"
    OrbitalPosition = "OrbitalPosition"
    TunerType = "TunerType"
    TunerSystem = "TunerSystem"
    OrbitalPositionOrTunerSystem = "OrbitalPositionOrTunerSystem"
    TerrestrialChannelNumber = "TerrestrialChannelNumber"
    TransponderInfoMisPls = "TransponderInfoMisPls"
    TransponderName = "TransponderName"

    # Service
    ServiceRef = "ServiceRef"
    ProviderName = "ProviderName"

    # IPTV specific types
    IPTVInfo = "IPTVInfo"
    IPTVUrl = "IPTVUrl"
    IPTVStreamType = "IPTVStreamType"
    IPTVHost = "IPTVHost"
    IPTVProtocol = "IPTVProtocol"
    IPTVPort = "IPTVPort"
    IPTVPath = "IPTVPath"
    IPTVContainer = "IPTVContainer"
    IPTVAudioCodec = "IPTVAudioCodec"
    IPTVAudioLang = "IPTVAudioLang"
    IPTVBitrate = "IPTVBitrate"
    IPTVSummary = "IPTVSummary"
    IPTVIsIPTV = "IPTVIsIPTV"

    # Empty ecm data sentinel. 4-tuple, matching GetEcmInfo.EMPTY_ECM_INFO.
    NO_ECM_DATA = ("", "0", "0", "0")

    def __init__(self, type):
        Converter.__init__(self, type)
        Poll.__init__(self)
        self.type = type
        self.poll_interval = 1000
        self.poll_enabled = True

        # CA table for boolean checks
        self.ca_table = (
            ("CryptoCaidDvnAvailable", "TB", False),
            ("CryptoCaidSmsxAvailable", "SM", False),
            ("CryptoCaidTongfangAvailable", "TF", False),
            ("CryptoCaidSecaAvailable", "S", False),
            ("CryptoCaidViaAvailable", "V", False),
            ("CryptoCaidIrdetoAvailable", "I", False),
            ("CryptoCaidNDSAvailable", "Nd", False),
            ("CryptoCaidConaxAvailable", "Co", False),
            ("CryptoCaidCryptoWAvailable", "Cw", False),
            ("CryptoCaidPowerVUAvailable", "P", False),
            ("CryptoCaidBetaAvailable", "B", False),
            ("CryptoCaidNagraAvailable", "N", False),
            ("CryptoCaidBissAvailable", "Bi", False),
            ("CryptoCaidDre3Available", "D3", False),
            ("CryptoCaidDreAvailable", "D", False),
            ("CryptoCaidBulCrypt1Available", "B1", False),
            ("CryptoCaidBulCrypt2Available", "B2", False),
            ("CryptoCaidVerimatrixAvailable", "Vm", False),
            ("CryptoCaidTandbergAvailable", "TB", False),
            ("CryptoCaidDvnSelected", "TB", True),
            ("CryptoCaidSmsxSelected", "SM", True),
            ("CryptoCaidTongfangSelected", "TF", True),
            ("CryptoCaidSecaSelected", "S", True),
            ("CryptoCaidViaSelected", "V", True),
            ("CryptoCaidIrdetoSelected", "I", True),
            ("CryptoCaidNDSSelected", "Nd", True),
            ("CryptoCaidConaxSelected", "Co", True),
            ("CryptoCaidCryptoWSelected", "Cw", True),
            ("CryptoCaidPowerVUSelected", "P", True),
            ("CryptoCaidBetaSelected", "B", True),
            ("CryptoCaidNagraSelected", "N", True),
            ("CryptoCaidBissSelected", "Bi", True),
            ("CryptoCaidDre3Selected", "D3", True),
            ("CryptoCaidDreSelected", "D", True),
            ("CryptoCaidBulCrypt1Selected", "B1", True),
            ("CryptoCaidBulCrypt2Selected", "B2", True),
            ("CryptoCaidVerimatrixSelected", "Vm", True),
            ("CryptoCaidTandbergSelected", "TB", True),
        )

        self.ecmdata = GetEcmInfo()
        self.feraw = None
        self.fedata = None
        self.updateFEdata = None
        self.current_source = ""
        self.current_caid = "0"
        self.current_provid = "0"
        self.current_ecmpid = "0"
        self.is_iptv = False
        self.iptv_url = ""
        self.iptv_host = ""
        self.iptv_stream_type = ""
        self.iptv_full_ref = ""

        # v2: cached /proc/stb/vmpeg reads; invalidated on program change
        self._vmpeg_cache = None

        # a53015a: last ecm.info data that belonged to a given service ref,
        # keyed by service reference, FIFO-capped. Replaces the single-slot
        # 4bd6d69 tuple so that 3 simultaneous services (2 tuners + CI)
        # don't thrash the cache.
        self._own_ecm = {}
        self._OWN_ECM_MAX = 8

        # Cached colors (avoid dict lookup every poll)
        try:
            self.cryptocolors = parameters.get("PliExtraInfoCryptoColors",
                (0x004C7D3F, 0x009F9F9F, 0x00EEEE00, 0x00FFFFFF))
        except Exception:
            self.cryptocolors = (0x004C7D3F, 0x009F9F9F, 0x00EEEE00, 0x00FFFFFF)

        try:
            self.bar_colors = parameters.get("PliExtraInfoColors",
                (0x0000FF00, 0x00FF0000, 0x00FFFFFF, 0x007F7F7F))
        except Exception:
            self.bar_colors = (0x0000FF00, 0x00FF0000, 0x00FFFFFF, 0x007F7F7F)

    def _safe_int(self, value, default=0):
        return _safe_int(value, default)

    def _safe_str(self, value, default=""):
        return _safe_str(value, default)

    # ------------------------------------------------------------------
    # Crypto: OpenViX 4bd6d69 + 2a9c832 + a53015a ports
    # ------------------------------------------------------------------

    def _service_ecm_pairs(self, info):
        """The (CAID, ECM PID) pairs of the service (what the PMT says),
        empty if not known. Port of OpenViX a53015a serviceEcmPairs()."""
        try:
            return {(pair[0], pair[1])
                    for pair in info.getInfoObject(iServiceInformation.sCAIDPIDs)}
        except Exception:
            return set()

    def _is_service_fta(self, info):
        """True if this service is free-to-air.

        Port of OpenViX 2a9c832 ecmFilePresentFor() logic, adapted because
        sIsScrambled is not available in this tree's iServiceInformation
        enum. We use sIsCrypted only, which fixes the reported bug:
        an FTA service on the playing slot no longer displays the
        recording service's encryption status.
        """
        if info is None:
            return False
        return info.getInfo(iServiceInformation.sIsCrypted) != 1

    def _ecm_number(self, text):
        """A hex number from ecm.info, None if the softcam did not give it.

        '0' is what GetEcmInfo makes of a missing line; a given 0x0000 is
        a real number and not a real CAID/ECM PID. Port of a53015a
        ecmNumber()."""
        if text in ("", "0"):
            return None
        try:
            return int(text, 16)
        except (TypeError, ValueError):
            return None

    def _ecm_data_for(self, info):
        """The data of /tmp/ecm.info for the current service.

        Port of OpenViX a53015a ecmDataFor() (supersedes the 4bd6d69 port).
        With two services decoding (a recording and the one playing) the
        softcam writes the file for both in turn, so what is in it is only
        the current service's if its CAID and ECM PID are a pair of the
        service. Only what the file gives is compared. Otherwise the last
        data that was the current service's is used, and without any
        nothing is known. If the file gives neither, or the pairs of the
        service are not known, the file is taken as it is.
        """
        data = self.ecmdata.getEcmData()
        if not info or not pathExists("/tmp/ecm.info"):
            return data
        pairs = self._service_ecm_pairs(info)
        caid = self._ecm_number(self._safe_str(data[1], "0"))
        pid = self._ecm_number(self._safe_str(data[3], "0"))
        if not pairs or (caid is None and pid is None):
            return data
        ref = self._safe_str(info.getInfoString(iServiceInformation.sServiceref), "")
        if any((caid is None or pair[0] == caid) and
               (pid is None or pair[1] == pid) for pair in pairs):
            self._own_ecm.pop(ref, None)
            self._own_ecm[ref] = data
            if len(self._own_ecm) > self._OWN_ECM_MAX:
                del self._own_ecm[next(iter(self._own_ecm))]
            return data
        return self._own_ecm.get(ref, self.NO_ECM_DATA)

    # ------------------------------------------------------------------
    # IPTV detection & parsing
    # ------------------------------------------------------------------

    def _is_iptv_service(self, refstr):
        """Check if service is IPTV"""
        if not refstr:
            return False
        refstr = refstr.lower()
        for pattern in ('%3a//',) + IPTV_PROTOCOLS + ('.m3u8', '.ts', 'stream', 'live', 'iptv'):
            if pattern in refstr:
                return True
        return False

    def _clean_iptv_url(self, url):
        """Clean IPTV URL by removing channel name from the end"""
        if not url:
            return url

        match = _RE_IPTV_TRIM_CHANNEL.search(url)
        if match:
            after_colon = url.split(':')[-1]
            if not after_colon.isdigit() and '/' not in after_colon and '?' not in after_colon:
                return match.group(1)

        match = _RE_IPTV_TRIM_CHANNEL2.search(url)
        if match:
            after = match.group(2)
            if after.startswith(':') and len(after) > 1:
                channel_name = after[1:]
                if re.search(r'[a-zA-Z]', channel_name) and not channel_name.isdigit():
                    return match.group(1)

        return url

    def _parse_iptv_url(self, refstr):
        """Parse IPTV URL from service reference"""
        if not refstr:
            return "", "", ""

        self.iptv_full_ref = refstr

        clean_ref = refstr.replace("%3a", ":").replace("%3A", ":")
        clean_ref = clean_ref.replace("%2f", "/").replace("%2F", "/")
        clean_ref = clean_ref.replace("%3f", "?").replace("%3F", "?")
        clean_ref = clean_ref.replace("%3d", "=").replace("%3D", "=")
        clean_ref = clean_ref.replace("%26", "&")

        url = ""
        host = ""
        stream_type = ""

        for rx in _RE_URL_PATTERNS:
            match = rx.search(clean_ref)
            if match:
                url = match.group(1)
                break

        if not url:
            for protocol in IPTV_PROTOCOLS:
                if protocol in clean_ref:
                    start = clean_ref.find(protocol)
                    end = clean_ref.find(' ', start)
                    if end == -1:
                        end = len(clean_ref)
                    url = clean_ref[start:end]
                    break

        if not url:
            parts = clean_ref.split(':')
            for i, part in enumerate(parts):
                if part in ('http', 'https', 'rtsp', 'rtmp', 'udp', 'rtp', 'mms'):
                    url = ':'.join(parts[i:])
                    break

        if url:
            url = self._clean_iptv_url(url)

        if url:
            try:
                parsed = urlparse(url)
                host = parsed.netloc or parsed.path.split('/')[0]
                if '@' in host:
                    host = host.split('@')[-1]
                if ':' in host:
                    host = host.split(':')[0]

                low = url.lower()
                if low.startswith(('http://', 'https://')):
                    for hint, name in _RE_STREAM_HINTS:
                        if hint in low:
                            stream_type = name
                            break
                    else:
                        stream_type = "HTTP"
                elif low.startswith('rtsp://'):
                    stream_type = "RTSP"
                elif low.startswith('rtmp://'):
                    stream_type = "RTMP"
                elif low.startswith('udp://'):
                    stream_type = "UDP"
                elif low.startswith('rtp://'):
                    stream_type = "RTP"
                elif low.startswith('mms://'):
                    stream_type = "MMS"
            except Exception:
                pass

        return url, host, stream_type

    # ------------------------------------------------------------------
    # IPTV extended helpers
    # ------------------------------------------------------------------

    def _parse_iptv_protocol(self, url):
        if not url:
            return ""
        try:
            return urlparse(url).scheme.lower()
        except Exception:
            return ""

    def _parse_iptv_port(self, url):
        if not url:
            return ""
        try:
            p = urlparse(url).port
            return str(p) if p else ""
        except Exception:
            return ""

    def _parse_iptv_path(self, url):
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            path = parsed.path or ""
            if parsed.query:
                path += "?" + parsed.query
            return path
        except Exception:
            return ""

    def _detect_container(self, url, stream_type):
        """Best-effort container name from URL extension or stream type."""
        if stream_type in ("HLS", "DASH"):
            return stream_type
        if url:
            low = url.lower()
            for ext, name in _RE_CONTAINER_HINTS:
                if ext in low:
                    return name
            for hint, name in _RE_STREAM_HINTS:
                if hint in low:
                    return name
        return stream_type or ""

    def _audio_codec_name(self, info):
        """Audio codec name. sAudioType is absent in this tree's enum,
        so this returns '' on BlackSail (safe)."""
        try:
            if not hasattr(iServiceInformation, "sAudioType"):
                return ""
            atype = info.getInfo(iServiceInformation.sAudioType)
            if atype is None or atype < 0:
                return ""
            return _AUDIO_CODEC_NAMES.get(atype, "")
        except Exception:
            return ""

    def _audio_language(self, info):
        """Selected audio track's language via iAudioTrackSelection."""
        try:
            service = self.source.service
            if service is None:
                return ""
            at = service.audioTracks()
            if at is None:
                return ""
            idx = at.getCurrentTrack()
            if idx is None or idx < 0:
                return ""
            tinfo = at.getTrackInfo(idx)
            if tinfo is None:
                return ""
            return tinfo.getLanguage() or ""
        except Exception:
            return ""

    def _bitrate_string(self, info):
        """Bitrate in Mb/s via sTransferBPS (works on IPTV too, when supported)."""
        try:
            bps = info.getInfo(iServiceInformation.sTransferBPS)
            if bps is None or bps <= 0:
                return ""
            return "%.1f Mb/s" % (bps / 1000000.0)
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Crypto data refresh
    # ------------------------------------------------------------------

    def getCryptoInfo(self, info):
        """Get crypto information (uses _ecm_data_for -> 4bd6d69+a53015a)."""
        try:
            refstr = info.getInfoString(iServiceInformation.sServiceref)
            if refstr:
                refstr = self._safe_str(refstr, "")
                if self._is_iptv_service(refstr):
                    self.is_iptv = True
                    self.iptv_url, self.iptv_host, self.iptv_stream_type = self._parse_iptv_url(refstr)
                else:
                    self.is_iptv = False
                    self.iptv_url = ""
                    self.iptv_host = ""
                    self.iptv_stream_type = ""
        except Exception:
            self.is_iptv = False

        if info.getInfo(iServiceInformation.sIsCrypted) == 1:
            data = self._ecm_data_for(info)
            if data and len(data) >= 4:
                self.current_source = self._safe_str(data[0], "")
                self.current_caid = self._safe_str(data[1], "0")
                self.current_provid = self._safe_str(data[2], "0")
                self.current_ecmpid = self._safe_str(data[3], "0")
            else:
                self.current_source = ""
                self.current_caid = "0"
                self.current_provid = "0"
                self.current_ecmpid = "0"
        else:
            self.current_source = ""
            self.current_caid = "0"
            self.current_provid = "0"
            self.current_ecmpid = "0"

    # ============ CRYPTO METHODS ============

    def createCryptoBar(self, info):
        """Create colored crypto status bar"""
        if self.is_iptv:
            return r"\c00FF6600IPTV"

        res = ""
        available_caids = []
        try:
            available_caids = info.getInfoObject(iServiceInformation.sCAIDs) or []
        except Exception:
            available_caids = []

        colors = self.bar_colors
        current_caid_int = self._safe_int(self.current_caid, 0)

        for caid_entry in caid_data:
            start_caid = self._safe_int(caid_entry[0], 0)
            end_caid = self._safe_int(caid_entry[1], 0)

            if start_caid <= current_caid_int <= end_caid:
                color = r"\c%08x" % colors[0]
            else:
                color = r"\c%08x" % colors[2]
                try:
                    if available_caids:
                        for caid in available_caids:
                            caid_int = self._safe_int(caid, 0)
                            if start_caid <= caid_int <= end_caid:
                                color = r"\c%08x" % colors[1]
                                break
                except Exception:
                    pass

            if color != r"\c%08x" % colors[2] or caid_entry[5]:
                if res:
                    res += " "
                res += color + caid_entry[3]

        res += r"\c%08x" % colors[3]
        return res

    def createCurrentCaidLabel(self, info):
        """Current CAID label with CI support.

        Uses _is_service_fta (2a9c832) instead of the bare ecm.info existence
        check: an ecm.info left over by a recording service no longer makes
        an FTA service look encrypted.
        """
        if self.is_iptv:
            return "IPTV"

        res = ""
        decodingCiSlot = -1

        NUM_CI = SystemInfo.get("CommonInterface", 0)
        if NUM_CI and NUM_CI > 0 and dvbCIUI:
            for slot in range(NUM_CI):
                try:
                    stateDecoding = dvbCIUI.getDecodingState(slot)
                    stateSlot = dvbCIUI.getState(slot)
                    if stateDecoding == 2 and stateSlot not in (-1, 0, 3):
                        decodingCiSlot = slot
                except Exception:
                    pass

        # 2a9c832: /tmp/ecm.info only counts as present for THIS service
        # if the service is actually encrypted.
        ecm_present = not self._is_service_fta(info) and pathExists("/tmp/ecm.info")

        if not ecm_present and decodingCiSlot == -1:
            return "FTA"

        if decodingCiSlot > -1 and not ecm_present:
            return "CI%d" % (decodingCiSlot)

        current_caid_int = self._safe_int(self.current_caid, 0)
        for caid_entry in caid_data:
            start_caid = self._safe_int(caid_entry[0], 0)
            end_caid = self._safe_int(caid_entry[1], 0)
            if start_caid <= current_caid_int <= end_caid:
                res = caid_entry[4]
                break

        if decodingCiSlot > -1:
            return "CI%d + %s" % (decodingCiSlot, res)
        return res

    def createCryptoSpecial(self, info):
        """Create crypto special info with CAID/Provider/SID"""
        if self.is_iptv:
            return self.iptv_url if self.iptv_url else self.iptv_host or "IPTV"

        try:
            refstr = info.getInfoString(iServiceInformation.sServiceref)
            if refstr:
                refstr = self._safe_str(refstr, "")
        except Exception:
            refstr = ""

        if refstr and self._is_iptv_service(refstr):
            url, host, _ = self._parse_iptv_url(refstr)
            return url if url else host or "IPTV"

        caid_name = "Free to Air"
        current_caid_int = self._safe_int(self.current_caid, 0)
        if current_caid_int == 0:
            current_provid_int = self._safe_int(self.current_provid, 0)
            try:
                sid = info.getInfo(iServiceInformation.sSID)
                if sid is None or sid < 0:
                    sid = 0
            except Exception:
                sid = 0
            return "FTA:%06X:%04X" % (current_provid_int, sid)

        try:
            for caid_entry in caid_data:
                start_caid = self._safe_int(caid_entry[0], 0)
                end_caid = self._safe_int(caid_entry[1], 0)
                if start_caid <= current_caid_int <= end_caid:
                    caid_name = caid_entry[2]
                    break

            current_provid_int = self._safe_int(self.current_provid, 0)
            try:
                sid = info.getInfo(iServiceInformation.sSID)
                if sid is None or sid < 0:
                    sid = 0
            except Exception:
                sid = 0

            return "%s:%04X:%06X:%04X" % (caid_name, current_caid_int, current_provid_int, sid)
        except Exception:
            pass
        return ""

    def createCryptoNameCaid(self, info):
        """Create crypto name with CAID"""
        if self.is_iptv:
            return "IPTV"

        caid_name = "FTA"
        current_caid_int = self._safe_int(self.current_caid, 0)
        if current_caid_int == 0:
            return caid_name
        try:
            for caid_entry in caid_data:
                start_caid = self._safe_int(caid_entry[0], 0)
                end_caid = self._safe_int(caid_entry[1], 0)
                if start_caid <= current_caid_int <= end_caid:
                    caid_name = caid_entry[2]
                    break
            return "%s:%04X" % (caid_name, current_caid_int)
        except Exception:
            pass
        return ""

    # ============ IPTV SPECIFIC METHODS ============

    def createIPTVInfo(self, info):
        """Richer IPTV info: [CONTAINER] host url"""
        if not self.is_iptv:
            return ""
        container = self._detect_container(self.iptv_url, self.iptv_stream_type)
        bits = []
        if container:
            bits.append("[%s]" % container)
        if self.iptv_host:
            bits.append(self.iptv_host)
        if self.iptv_url and self.iptv_url != self.iptv_host:
            bits.append(self.iptv_url)
        return " ".join(bits)

    def createIPTVUrl(self, info):
        if self.is_iptv and self.iptv_url:
            return self.iptv_url
        return ""

    def createIPTVStreamType(self, info):
        if self.is_iptv and self.iptv_stream_type:
            return self.iptv_stream_type
        return ""

    def createIPTVHost(self, info):
        if self.is_iptv and self.iptv_host:
            return self.iptv_host
        return ""

    def createIPTVProtocol(self, info):
        return self._parse_iptv_protocol(self.iptv_url) if self.is_iptv else ""

    def createIPTVPort(self, info):
        return self._parse_iptv_port(self.iptv_url) if self.is_iptv else ""

    def createIPTVPath(self, info):
        return self._parse_iptv_path(self.iptv_url) if self.is_iptv else ""

    def createIPTVContainer(self, info):
        if not self.is_iptv:
            return ""
        return self._detect_container(self.iptv_url, self.iptv_stream_type)

    def createIPTVAudioCodec(self, info):
        return self._audio_codec_name(info) if self.is_iptv else ""

    def createIPTVAudioLang(self, info):
        return self._audio_language(info) if self.is_iptv else ""

    def createIPTVBitrate(self, info):
        return self._bitrate_string(info) if self.is_iptv else ""

    def createIPTVSummary(self, info):
        if not self.is_iptv:
            return ""
        parts = (
            self.createIPTVContainer(info),
            self.createResolution(info),
            self.createVideoCodec(info),
            self.createIPTVAudioCodec(info),
            self.createIPTVAudioLang(info),
            self.createIPTVBitrate(info),
        )
        return " ".join(p for p in parts if p)

    # ============ VIDEO METHODS ============

    def _read_vmpeg_info(self):
        if self._vmpeg_cache is not None:
            return self._vmpeg_cache

        xres = _read_proc_int("/proc/stb/vmpeg/0/xres", 16)
        yres = _read_proc_int("/proc/stb/vmpeg/0/yres", 16)

        if not xres or not yres or xres > 4096 or yres > 4096 or (xres <= 128 and yres <= 128):
            self._vmpeg_cache = ("", "", "")
            return self._vmpeg_cache

        mode = ""
        prog = _read_proc_int("/proc/stb/vmpeg/0/progressive", 16)
        if prog is not None:
            mode = "p" if prog else "i"

        fps = ""
        try:
            with open("/proc/stb/vmpeg/0/framerate", "r") as f:
                raw = f.read().strip()
                if raw:
                    fps = str((int(raw) + 500) // 1000)
        except Exception:
            pass

        self._vmpeg_cache = (xres, yres, mode, fps)
        return self._vmpeg_cache

    def createResolution(self, info):
        xres = info.getInfo(iServiceInformation.sVideoWidth)
        yres = info.getInfo(iServiceInformation.sVideoHeight)
        prog = info.getInfo(iServiceInformation.sProgressive)

        if xres > 0 and yres > 0:
            mode = ("i", "p", " ")[prog]
            fps = (info.getInfo(iServiceInformation.sFrameRate) + 500) // 1000
            if not fps or fps == -1:
                try:
                    fps = (int(open("/proc/stb/vmpeg/0/framerate", "r").read()) + 500) // 1000
                except Exception:
                    pass
            return "%sx%s%s%s" % (xres, yres, mode, fps)

        cached = self._read_vmpeg_info()
        if cached and cached[0] != "":
            xres, yres, mode, fps = cached
            if fps:
                return "%sx%s%s@%s" % (xres, yres, mode, fps)
            return "%sx%s%s" % (xres, yres, mode)

        return ""

    def createGamma(self, info):
        try:
            gamma = info.getInfo(iServiceInformation.sGamma)
            return gamma_data.get(gamma, "")
        except Exception:
            return ""

    def createVideoCodec(self, info):
        try:
            video_type = info.getInfo(iServiceInformation.sVideoType)
            return codec_data.get(video_type, "N/A")
        except Exception:
            return "N/A"

    def createResolutionString(self, info):
        resolution = self.createResolution(info)
        gamma = self.createGamma(info)
        if resolution and gamma:
            return resolution + " " + gamma
        return resolution or gamma or ""

    # ============ PID METHODS ============

    def createPIDInfo(self, info):
        try:
            vpid = info.getInfo(iServiceInformation.sVideoPID)
            apid = info.getInfo(iServiceInformation.sAudioPID)
            pcrpid = info.getInfo(iServiceInformation.sPCRPID)
            sidpid = info.getInfo(iServiceInformation.sSID)
            tsid = info.getInfo(iServiceInformation.sTSID)
            onid = info.getInfo(iServiceInformation.sONID)
        except Exception:
            return ""

        vpid = max(0, vpid if vpid is not None else -1)
        apid = max(0, apid if apid is not None else -1)
        pcrpid = max(0, pcrpid if pcrpid is not None else -1)
        sidpid = max(0, sidpid if sidpid is not None else -1)
        tsid = max(0, tsid if tsid is not None else -1)
        onid = max(0, onid if onid is not None else -1)

        return "%d-%d:%05d:%04d:%04d:%04d" % (onid, tsid, sidpid, vpid, apid, pcrpid)

    # ============ SERVICE METHODS ============

    def createProviderName(self, info):
        try:
            provider = info.getInfoString(iServiceInformation.sProvider)
            if provider:
                provider = self._safe_str(provider, "")
                if not provider and self.is_iptv:
                    return self.iptv_host or ""
                return provider
        except Exception:
            pass
        return ""

    def createServiceRef(self, info):
        try:
            ref = info.getInfoString(iServiceInformation.sServiceref)
            return self._safe_str(ref, "") if ref else ""
        except Exception:
            return ""

    # ============ TRANSPONDER METHODS ============

    def createTransponderInfo(self, fedata, feraw, info):
        if self.is_iptv:
            return self.iptv_url if self.iptv_url else self.iptv_host or ""

        if not feraw:
            refstr = info.getInfoString(iServiceInformation.sServiceref)
            if refstr and "%3a//" in refstr.lower():
                return refstr.split(":")[10].replace("%3a", ":").replace("%3A", ":")
            return ""

        tuner_type = self._safe_str(feraw.get("tuner_type", ""))
        if "DVB-T" in tuner_type:
            tmp = (addspace(self.createChannelNumber(fedata, feraw)) +
                   addspace(self.createFrequency(fedata)) +
                   addspace(self.createPolarization(fedata)))
        else:
            tmp = addspace(self.createFrequency(fedata)) + addspace(self.createPolarization(fedata))

        return (addspace(self.createTunerSystem(fedata)) + tmp +
                addspace(self.createSymbolRate(fedata, feraw)) +
                addspace(self.createFEC(fedata, feraw)) +
                addspace(self.createModulation(fedata)) +
                addspace(self.createOrbPos(feraw)) +
                addspace(self.createMisPls(fedata)))

    def createFrequency(self, fedata):
        try:
            frequency = fedata.get("frequency")
            if frequency:
                if frequency > 1000000:
                    return "%d %s" % (int(frequency // 1000000.0 + 0.5), _("MHz"))
                return str(frequency)
        except Exception:
            pass
        return ""

    def createChannelNumber(self, fedata, feraw):
        try:
            tuner_type = self._safe_str(feraw.get("tuner_type", ""))
            if "DVB-T" in tuner_type:
                channel = fedata.get("channel")
                return self._safe_str(channel, "") if channel else ""
        except Exception:
            pass
        return ""

    def createSymbolRate(self, fedata, feraw):
        try:
            tuner_type = self._safe_str(feraw.get("tuner_type", ""))
            if "DVB-T" in tuner_type:
                bandwidth = fedata.get("bandwidth")
                return self._safe_str(bandwidth, "") if bandwidth else ""
            else:
                symbolrate = fedata.get("symbol_rate")
                if symbolrate:
                    return str(symbolrate // 1000)
        except Exception:
            pass
        return ""

    def createPolarization(self, fedata):
        try:
            pol = fedata.get("polarization_abbreviation")
            return self._safe_str(pol, "") if pol else ""
        except Exception:
            return ""

    def createFEC(self, fedata, feraw):
        try:
            tuner_type = self._safe_str(feraw.get("tuner_type", ""))
            if "DVB-T" in tuner_type:
                code_rate_lp = fedata.get("code_rate_lp")
                code_rate_hp = fedata.get("code_rate_hp")
                guard_interval = fedata.get("guard_interval")
                if code_rate_lp and code_rate_hp and guard_interval:
                    return (self._safe_str(code_rate_lp) + "-" +
                            self._safe_str(code_rate_hp) + "-" +
                            self._safe_str(guard_interval))
            else:
                fec = fedata.get("fec_inner")
                if fec:
                    return self._safe_str(fec, "")
        except Exception:
            pass
        return ""

    def createModulation(self, fedata):
        try:
            tuner_type = self._safe_str(fedata.get("tuner_type", ""))
            if tuner_type == _("Terrestrial") or tuner_type == "Terrestrial":
                constellation = fedata.get("constellation")
                if constellation:
                    return self._safe_str(constellation, "")
            else:
                modulation = fedata.get("modulation")
                if modulation:
                    return self._safe_str(modulation, "")
        except Exception:
            pass
        return ""

    def createTunerType(self, feraw):
        try:
            tuner_type = feraw.get("tuner_type")
            return self._safe_str(tuner_type, "") if tuner_type else ""
        except Exception:
            return ""

    def createTunerSystem(self, fedata):
        try:
            system = fedata.get("system")
            return self._safe_str(system, "") if system else ""
        except Exception:
            return ""

    def createOrbPos(self, feraw):
        try:
            orbpos = feraw.get("orbital_position")
            if orbpos:
                if orbpos > 1800:
                    return _("%.1f° W") % ((3600 - orbpos) / 10.0)
                elif orbpos > 0:
                    return _("%.1f° E") % (orbpos / 10.0)
        except Exception:
            pass
        return ""

    def createOrbPosOrTunerSystem(self, fedata, feraw):
        orbpos = self.createOrbPos(feraw)
        if orbpos != "":
            return orbpos
        return self.createTunerSystem(fedata)

    def createTransponderName(self, feraw):
        try:
            orbpos = feraw.get("orbital_position")
            if orbpos is None:
                return ""
            if orbpos > 1800:
                return _("%.1f° W") % ((3600 - orbpos) / 10.0)
            elif orbpos > 0:
                return _("%.1f° E") % (orbpos / 10.0)
        except Exception:
            pass
        return ""

    def createMisPls(self, fedata):
        if not fedata:
            return ""
        tmp = ""

        is_id = fedata.get("is_id")
        if is_id is not None and is_id > -1:
            tmp = "MIS %d" % is_id

        pls_mode = fedata.get("pls_mode")
        pls_code = fedata.get("pls_code")
        if pls_code is not None and pls_code > 0:
            tmp = addspace(tmp) + "%s %d" % (self._safe_str(pls_mode, ""), pls_code)

        t2mi_plp_id = fedata.get("t2mi_plp_id")
        t2mi_pid = fedata.get("t2mi_pid")
        if t2mi_plp_id is not None and t2mi_plp_id > -1:
            tmp = addspace(tmp) + "T2MI %d PID %d" % (t2mi_plp_id, t2mi_pid)

        return tmp

    # ============ MAIN METHODS ============

    @cached
    def getText(self):
        service = self.source.service
        if service is None:
            return ""
        info = service and service.info()

        if not info:
            return ""

        try:
            try:
                show_crypto = int(config.usage.show_cryptoinfo.value) > 0
            except Exception:
                show_crypto = False

            self.getCryptoInfo(info)

            # === IPTV TYPES ===
            if self.type == "IPTVInfo":
                return self.createIPTVInfo(info)
            if self.type == "IPTVUrl":
                return self.createIPTVUrl(info)
            if self.type == "IPTVStreamType":
                return self.createIPTVStreamType(info)
            if self.type == "IPTVHost":
                return self.createIPTVHost(info)
            if self.type == "IPTVProtocol":
                return self.createIPTVProtocol(info)
            if self.type == "IPTVPort":
                return self.createIPTVPort(info)
            if self.type == "IPTVPath":
                return self.createIPTVPath(info)
            if self.type == "IPTVContainer":
                return self.createIPTVContainer(info)
            if self.type == "IPTVAudioCodec":
                return self.createIPTVAudioCodec(info)
            if self.type == "IPTVAudioLang":
                return self.createIPTVAudioLang(info)
            if self.type == "IPTVBitrate":
                return self.createIPTVBitrate(info)
            if self.type == "IPTVSummary":
                return self.createIPTVSummary(info)

            # === CRYPTO TYPES ===
            if self.type == "CryptoInfo":
                if show_crypto:
                    return addspace(self.createCryptoBar(info)) + self.createCryptoSpecial(info)
                else:
                    return (addspace(self.createCryptoBar(info)) +
                            addspace(self.current_source) +
                            self.createCryptoSpecial(info))

            if self.type == "CurrentCrypto":
                return self.createCurrentCaidLabel(info)

            if self.type == "CryptoBar":
                return self.createCryptoBar(info)

            if self.type == "CryptoSpecial":
                return self.createCryptoSpecial(info)

            if self.type == "CryptoNameCaid":
                return self.createCryptoNameCaid(info)

            # === VIDEO TYPES ===
            if self.type == "Resolution":
                return self.createResolution(info)

            if self.type == "ResolutionString":
                return addspace(self.createResolution(info)) + self.createGamma(info)

            if self.type == "VideoCodec":
                return self.createVideoCodec(info)

            if self.type == "Gamma":
                return self.createGamma(info)

            # Update frontend data
            if self.updateFEdata:
                self.updateFEdata = False
                feinfo = service.frontendInfo()
                if feinfo:
                    try:
                        source_value = config.usage.infobar_frontend_source.value
                        if isinstance(source_value, bytes):
                            source_value = source_value.decode('utf-8', errors='ignore')
                        self.feraw = feinfo.getAll(source_value == "settings")
                        if self.feraw:
                            self.fedata = ConvertToHumanReadable(self.feraw)
                    except Exception:
                        pass

            feraw = self.feraw
            if not feraw:
                try:
                    feraw = info.getInfoObject(iServiceInformation.sTransponderData)
                    if feraw:
                        self.fedata = ConvertToHumanReadable(feraw)
                    else:
                        self.fedata = None
                except Exception:
                    self.fedata = None
            else:
                if self.fedata is None:
                    try:
                        self.fedata = ConvertToHumanReadable(feraw)
                    except Exception:
                        self.fedata = {}

            fedata = self.fedata

            # === ALL ===
            if self.type == "All":
                if self.is_iptv:
                    provider = self.createProviderName(info)
                    summary = self.createIPTVSummary(info)
                    url = self.iptv_url if self.iptv_url else self.iptv_host
                    line1 = (addspace(provider) + summary).rstrip()
                    return line1 + "\n" + url

                elif show_crypto:
                    return (addspace(self.createProviderName(info)) +
                            self.createTransponderInfo(fedata, feraw, info) + "\n" +
                            addspace(self.createCryptoBar(info)) +
                            addspace(self.createCryptoSpecial(info)) + "\n" +
                            addspace(self.createPIDInfo(info)) +
                            addspace(self.createVideoCodec(info)) +
                            addspace(self.createResolution(info)) +
                            self.createGamma(info))
                else:
                    return (addspace(self.createProviderName(info)) +
                            self.createTransponderInfo(fedata, feraw, info) + "\n" +
                            addspace(self.createCryptoBar(info)) +
                            self.current_source + "\n" +
                            addspace(self.createCryptoSpecial(info)) +
                            addspace(self.createVideoCodec(info)) +
                            addspace(self.createResolution(info)) +
                            self.createGamma(info))

            # === PID ===
            if self.type == "PIDInfo":
                return self.createPIDInfo(info)

            # === SERVICE INFO ===
            if self.type == "ServiceInfo":
                if self.is_iptv:
                    provider = self.createProviderName(info)
                    summary = self.createIPTVSummary(info)
                    url = self.iptv_url if self.iptv_url else self.iptv_host
                    return (addspace(provider) + summary + " " + url).rstrip()

                return (addspace(self.createProviderName(info)) +
                        addspace(self.createTunerSystem(fedata)) +
                        addspace(self.createFrequency(fedata)) +
                        addspace(self.createPolarization(fedata)) +
                        addspace(self.createSymbolRate(fedata, feraw)) +
                        addspace(self.createFEC(fedata, feraw)) +
                        addspace(self.createModulation(fedata)) +
                        addspace(self.createOrbPos(feraw)) +
                        addspace(self.createTransponderName(feraw)) +
                        addspace(self.createVideoCodec(info)) +
                        addspace(self.createResolution(info)) +
                        self.createGamma(info))

            # === SERVICE REF ===
            if self.type == "ServiceRef":
                return self.createServiceRef(info)

            # === PROVIDER ===
            if self.type == "ProviderName":
                return self.createProviderName(info)

            if not feraw:
                if self.is_iptv:
                    return self.iptv_url if self.iptv_url else self.iptv_host
                return ""

            # === TRANSPONDER TYPES ===
            if self.type == "TransponderInfo":
                return self.createTransponderInfo(fedata, feraw, info)

            if self.type == "TransponderFrequency":
                return self.createFrequency(fedata)

            if self.type == "TransponderSymbolRate":
                return self.createSymbolRate(fedata, feraw)

            if self.type == "TransponderPolarization":
                return self.createPolarization(fedata)

            if self.type == "TransponderFEC":
                return self.createFEC(fedata, feraw)

            if self.type == "TransponderModulation":
                return self.createModulation(fedata)

            if self.type == "OrbitalPosition":
                return self.createOrbPos(feraw)

            if self.type == "TunerType":
                return self.createTunerType(feraw)

            if self.type == "TunerSystem":
                return self.createTunerSystem(fedata)

            if self.type == "OrbitalPositionOrTunerSystem":
                return self.createOrbPosOrTunerSystem(fedata, feraw)

            if self.type == "TerrestrialChannelNumber":
                return self.createChannelNumber(fedata, feraw)

            if self.type == "TransponderInfoMisPls":
                return self.createMisPls(fedata)

            if self.type == "TransponderName":
                return self.createTransponderName(feraw)

            return _("invalid type")

        except Exception:
            return "FTA"

    text = property(getText)

    @cached
    def getBool(self):
        """Boolean value for crypto indicators and IPTVIsIPTV.

        Crypto path uses _ecm_data_for (4bd6d69 + a53015a) so that the
        recording service's ecm.info is not mistaken for the playing
        service's.
        """
        try:
            service = self.source.service
            info = service and service.info()

            if not info:
                return False

            # === IPTVIsIPTV ===
            if self.type == "IPTVIsIPTV":
                ref = self._safe_str(
                    info.getInfoString(iServiceInformation.sServiceref), "")
                return self._is_iptv_service(ref)

            request_caid = None
            request_selected = None
            for x in self.ca_table:
                if x[0] == self.type:
                    request_caid = x[1]
                    request_selected = x[2]
                    break

            if request_caid is None:
                return False

            if info.getInfo(iServiceInformation.sIsCrypted) != 1:
                return False

            # a53015a: use _ecm_data_for so cross-service ecm.info doesn't leak
            data = self._ecm_data_for(info)
            if data is None or len(data) < 2:
                return False

            current_caid = self._safe_str(data[1], "0")
            current_caid_int = self._safe_int(current_caid, 0)

            try:
                available_caids = info.getInfoObject(iServiceInformation.sCAIDs) or []
            except Exception:
                available_caids = []

            for caid_entry in caid_data:
                if caid_entry[3] == request_caid:
                    if request_selected:
                        start_caid = self._safe_int(caid_entry[0], 0)
                        end_caid = self._safe_int(caid_entry[1], 0)
                        if start_caid <= current_caid_int <= end_caid:
                            return True
                    else:
                        try:
                            if available_caids:
                                for caid in available_caids:
                                    caid_int = self._safe_int(caid, 0)
                                    start_caid = self._safe_int(caid_entry[0], 0)
                                    end_caid = self._safe_int(caid_entry[1], 0)
                                    if start_caid <= caid_int <= end_caid:
                                        return True
                        except Exception:
                            pass

            return False
        except Exception:
            return False

    boolean = property(getBool)

    def changed(self, what):
        try:
            if what[0] == self.CHANGED_SPECIFIC:
                self.updateFEdata = False
                if what[1] == iPlayableService.evNewProgramInfo:
                    self.updateFEdata = True
                    self._vmpeg_cache = None
                if what[1] == iPlayableService.evEnd:
                    self.feraw = None
                    self.fedata = None
                    self._vmpeg_cache = None
                Converter.changed(self, what)
            elif what[0] == self.CHANGED_POLL and self.updateFEdata is not None:
                self.updateFEdata = False
                Converter.changed(self, what)
        except Exception:
            pass