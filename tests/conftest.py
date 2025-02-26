"""
specific file name that we can build fixtures and use them in all other test files for pytest
"""

import importlib
import warnings

import complex_base_params
import pytest

warnings.filterwarnings("error")


# TODO need default factory for mutables like dict,list,baseparams... otherwise the data is saved acrros different inits ofthe object since it's class level var
@pytest.fixture(autouse=True)
def params():
    importlib.reload(complex_base_params)
    return complex_base_params.MyParams()
