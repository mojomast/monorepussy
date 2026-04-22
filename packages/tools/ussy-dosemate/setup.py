from setuptools import setup, find_packages

setup(
    name="dosemate",
    version="1.0.0",
    description="Pharmacokinetic ADME Modeling for Code Change Propagation",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "dosemate=dosemate.cli:main",
        ],
    },
)
