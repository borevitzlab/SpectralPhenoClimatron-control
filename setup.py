from setuptools import setup

setup(
    name="spcControl",
    install_requires=['psycopg2>=2.4.6', ],
    packages=['spcControl', 'spcControl.monitor',],
    version="0.1rc4",
    description=("A controller module for Conviron growth cabinets "
        "and Heliospectra mulitspectrat lamps"),
    author="Kevin Murray",
    author_email="k.d.murray.91@gmail.com",
    url="https://github.com/borevitzlab/SpectralPhenoClimatron-control",
    keywords=["hvac", "telnet", "heliospectra", "spcControl"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "License :: OSI Approved :: GNU Lesser General Public License v3 "
        "(LGPLv3)",
        "Operating System :: OS Independent",
    ],
    )
