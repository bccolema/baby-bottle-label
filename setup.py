from setuptools import setup

setup(
    name="label",
    version="0.0.1",
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "flask~=2.3.2",
        "pillow~=10.0.0",
    ],
)
