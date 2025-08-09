"""
Setup script for the TradingAgents package.
"""

from setuptools import setup, find_packages

setup(
    name="trading-agents",
    version="0.1.0",
    description="Multi-Agents LLM Financial Trading Framework",
    author="DarrenWang",
    author_email="wangyang9113@gmail.com",
    url="https://github.com/boundles/trading-agents",
    packages=find_packages(),
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Trading Industry",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
)
