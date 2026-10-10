import enum
import time
import asyncio
import random
import yt_dlp
import discord
from typing import Optional, List, Union

class TrackSource(enum.Enum):
    YouTube = "ytsearch"
    SoundCloud = "scsearch"
    Spotify = "spotify"

class AutoPlayMode(enum.Enum):
    disabled = 0
    enabled = 1

class QueueMode(enum.Enum):
    normal = 0
    loop = 1

class Track:
    def __init__(self, title: str, author: str, length: int, uri: str, artwork: Optional[str] = None, source: str = "youtube", stream_url: Optional[str] = None):
        self.title = title or "Unknown Title"
        self.author = author or "Unknown Artist"
        self.length = int(length or 0)  # in milliseconds
        self.uri = uri or ""
        self.artwork = artwork
        self.source = str(source).lower()
        self._stream_url = stream_url

    async def get_stream_url(self) -> Optional[str]:
        if self._stream_url:
            return self._stream_url
        loop = asyncio.get_event_loop()
        def _extract():
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'noplaylist': True,
                'js_runtimes': {'node': {}}
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(self.uri, download=False)
                    if not info:
                        return None
                    if 'url' in info:
                        return info['url']
                    for f in info.get('formats', []):
                        if f.get('acodec') != 'none' and f.get('url'):
                            return f['url']
                    return None
                except Exception as e:
                    print(f"[discord_music extract error]: {e}")
                    return None
        self._stream_url = await loop.run_in_executor(None, _extract)
        return self._stream_url

class Playlist:
    def __init__(self, name: str, tracks: List[Track]):
        self.name = name
        self.tracks = tracks

class Playable:
    @classmethod
    async def search(cls, query: str, source: Union[str, TrackSource] = "ytsearch") -> Union[List[Track], Playlist]:
        loop = asyncio.get_event_loop()
        def _do_search():
            src_str = source.value if isinstance(source, TrackSource) else str(source or "ytsearch")
            is_url = query.startswith("http://") or query.startswith("https://")
            is_playlist_url = is_url and ("list=" in query or "playlist" in query)

            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'js_runtimes': {'node': {}}
            }
            if not is_playlist_url:
                ydl_opts['noplaylist'] = True

            q = query
            if not is_url:
                prefix = "scsearch" if "sc" in src_str.lower() else "ytsearch"
                q = f"{prefix}5:{query}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(q, download=False)
                except Exception as e:
                    print(f"[discord_music search error]: {e}")
                    return []

            if not info:
                return []

            if info.get('_type') == 'playlist' and is_playlist_url:
                pl_title = info.get('title', 'Unknown Playlist')
                tracks = []
                for e in info.get('entries', []):
                    if not e: continue
                    t = cls._entry_to_track(e, source=src_str)
                    if t: tracks.append(t)
                return Playlist(name=pl_title, tracks=tracks)

            entries = info.get('entries', [info])
            tracks = []
            for e in entries:
                if not e: continue
                t = cls._entry_to_track(e, source=src_str)
                if t: tracks.append(t)
            return tracks

        return await loop.run_in_executor(None, _do_search)

    @classmethod
    def _entry_to_track(cls, e: dict, source: str = "youtube") -> Optional[Track]:
        title = e.get('title')
        if not title:
            return None
        author = e.get('uploader') or e.get('channel') or 'Unknown Artist'
        duration = int((e.get('duration') or 0) * 1000)
        uri = e.get('webpage_url') or e.get('url')
        if not uri or not uri.startswith('http'):
            vid_id = e.get('id')
            uri = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else ""
        thumb = None
        thumbs = e.get('thumbnails')
        if thumbs and isinstance(thumbs, list):
            thumb = thumbs[-1].get('url')
        elif e.get('thumbnail'):
            thumb = e.get('thumbnail')
        src_name = "soundcloud" if "sc" in source.lower() else ("spotify" if "spotify" in source.lower() else "youtube")
        return Track(title=title, author=author, length=duration, uri=uri, artwork=thumb, source=src_name)

class Queue(list):
    def __init__(self):
        super().__init__()
        self.mode = QueueMode.normal

    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    async def put_wait(self, item):
        if isinstance(item, (list, tuple)):
            self.extend(item)
        else:
            self.append(item)

    async def get_wait(self) -> Track:
        if not self:
            raise asyncio.QueueEmpty()
        return self.pop(0)

class TrackStartEventPayload:
    def __init__(self, player, track: Track):
        self.player = player
        self.track = track

class TrackEndEventPayload:
    def __init__(self, player, track: Track, reason: str = "finished"):
        self.player = player
        self.track = track
        self.reason = reason

# Filter builder compatible with wavelink.Filters
class _Timescale:
    def __init__(self):
        self.pitch = 1.0
        self.speed = 1.0
        self.rate = 1.0
    def set(self, pitch=1.0, speed=1.0, rate=1.0):
        self.pitch = pitch
        self.speed = speed
        self.rate = rate

