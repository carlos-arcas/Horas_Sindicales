from setuptools import find_namespace_packages, setup


setup(
    name="horas-sindicales",
    version="0.0.0",
    packages=find_namespace_packages(
        include=[
            "app",
            "app.*",
            "aplicacion",
            "aplicacion.*",
        ]
    ),
)
