from setuptools import setup
def readme():
    with open('README.md') as f:
        return f.read()

setup(name='prosumerPolicy',
      version='0.1',
      description='Household solar self-consumption model under different policies',
      long_description=readme(),
      keywords='',
      url='',
      author=['Ahmad Ziade','Martin Klein'],
      license='MIT',
      packages=['prosumerPolicy'],
      install_requires=['pandas','numpy','gurobi']
      )