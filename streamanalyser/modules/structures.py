from dataclasses import dataclass, field
import datetime
import webbrowser
import platform
from colorama import init, Fore, Style
from colorama.ansi import AnsiFore

init()


@dataclass
class Author:
    id: str
    name: str

    def __repr__(self):
        return f"{self.name}: {self.id}"

    def __hash__(self):
        return hash(self.id)


@dataclass
class Message:
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

    def __hash__(self):
        return hash(self.id)


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
    fdelta: float = 0.0  # is the difference between frequencies from start to finish
    messages: list[Message] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
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

    def open_in_browser(self, browser="chrome", browser_path=None):
        """Open highlight in browser

        Args:
            browser (str): Browser name to get default path.
                Current choices are:
                - chrome
                - edge
                - firefox
                - opera
                Defaults to 'chrome'.

            browser_path (str, optional): Path to executable
                browser file. Overrides browser argument.
                Defaults to None.
        """

        if browser_path:
            webbrowser.get(browser_path).open(self.url)
            return

        # TODO modify default path for other OS's
        if platform.system == "Windows":
            if browser == "chrome":
                browser_path = (
                    r"C:/Program Files/Google/Chrome/Application/chrome.exe %s"
                )
            elif browser == "edge":
                browser_path = (
                    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe %s"
                )
            elif browser == "firefox":
                browser_path = r"C:/Program Files/Mozilla Firefox/FireFox.exe %s"
            elif browser == "opera":
                browser_path = r"C:/Program Files/Opera/Launcher.exe %s"
        elif platform.system == "Linux":
            pass
        elif platform.system == "Darwin":
            pass
        else:
            pass

        webbrowser.get(browser_path).open(self.url)

    @property
    def time_in_hms(self):
        return datetime.timedelta(seconds=int(self.time))
