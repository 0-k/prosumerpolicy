# Prosumer Policy

This project aims to model the optimum dispatch behaviour of households with PV and battery systems under different policy instrument mixes. Household electricity consumers with photovoltaics and battery systems are referred to as prosumers since they both produce and consume electricity. This model uses the Gurobi optimizer (plans on adding more soon, contact us if you want to have more interfaces) to determine the optimal household charging behaviour under different policies such as real-time electricity pricing schemes, time varying remunerations schemes and fixed network charges.


## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

This model depends on the packages Numpy and Pandas for data wrangling and [Gurobi](https://www.gurobi.com/documentation/8.0/quickstart_windows/py_python_interface) python package for optimization. Gurobi offers a free license for Academic use.  


### Sample Usage

The interface point between the package and the user is the Model Class. An instance of this class can be created as follows:

```
w=Model()
```
Each model instance has a set of system attributes, policy attributes and optimization parameters.
##### System Attributes
System attributes include, among others, PV and battery system size. Other parameters, such as battery efficiencies etc.. can be changed in the parametrs.yaml file. 

Battery and PV size can be set as follows:

```
w.PV.size=5 #sets PV size to 5 kW
w.Battery.size=5 #sets Battery size to 5 kWh
```
Other parameters can be updated either from the default YAML file or a custom YAML file as follows:

```
w.PV.update_parameters() #updates from default YAML file

w.Battery.update_parameters('customFile.yaml') #updates from custom YAML File
```
##### Policy Attributes  
For each instance of Model there exists a specific regulatory regime made up of:
* RTP: Real Time Electricity Pricing
* VFIT: Variable Feed in Remuneration
* FixedNetworkCharges: Fixed or Volumetric Network charges

Parameters can be defined in YAML file and could also be changed as follows:
```
w.Policy.isRTP=False
```
or through a custom (or default) yaml parameter file
```
w.Policy.update_parameters('customFile.yaml') 
``` 

##### Optimization Parameters
Optimization parameters such as foresight duration and starting day of year can be edited as follows

```
w.timeDuration=24 #sets foresight to 24h
w.day=45 #sets the day 45 of the year
 ```
 ##### Optimization and Results Extracting
With the aforementioned parameters the Model can be optimized:
```
print(w.opt) #returns the dispatch as a DataFrame 
print(w.revenue) #returns the revenue 
``` 
Additional parameters can be computed such as **MAI**, **IRR**, etc.. The **MAI** stands for **M**arket **A**lignment **I**ndicator which measures the performance of a certain instrument mixes in comparison to an ideal case  


 
## Contributing

Please contact us via email to m.klein@dlr.de.


## Authors

* **Ahmad Ziade** - *Initial work* 
* **Martin Klein** - *Initial work* 


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

Marc Deissenroth, Kristina Nienhaus, Laurens de Vries
