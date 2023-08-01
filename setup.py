from setuptools import setup

setup(
    name="label",
    version="1.0.0",
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "bottle~=0.12.25",
        "pillow~=10.0.0",
    ],
)
