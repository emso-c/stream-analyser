from dataclasses import dataclass, field
import datetime
from typing import Optional
import webbrowser
import platform
from colorama import init, Fore, Style
from colorama.ansi import AnsiFore
from enum import IntEnum
#from .chatanalyser import DEFAULT_CONTEXT_SOURCE_PATH  # circular import
from .exceptions import PathAlreadyExistsException

init()

class ImageResolution(IntEnum):
    MEDIUM = 0
    HIGH = 1
    STANDARD = 2
    MAXIMUM = 3

class Browser:
    CHROME = "chrome"
    EDGE = "edge"
    FIREFOX = "firefox"
    OPERA = "opera"

class OSName:
    WINDOWS = "Windows"
    LINUX = "Linux"
    MAC = "Darwin"
    
class DefaultStoragePath:
    WINDOWS = "C:/Stream Analyser"
    LINUX = "/var/lib/Stream Analyser"
    MAC = "/Library/Application Support/Stream Analyser" # Not tested
    
    @staticmethod
    def get_path():
        sys = platform.system()
        if sys == OSName.WINDOWS:
            return DefaultStoragePath.WINDOWS
        elif sys == OSName.LINUX:
            return DefaultStoragePath.LINUX
        elif sys == OSName.MAC:
            return DefaultStoragePath.MAC
        elif not sys:
            raise ValueError("Could not determine OS name.")
        else:
            raise ValueError("Invalid OS name: %s" % platform.system)

@dataclass
class Icon:
    id: str  # title
    url: str
    width: int = 0
    height: int = 0

    def __repr__(self):
        if self.width and self.height:
            return f"{self.id} ({self.width}x{self.height}): {self.url}"
        return f"{self.id}: {self.url}"

@dataclass
class Emote:
    id: str
    name: str
    is_custom_emoji: bool
    images: list[Icon] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id+self.name)

    def __repr__(self):
        return f"{self.id}: {self.name} ({len(self.images)} images)"

@dataclass
class Author:
    id: str
    name: str
    is_member: bool = False
    membership_info: str = ""
    images: list[Icon] = field(default_factory=list)

    def colorless_str(self):
        if self.is_member:
            return f"{self.name}: {self.id} [{self.membership_info}]"
        return f"{self.name}: {self.id}"

    def __repr__(self):
        color = Fore.GREEN if self.is_member else Fore.YELLOW
        if self.is_member:
            return f"{color+self.name+Style.RESET_ALL}: {self.id} [{self.membership_info}]"
        return f"{color+self.name+Style.RESET_ALL}: {self.id}"

    def __hash__(self):
        return hash(self.id)

@dataclass
class SuperchatColor:
    background: str
    header: str

    def __repr__(self):
        return f"{self.header}/{self.background}"


@dataclass
class Money:
    amount: str
    currency: str
    currency_symbol: str
    text: str

    def __repr__(self):
        return f"{self.text} ({self.currency})"

@dataclass
class ChatItem:
    id: str
    time: int
    author: Author
    text: str

    @property
    def time_in_hms(self):
        return datetime.timedelta(seconds=int(self.time))
    
    def __hash__(self):
        return hash(self.id)

@dataclass
class Message(ChatItem):
    emotes: list[Emote] = field(default_factory=list)

    @property
    def colorless_str(self):
        return f"[{self.time_in_hms}] {self.author.name}: {self.text}"

    def __repr__(self):
        return f"[{self.time_in_hms}] {Fore.YELLOW+self.author.name+Style.RESET_ALL}: {self.text}"

@dataclass
class Superchat(ChatItem):
    money: Money
    colors: SuperchatColor
    emotes: list[Emote] = field(default_factory=list)

    @property
    def colorless_str(self):
        return f"[{self.time_in_hms}] {self.author.name}: {self.text} ({self.money.text})"

    def __repr__(self):
        return f"[{self.time_in_hms}] {Fore.RED+self.author.name+Style.RESET_ALL}: {self.text} ({self.money.text})"

@dataclass
class Membership(ChatItem):
    welcome_text: str
    emotes: list[Emote] = field(default_factory=list)

    @property
    def colorless_str(self):
        return f"[{self.time_in_hms}] {self.author.name} has joined membership. {str(self.welcome_text)}"

    def __repr__(self):
        return f"[{self.time_in_hms}] {Fore.GREEN+self.author.name+Style.RESET_ALL} has joined membership. {str(self.welcome_text)}"

@dataclass
class Sticker(Superchat):
    sticker_images: list[Icon] = field(default_factory=list)

    @property
    def colorless_str(self):
        return f"[{self.time_in_hms}] {self.author.name} sent a Sticker ({self.money.text})"

    def __repr__(self):
        return f"[{self.time_in_hms}] {Fore.RED+self.author.name+Style.RESET_ALL} sent a Sticker ({self.money.text})"

