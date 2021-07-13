from dataclasses import dataclass, field
import datetime
import webbrowser
from colorama import init, Fore, Style
from colorama.ansi import AnsiFore
init()


@dataclass
class Author():
    id: str
    name: str

    def __repr__(self):
        return f"{self.name}: {self.id}"

    def __hash__(self):
        return hash(self.id)


@dataclass
class Message():
    id: str
    text: str
    time: int
    author: Author

    @property
    def time_in_hms(self):
        return datetime.timedelta(seconds=int(self.time))

    @property
    def colorless_str(self):
        return f"[{self.time_in_hms}] {self.author.name}: {self.text}"
    
    def __repr__(self):
        return f"[{self.time_in_hms}] {Fore.YELLOW+self.author.name+Style.RESET_ALL}: {self.text}"


@dataclass
class Intensity():
    level: str
    constant: int
    color: AnsiFore

    def __repr__(self):
        return f"{self.color+self.level+Style.RESET_ALL}: {self.constant}"

    @property
    def colored_level(self):
        return self.color+self.level+Style.RESET_ALL


@dataclass
class Highlight():
    stream_id: str
    time: int
    duration: int
    intensity: Intensity = None
    fdelta: float = 0.0  # is the difference between frequencies from start to finish
    messages: list[Message] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    contexts: set[str] = field(default_factory=set)

    def __repr__(self):
        return "[{0}] {1}: {2} ({3} messages, {4} intensity, {5:.3f} diff, {6}s duration)".format(
            self.time_in_hms,
            Fore.LIGHTRED_EX+'/'.join(self.contexts)+Style.RESET_ALL,
            ', '.join(self.keywords),
            len(self.messages) if self.messages else 'No',
            self.intensity.colored_level,
            self.fdelta,
            self.duration
        )

    @property
    def colorless_str(self):
        return "[{0}] {1}: {2} ({3} messages, {4} intensity, {5:.3f} diff, {6}s duration)".format(
            self.time_in_hms,
            '/'.join(self.contexts),
            ', '.join(self.keywords),
            len(self.messages) if self.messages else 'No',
            self.intensity.level,
            self.fdelta,
            self.duration
        )

    @property
    def url(self):
        return f'https://youtu.be/{self.stream_id}?t={self.time}'
    
    # TODO add other browsers
    def open_in_chrome(self):
        webbrowser.get(r'C:/Program Files/Google/Chrome/Application/chrome.exe %s').open(self.url)

    @property
    def time_in_hms(self):
        return datetime.timedelta(seconds=int(self.time))
        