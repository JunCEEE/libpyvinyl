"""
:module BaseCalculator: Module hosting the BaseCalculator class.

"""

####################################################################################
#                                                                                  #
# This file is part of libpyvinyl - The APIs for Virtual Neutron and x-raY         #
# Laboratory.                                                                      #
#                                                                                  #
# Copyright (C) 2021  Carsten Fortmann-Grote, Juncheng                             #
#                                                                                  #
# This program is free software: you can redistribute it and/or modify it under    #
# the terms of the GNU Lesser General Public License as published by the Free      #
# Software Foundation, either version 3 of the License, or (at your option) any    #
# later version.                                                                   #
#                                                                                  #
# This program is distributed in the hope that it will be useful, but WITHOUT ANY  #
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A  #
# PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details. #
#                                                                                  #
# You should have received a copy of the GNU Lesser General Public License along   #
# with this program.  If not, see <https://www.gnu.org/licenses/                   #
#                                                                                  #
####################################################################################

from abc import abstractmethod
from typing import Union
from libpyvinyl.AbstractBaseClass import AbstractBaseClass
from libpyvinyl.BaseData import BaseData, DataCollection

from libpyvinyl.Parameters import CalculatorParameters

from tempfile import mkstemp
import copy
import dill
import h5py
import sys
import logging
import os

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(message)s", level=logging.WARNING
)


