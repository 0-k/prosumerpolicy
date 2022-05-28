import os.path
import logging
import yaml

""" paths.py: Sets the Paths of the input data """

logging.basicConfig(
    filename="logger.log",
    filemode="w",
    level=logging.CRITICAL,
    format=" %(asctime)s -  %(levelname)s-  %(message)s",
)
logging.disable(logging.CRITICAL)

formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")


path_Prices = "../data/market_data_2016.csv"  # Market Prices Paths
path_Load = "../data/summed_load_profiles.csv"  # Consumption Load Profiles Path
path_PvGen = "../data/generation_data.csv"  # PV Generation Path
path_parameters = "../example/parameters.yaml"  # parameter Path


def gen_path(PATH):
    scriptdir = os.path.dirname(
        os.path.abspath(__file__)
    )  # returns working directory of the current folder
    path = os.path.join(scriptdir, PATH)
    return str(path)


def read_parameters(path):
    with open(path, "r") as stream:
        try:
            parameters = yaml.load(stream)
            return parameters
        except yaml.YAMLError as exc:
            print("I/O Error, Unable to retrieve data from {}".format(path))
            print(exc)