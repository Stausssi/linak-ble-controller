from os import path
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.readlines()

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md")) as f:
    long_description = f.read()

setup(
    name="linak_ble_controller",
    version="1.0.0",
    author="Stausssi",
    author_email="",
    url="https://github.com/stausssi/linak-ble-controller",
    description="Command line tool for controlling standing desks with a Linak Bluetooth controller",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages(),
    entry_points={"console_scripts": ["linak-controller=linak_ble_controller.main:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    keywords="python package linak standing desk",
    install_requires=requirements,
    zip_safe=False,
    include_package_data=True,
    package_data={"": ["example/*"]},
    python_requires=">=3.7.3",
)
