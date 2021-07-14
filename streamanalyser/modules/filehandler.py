import os

#TODO Find a way to log without circular imports
class FileHandler():
    """ A class to manage files like logs and cached files """
    
    def __init__(self,
            storage_path,
            cache_fname='Cache',
            log_fname='Logs'
        ):
        self.storage_path = storage_path
        self.cache_path = os.path.join(self.storage_path, cache_fname)
        self.log_path = os.path.join(self.storage_path, log_fname)

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


streamanalyser_filehandler = FileHandler(
    storage_path='C:\\Stream Analyser',
    cache_fname='Cache',
    log_fname='Logs',
)