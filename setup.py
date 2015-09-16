# Copyright (C) 2015 Bitquant Research Laboratories (Asia) Limited
# Released under the Simplified BSD License

from setuptools import (
    setup,
    find_packages,
    )

setup(
    name="cryptoexchange",
    version = "0.0.6",
    author="Joseph C Wang",
    author_email='joequant@gmail.com',
    url="https://github.com/joequant/cryptoexchange",
    description="API's for bitcoin exchanges",
    long_description="""API's for cryptocurrency exchanges """,
    license="BSD",
    packages=['cryptoexchange', 'cryptoexchange/util'],
    install_requires = ["websocket-client"],
    use_2to3 = True
)
                                
