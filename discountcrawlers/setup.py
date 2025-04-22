from setuptools import setup, find_packages

setup(
    name="discountcrawlers",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "scrapy>=2.11.0",
        "scrapy-playwright>=0.0.34",
        "playwright>=1.41.0",
    ],
    python_requires=">=3.8",
) 