class _Equalizer:
    def __init__(self):
        self.bands = []
    def set(self, bands=None):
        self.bands = bands or []

class _Karaoke:
    def __init__(self):
        self.enabled = False
    def set(self, **kwargs):
        self.enabled = True

class _Tremolo:
    def __init__(self):
        self.enabled = False
        self.depth = 0.5
        self.frequency = 14.0
    def set(self, depth=0.5, frequency=14.0):
        self.enabled = True
        self.depth = depth
        self.frequency = frequency

class _Vibrato:
    def __init__(self):
        self.enabled = False
        self.depth = 0.5
        self.frequency = 14.0
    def set(self, depth=0.5, frequency=14.0):
        self.enabled = True
        self.depth = depth
        self.frequency = frequency

class _Rotation:
    def __init__(self):
        self.enabled = False
        self.hz = 5.0
    def set(self, rotation_hz=5.0):
        self.enabled = True
        self.hz = rotation_hz

class _Distortion:
    def __init__(self):
        self.enabled = False
    def set(self, **kwargs):
        self.enabled = True

class _ChannelMix:
    def __init__(self):
        self.enabled = False
    def set(self, **kwargs):
        self.enabled = True

class Filters:
    def __init__(self):
        self.timescale = _Timescale()
        self.equalizer = _Equalizer()
        self.karaoke = _Karaoke()
        self.tremolo = _Tremolo()
        self.vibrato = _Vibrato()
        self.rotation = _Rotation()
        self.distortion = _Distortion()
        self.channel_mix = _ChannelMix()
        self.preset = None

    def set_preset(self, preset_name: str):
        self.preset = str(preset_name).lower()

    def to_ffmpeg_filter(self) -> str:
        if self.preset:
            p = self.preset
            if p in ("clear", "reset"):
                return ""
            elif p == "bassboost":
                return "bass=g=14:f=110:w=0.6"
            elif p == "nightcore":
                return "asetrate=48000*1.25,aresample=48000,atempo=1.0"
            elif p in ("daycore", "vaporwave"):
                return "asetrate=48000*0.80,aresample=48000,atempo=1.0"
            elif p in ("8d", "3d"):
                return "apulsator=hz=0.125"
            elif p == "karaoke":
                return "stereotools=mlev=0.03"
            elif p == "tremolo":
                return "tremolo=f=14.0:d=0.5"
            elif p == "vibrato":
                return "vibrato=f=14.0:d=0.5"
            elif p == "distortion":
                return "aecho=0.8:0.9:1000:0.3"
            elif p == "channelmix":
                return "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1"
            elif p == "lowpass":
                return "lowpass=f=1000"
            elif p == "timescale":
                return "atempo=1.25"
            elif p == "subwoofer":
                return "bass=g=20:f=60:w=0.5"
            elif p == "popvocal":
                return "equalizer=f=1000:t=q:w=1:g=5,equalizer=f=3000:t=q:w=1:g=3"
            elif p == "rock":
                return "equalizer=f=100:t=q:w=1:g=4,equalizer=f=5000:t=q:w=1:g=3"
            elif p == "lofi":
                return "lowpass=f=3200,highpass=f=300"
            elif p == "deepvoice":
                return "asetrate=48000*0.75,aresample=48000,atempo=1.33"

        filters = []
        if self.timescale.pitch != 1.0 or self.timescale.speed != 1.0:
            p = self.timescale.pitch
            s = self.timescale.speed
            filters.append(f"asetrate=48000*{p},aresample=48000,atempo={s/p}")
        if self.equalizer.bands:
            filters.append("bass=g=10:f=110:w=0.6")
        if self.tremolo.enabled:
            filters.append(f"tremolo=f={self.tremolo.frequency}:d={self.tremolo.depth}")
        if self.vibrato.enabled:
            filters.append(f"vibrato=f={self.vibrato.frequency}:d={self.vibrato.depth}")
        if self.rotation.enabled:
            filters.append("apulsator=hz=0.125")
        if self.karaoke.enabled:
            filters.append("stereotools=mlev=0.03")
        if self.distortion.enabled:
            filters.append("aecho=0.8:0.9:1000:0.3")
        return ",".join(filters) if filters else ""

