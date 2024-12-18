from setuptools import setup, find_packages

setup(
    name="api_performance_prediction",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'pandas',
        'scikit-learn',
        'numpy',
        'aiohttp',
    ],
)