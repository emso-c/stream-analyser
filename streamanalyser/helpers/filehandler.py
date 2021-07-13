import os

#TODO implement other functions
class FileHandler():
    """ A class to manage files like logs and cached files """

    def __init__(self, project_title, cache_fname, log_fname) -> None:
        self.project_name = project_title
        self.project_path = os.path.join(os.environment['LOCALAPPDATA'], project_title)
        self.cache_path = os.path.join(self.project_path, cache_fname)
        self.log_path = os.path.join(self.project_path, log_fname)

    def __repr__(self) -> str:
        return "Storing files into "+self.project_path

    def cache_file(self):
        pass

    def show_cached(self):
        pass

    def read_cache(self):
        pass

    def compress_file(self):
        pass

    def decompress_file(self):
        pass


streamanalyser_filemanager = FileHandler(
    'Stream Analyser',
    'Cache',
    'Logs'
)