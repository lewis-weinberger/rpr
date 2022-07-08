from setuptools import setup

setup(
    name="rpr",
    version="0.1",
    py_modules=["rpr"],
    install_requires=[
        "Flask",
        "Flask-Caching",
        "WTForms"
    ]
)
