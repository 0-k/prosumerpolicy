from __future__ import print_function
import logging

from paths import *
import pandas as pd


__all__=['import_Load', 'import_PV', 'import_Prices']


def import_Load(path=path_Load):
    try:
        absPath = gen_Path(path_Load)
        totalload = pd.read_csv(absPath, header=None, delimiter=';')
        logging.info("Load Successfully Imported from {}".format(path_Load))
        return totalload
    except:
        logging.WARNING("Load Input from {} Error".format(path_Load))

def import_PV(path=path_PvGen):
    try:
        absPath = gen_Path(path_PvGen)
        totalPvGen = pd.read_csv(absPath, header=None)
        logging.info("PV Gen Successfully Imported from {}".format(path_PvGen))
        return totalPvGen
    except:
        logging.WARNING("Pv Gen Input from {} Error".format(path_PvGen))

def import_Prices(path=path_Prices):
    try:
        absPath = gen_Path(path_Prices)
        totalPrices = pd.read_csv(absPath, sep=';')
        logging.info("Prices Successfully Imported from {}".format(path_Prices))
        return totalPrices
    except:
        logging.WARNING("Price Input from {} Error ".format(path_Prices))
