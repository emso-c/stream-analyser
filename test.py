from pprint import pprint

from streamanalyser.helpers.datacollector import DataCollector
from streamanalyser.helpers.datarefiner import DataRefiner
from streamanalyser.helpers.chatanalyser import ChatAnalyser


id = 'X_TGEG8efoc' #micomet bunny
id = 'VtZfehdSHb4' # pekora i guess
id = 'Qi1H7xL-xVo' #micomet gta
id = 'TqCsK1IriTA' # mikkorone a way out

collector = DataCollector(id, msglimit=100, verbose=True)
metadata = collector.collect_metadata()
raw_msgs = collector.fetch_raw_messages()

refiner = DataRefiner(verbose=True)
messages = refiner.refine_raw_messages(raw_msgs)
canalyser = ChatAnalyser(messages)
canalyser.init_intensity(
    #config...
)

pprint(canalyser.get_frequency())