class Player(discord.VoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        super().__init__(client, channel)
        self.queue = Queue()
        self.autoplay = AutoPlayMode.disabled
        self.current: Optional[Track] = None
        self.ctx = None
        self._volume = 100
        self._start_time = 0.0
        self._pause_time: Optional[float] = None
        self._seek_position_ms = 0
        self._is_seeking = False
        self._filters: Optional[Filters] = None

    @property
    def playing(self) -> bool:
        return (self.is_playing() or self.is_paused()) and self.current is not None

    @property
    def paused(self) -> bool:
        return self.is_paused()

    @property
    def connected(self) -> bool:
        return self.is_connected()

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def position(self) -> int:
        if not self.current:
            return 0
        if self.is_paused() and self._pause_time:
            elapsed = self._pause_time - self._start_time
        elif self._start_time > 0:
            elapsed = time.time() - self._start_time
        else:
            elapsed = 0.0
        return max(0, int(elapsed * 1000))

    async def set_volume(self, value: int):
        self._volume = max(0, min(1000, value))
        if self.source and isinstance(self.source, discord.PCMVolumeTransformer):
            self.source.volume = self._volume / 100.0

    async def set_filters(self, filters: Filters):
        self._filters = filters
        if self.current and (self.is_playing() or self.is_paused()):
            pos = self.position
            await self.seek(pos)

    async def play(self, track: Track):
        self.current = track
        self._seek_position_ms = 0
        await self._start_stream(track, seek_seconds=0)

    async def _start_stream(self, track: Track, seek_seconds: float = 0):
        stream_url = await track.get_stream_url()
        if not stream_url:
            print(f"[Player] Could not obtain audio stream URL for {track.title}")
            self._on_track_finished(track)
            return

        before_opts = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        if seek_seconds > 0:
            before_opts = f"-ss {seek_seconds:.2f} " + before_opts

        opts = "-vn"
        if self._filters:
            af = self._filters.to_ffmpeg_filter()
            if af:
                opts += f" -af {af}"

        try:
            raw_source = discord.FFmpegPCMAudio(
                stream_url,
                executable="ffmpeg",
                before_options=before_opts,
                options=opts
            )
            vol_source = discord.PCMVolumeTransformer(raw_source, volume=self._volume / 100.0)
        except Exception as e:
            print(f"[Player Audio Source Error]: {e}")
            self._on_track_finished(track)
            return

        if self.is_playing() or self.is_paused():
            super().stop()

        self._start_time = time.time() - seek_seconds
        self._pause_time = None

        def _after_callback(error):
            if error:
                print(f"[Player Playback Error]: {error}")
            if not self._is_seeking:
                self._on_track_finished(track)

        super().play(vol_source, after=_after_callback)

        # Dispatch start event
        payload = TrackStartEventPayload(self, track)
        self.client.dispatch("wavelink_track_start", payload)
        self.client.dispatch("track_start", payload)
        music_cog = self.client.get_cog("Music")
        if music_cog and hasattr(music_cog, "set_vc_status"):
            asyncio.run_coroutine_threadsafe(music_cog.set_vc_status(self, track), self.client.loop)

    def _on_track_finished(self, track: Track):
        if self.client and not self.client.is_closed():
            asyncio.run_coroutine_threadsafe(self._handle_track_finished(track), self.client.loop)

    async def _handle_track_finished(self, track: Track):
        payload = TrackEndEventPayload(self, track)
        self.client.dispatch("wavelink_track_end", payload)
        self.client.dispatch("track_end", payload)

        music_cog = self.client.get_cog("Music")
        if music_cog and hasattr(music_cog, "on_track_end"):
            try:
                await music_cog.on_track_end(payload)
            except Exception as e:
                print(f"[Player Cog on_track_end error]: {e}")

    async def pause(self, state: bool = True):
        if state:
            if self.is_playing() and not self.is_paused():
                self._pause_time = time.time()
                super().pause()
        else:
            if self.is_paused():
                if self._pause_time:
                    self._start_time += (time.time() - self._pause_time)
                    self._pause_time = None
                super().resume()

    def stop(self):
        self.current = None
        if self.is_playing() or self.is_paused():
            super().stop()
        music_cog = self.client.get_cog("Music")
        if music_cog and hasattr(music_cog, "clear_vc_status"):
            asyncio.run_coroutine_threadsafe(music_cog.clear_vc_status(self), self.client.loop)

    async def seek(self, position_ms: int):
        if not self.current:
            return
        self._is_seeking = True
        try:
            seek_seconds = max(0, position_ms) / 1000.0
            await self._start_stream(self.current, seek_seconds=seek_seconds)
        finally:
            self._is_seeking = False

    async def disconnect(self, *, force: bool = False):
        self.current = None
        self.queue.clear()
        try:
            await super().disconnect(force=force)
        except Exception as e:
            pass

# Stubs for seamless wavelink API compatibility
class Node:
    def __init__(self, uri=None, password=None, **kwargs):
        self.uri = uri
        self.password = password

class Pool:
    @classmethod
    async def connect(cls, nodes=None, client=None, cache_capacity=None):
        print("[Discord Music Engine] Connected natively without Lavalink.")
        return True

class _Enums:
    TrackSource = TrackSource
    AutoPlayMode = AutoPlayMode
    QueueMode = QueueMode

enums = _Enums()
