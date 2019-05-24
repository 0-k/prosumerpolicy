import os.path
import logging
import yaml

""" paths.py: Sets the Paths of the input data """

__author__ = 'Ahmad Ziade, Martin Klein'
__email__ = 'm.klein@dlr.de'
__version__='1.1.0'
__credits__ = []
__status__ = "Production"


logging.basicConfig(filename='logger.log',filemode='w',level=logging.CRITICAL, format=' %(asctime)s -  %(levelname)s-  %(message)s')
logging.disable(logging.CRITICAL)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')


path_Prices='Data/Market_Data_2016.csv' #Market Prices Paths
path_Load= 'Data/summedLoadProfiles.csv' #Consumption Load Profiles Path
path_PvGen='Data/genData.csv' #PV Generation Path
path_parameters = 'Parameters/parameters.yaml' #parameter Path

def gen_Path(PATH):
    scriptdir = os.path.dirname(os.path.abspath(__file__))  # returns working directory of the current folder
    path = os.path.join(scriptdir, PATH)
    return str(path)

def read_parameters(path):
    with open(path, 'r') as stream:
        try:
            parameters = (yaml.load(stream))
            return parameters
        except yaml.YAMLError as exc:
            print("I/O Error, Unable to retrieve data from {}".format(path))
            print(exc)