class BaseCalculator(AbstractBaseClass):
    """

    :class BaseCalculator: Base class of all calculators.

    This class is provides the libpyvinyl API. It defines all methods
    through which a user interacts with the simulation backengines.

    This class is to be used as a base class for all calculators that implement
    a special simulation module, such as a photon diffraction calculator. Such a
    specialized Calculator has the same interface to the simulation
    backengine as all other ViNYL Calculators.

    A Complete example including a instrument and calculators can be found in
    `test/integration/plusminus`

    """

    def __init__(
        self,
        name: str,
        input: Union[DataCollection, list, BaseData],
        output_keys: Union[list, str],
        output_data_types: list,
        output_filenames: Union[list, str, None] = None,
        instrument_base_dir: str = "./",
        calculator_base_dir: str = "BaseCalculator",
        parameters: CalculatorParameters = None,
        dumpfile: str = None,
    ):
        """

        :param name: The name of this calculator.
        :type name: str

        :param name: The input of this caluclator. It can be a `DataCollection`,
        a list of `DataCollection`s or a single Data Object.
        :type name: DataCollection, list or BaseData

        :param output_keys: The key(s) of this caluclator's output data. It's a list of `str`s or
        a single str.
        :type output_keys: list or str

        :param output_data_types: The data type(s), i.e., classes, of each output. It's a list of the
        data classes or a single data class. The available data classes are based on `BaseData`.
        :type output_data_types: list or DataClass

        :param output_filenames: The name(s) of the output file(s). It can be a str of a filename or
        a list of filenames. If the mapping is dict mapping, the name is `None`. Defaults to None.
        :type output_filenames: list or str

        :param instrument_base_dir: The base directory for the instrument to which this calculator
        belongs. Defaults to "./". The final exact output file path depends on `instrument_base_dir`
        and `calculator_base_dir`: `instrument_base_dir`/`calculator_base_dir`/filename
        :type instrument_base_dir: str

        :param calculator_base_dir: The base directory for this calculator. Defaults to "./". The final
        exact output file path depends on `instrument_base_dir` and
        `calculator_base_dir`: `instrument_base_dir`/`calculator_base_dir`/filename
        :type instrument_base_dir: str

        :param parameters: The parameters for this calculator.
        :type  parameters: Parameters

        :param dumpfile: If given, load a previously dumped (aka pickled) calculator.
        :type dumpfile: str

        :param kwargs: (key, value) pairs of further arguments to the calculator, e.g input_path, output_path.

        If both 'parameters' and 'dumpfile' are given, the dumpfile is loaded
        first. Passing a parameters object may be used to update some
        parameters.

        TODO:
        Example:
        ```
        # Define a specialized calculator.
        class MyCalculator(BaseCalculator):

            def __init__(self, parameters=None, dumpfile=None, **kwargs):
                super()__init__(parameters, dumpfile, **kwargs)

            def backengine(self):
                os.system("my_simulation_backengine_call")

            def saveH5(self):
                # Format output into openpmd hdf5 format.

        class MyParameters(Parameters):
            pass

        my_calculator = MyCalculator(my_parameters)

        my_calculator.backengine()

        my_calculator.saveH5("my_sim_output.h5")
        my_calculater.dump("my_calculator.dill")
        ```

        """
        # Initialize the variables
        self.__name = None
        self.__instrument_base_dir = None
        self.__calculator_base_dir = None
        self.__input = None
        self.__output_keys = None
        self.__output_data_types = None
        self.__output_filenames = None
        self.__parameters = None

        self.name = name
        self.input = input
        self.output_keys = output_keys
        self.output_data_types = output_data_types
        self.output_filenames = output_filenames
        self.instrument_base_dir = instrument_base_dir
        self.calculator_base_dir = calculator_base_dir
        self.parameters = parameters

        # Create output data objects according to the output_data_classes
        self.__init_output()

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value):
        if isinstance(value, str):
            self.__name = value
        else:
            raise TypeError(
                f"Calculator: `name` is expected to be a str, not {type(value)}"
            )

    @property
    def parameters(self) -> CalculatorParameters:
        return self.__parameters

    @parameters.setter
    def parameters(self, value: CalculatorParameters):
        self.set_parameters(value)

    def set_parameters(self, value: CalculatorParameters):
        """Set the calculator parameters"""
        if isinstance(value, CalculatorParameters):
            self.__parameters = value
        elif value is None:
            self.init_parameters()
        else:
            raise TypeError(
                f"Calculator: `parameters` is expected to be CalculatorParameters, not {type(value)}"
            )

    @property
    def instrument_base_dir(self) -> str:
        return self.__instrument_base_dir

    @instrument_base_dir.setter
    def instrument_base_dir(self, value):
        self.set_instrument_base_dir(value)

    def set_instrument_base_dir(self, value: str):
        """Set the instrument base directory"""
        if isinstance(value, str):
            self.__instrument_base_dir = [value]
        else:
            raise TypeError(
                f"Calculator: `instrument_base_dir` is expected to be a str, not {type(value)}"
            )

    @property
    def calculator_base_dir(self) -> str:
        return self.__calculator_base_dir

    @calculator_base_dir.setter
    def calculator_base_dir(self, value):
        self.set_calculator_base_dir(value)

    def set_calculator_base_dir(self, value: str):
        """Set the calculator base directory"""
        if isinstance(value, BaseData):
            self.__calculator_base_dir = [value]
        else:
            raise TypeError(
                f"Calculator: `calculator_base_dir` is expected to be a str, not {type(value)}"
            )

    @property
    def input(self) -> DataCollection:
        return self.__input

    @input.setter
    def input(self, value):
        self.set_input(value)

    def set_input(self, value: Union[DataCollection, list, BaseData]):
        """Set the calculator input data. It can be a DataCollection, list or BaseData object."""
        if isinstance(value, DataCollection):
            self.__input = value
        elif isinstance(value, list):
            self.__input = DataCollection(*value)
        elif isinstance(value, BaseData):
            self.__input = DataCollection(value)
        else:
            raise TypeError(
                f"Calculator: `input` can be a DataCollection, list or BaseData object, and will be treated as a DataCollection. Your input type: {type(value)} is not accepted."
            )

    @property
    def output_keys(self) -> list:
        return self.__output_keys

    @output_keys.setter
    def output_keys(self, value):
        self.set_output_keys(value)

    def set_output_keys(self, value: Union[list, str]):
        """Set the calculator output keys. It can be a list of str or a single str."""
        if isinstance(value, list):
            for item in value:
                assert type(item) is str
            self.__output_keys = value
        elif isinstance(value, str):
            self.__output_keys = [value]
        else:
            raise TypeError(
                f"Calculator: `output_keys` can be a list or str, and will be treated as a list. Your input type: {type(value)} is not accepted."
            )

    @property
    def output_data_types(self) -> list:
        return self.__output_data_types

    @output_data_types.setter
    def output_data_types(self, value):
        self.set_output_data_types(value)

    def set_output_data_types(self, value: Union[list, BaseData]):
        """Set the calculator output data type. It can be a list of DataClass or a single DataClass."""
        if isinstance(value, list):
            for item in value:
                assert type(item) is BaseData
            self.__output_data_types = value
        elif isinstance(value, BaseData):
            self.__output_data_types = [value]
        else:
            raise TypeError(
                f"Calculator: `output_data_types` can be a list or a subclass of BaseData, and will be treated as a list. Your input type: {type(value)} is not accepted."
            )

    @property
    def output_filenames(self) -> list:
        return self.__output_filenames

    @output_filenames.setter
    def output_filenames(self, value):
        self.set_output_filenames(value)

    def set_output_filenames(self, value: Union[list, str, None]):
        """Set the calculator output filenames. It can be a list of filenames or just a single str."""
        if isinstance(value, list):
            for item in value:
                assert type(item) is str or type(None)
            self.__output_filenames = value
        elif isinstance(value, (BaseData, type(None))):
            self.__output_filenames = [value]
        else:
            raise TypeError(
                f"Calculator: `output_filenames` can be a list or just a str or None, and will be treated as a list. Your input type: {type(value)} is not accepted."
            )

    @property
    def output(self):
        """The output of this calculator"""
        return self.__output

    @property
    def data(self):
        """The alias of output. It's not recommened to use this varialble name due to it's Ambiguity."""
        return self.__output

    @abstractmethod
    def init_parameters(self):
        # This is just an example. Override this function in a concrete class.
        parameters = CalculatorParameters()
        times = parameters.new_parameter(
            "plus_times", comment="How many times to do the plus"
        )
        times.value = 1
        self.parameters = parameters

    def __init_output(self):
        """Create output data objects according to the output_data_types"""
        output = DataCollection()
        for i, key in enumerate(self.output_keys):
            output_data = self.output_data_types[i](key)
            output.add_data(output_data)
        self.__output = output

    def __call__(self, parameters=None, **kwargs):
        """The copy constructor

        :param parameters: The parameters for the new calculator.
        :type  parameters: CalculatorParameters

        :param kwargs: key-value pairs of parameters to change in the new instance.

        :return: A new parameters instance with optionally changed parameters.

        """

        new = copy.deepcopy(self)

        new.__dict__.update(kwargs)

        if parameters is not None:
            new.parameters = parameters

        return new

    # TODO: modify to from dump
    @classmethod
    def __load_from_dump(self, dumpfile):
        """ """
        """
        Load a dill dump and initialize self's internals.

        """

        with open(dumpfile, "rb") as fhandle:
            try:
                tmp = dill.load(fhandle)
            except:
                raise IOError("Cannot load calculator from {}.".format(dumpfile))

        self.__dict__ = copy.deepcopy(tmp.__dict__)

        del tmp

    def dump(self, fname=None):
        """
        Dump class instance to file.

        :param fname: Filename (path) of the file to write.

        """

        if fname is None:
            _, fname = mkstemp(
                suffix="_dump.dill",
                prefix=self.__class__.__name__[-1],
                dir=os.getcwd(),
            )
        try:
            with open(fname, "wb") as file_handle:
                dill.dump(self, file_handle)
        except:
            raise

        return fname

    @abstractmethod
    def backengine(self):
        raise NotImplementedError

# This project has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement No. 823852.