@dataclass
class Intensity:
    level: str
    constant: int
    color: AnsiFore

    def __repr__(self):
        return f"{self.color+self.level+Style.RESET_ALL}: {self.constant}"

    @property
    def colored_level(self):
        return self.color + self.level + Style.RESET_ALL


@dataclass
class Highlight:
    stream_id: str
    time: int
    duration: int
    intensity: Intensity = None
    fdelta: float = 0.0  # is the frequency difference from start to finish
    messages: list[Message] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    kw_emotes: list[Emote] = field(default_factory=list)
    contexts: set[str] = field(default_factory=set)

    def __repr__(self):
        return "[{0}] {1}: {2} ({3} messages, {4} intensity, {5:.3f} diff, {6}s duration)".format(
            self.time_in_hms,
            Fore.LIGHTRED_EX + "/".join(self.contexts) + Style.RESET_ALL,
            ", ".join(self.keywords),
            len(self.messages) if self.messages else "No",
            self.intensity.colored_level,
            self.fdelta,
            self.duration,
        )

    @property
    def colorless_str(self):
        return "[{0}] {1}: {2} ({3} messages, {4} intensity, {5:.3f} diff, {6}s duration)".format(
            self.time_in_hms,
            "/".join(self.contexts),
            ", ".join(self.keywords),
            len(self.messages) if self.messages else "No",
            self.intensity.level,
            self.fdelta,
            self.duration,
        )

    @property
    def url(self):
        return f"https://youtu.be/{self.stream_id}?t={self.time}"

    def open_in_browser(self, browser:Browser=Browser.CHROME, browser_path=None):
        """Open highlight in browser

        Args:
            browser (str): Browser name to get default path.

            browser_path (str, optional): Path to executable
                browser file. Overrides browser argument.
                Defaults to None.
        """

        if browser_path:
            webbrowser.get(browser_path).open(self.url)
            return

        # TODO modify default path for other OS's
        if platform.system() == OSName.WINDOWS:
            if browser == Browser.CHROME:
                browser_path = (
                    r"C:/Program Files/Google/Chrome/Application/chrome.exe %s"
                )
            elif browser == Browser.EDGE:
                browser_path = (
                    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe %s"
                )
            elif browser == Browser.FIREFOX:
                browser_path = r"C:/Program Files/Mozilla Firefox/FireFox.exe %s"
            elif browser == Browser.OPERA:
                browser_path = r"C:/Program Files/Opera/Launcher.exe %s"
        elif platform.system() == OSName.LINUX:
            pass
        elif platform.system() == OSName.MAC:
            pass
        else:
            pass

        webbrowser.get(browser_path).open(self.url)

    def to_dict(self) -> dict:
        return {
            "stream_id": self.stream_id,
            "time": self.time,
            "duration": self.duration,
            "intensity": self.intensity,
            "fdelta": self.fdelta,
            "messages": self.messages,
            "keywords": self.keywords,
            "kw_emotes": self.kw_emotes,
            "contexts": self.contexts,
        }

    @property
    def time_in_hms(self):
        return datetime.timedelta(seconds=int(self.time))


@dataclass
class ContextSourceManager():
    """Dataclass to manage source paths for context files
    """
    #paths: list = field(default_factory=lambda:[DEFAULT_CONTEXT_SOURCE_PATH])
    paths: list = field(default_factory=list)
    def __repr__(self):
        return "[%s]" % ", ".join(self.paths)

    def add(self, full_path:str):
        if not full_path:
            raise ValueError("Should provide a full path")
        if full_path not in self.paths:
            self.paths.append(full_path)
            # TODO check if valid path
            return
        raise PathAlreadyExistsException(f"Warning: '{full_path}' already exists in paths")
    def remove(self, byPath:Optional[str]=None, byIndex:Optional[int]=None):
        if byPath is not None and byIndex is not None:
            raise ValueError("Can't use both byPath and byIndex parameters")
        if byPath is not None:
            self.paths.remove(byPath)
        elif byIndex is not None:
            del self.paths[byIndex]
        else:
            raise ValueError("Should provide one of the parameters")
    def update(self, old_path:str, new_path:str):
        self.remove(byPath=old_path)
        self.add(new_path)
    def reset(self):
        self.paths = []


@dataclass
class Trigger():
    phrase: str
    is_exact: bool

    def __repr__(self):
        return f"{self.phrase} ({'exact' if self.is_exact else 'inexact'})"


@dataclass
class Context():
    reaction_to: str
    triggers: list[Trigger] = field(default_factory=list)

    def __hash__(self):
        return hash(self.reaction_to)

    def __repr__(self):
        return f"{self.reaction_to}: {', '.join([str(trigger) for trigger in self.triggers])}"
