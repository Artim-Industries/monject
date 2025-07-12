from setuptools import setup, find_packages

setup(
    name="monject",
    version="1.0.6",
    author="Artim Industries",
    author_email="mauritzlemgen@artim-industries.com",
    description="An Object Mapper for MongoDB",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Artim-Industries/monject",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
