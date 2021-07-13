import os
from filehandler import streamanalyser_filehandler as sf

class StreamAnalyser():
    def __init__(self):
        pass
        #project_title = 'Stream Analyser' #TODO get title from project metadata
        #project_path = os.path.join(os.environment['LOCALAPPDATA'], project_title)
        #cache_path = os.path.join(project_path, 'Cache')
        #log_path = os.path.join(project_path, 'Logs')

        #self.fm = FileManager(
        #    project_title,
        #    project_path,
        #    cache_path,
        #    log_path
        #)
    
    def __enter__(self):
        return self

    def __exit__(self):
        # delete object
        for file in self.files:
            os.unlink(file)

#usage
with StreamAnalyser() as sa:
    sa.do_stuff()
