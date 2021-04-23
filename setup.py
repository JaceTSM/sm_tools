import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sm_tools",
    version="0.0.1",
    author="Tim Murphy",
    author_email="jac3tssm@gmail.com",
    description="StepMania tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/JaceTSM/sm_tools",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.6",
    install_requires=[
        'pandas',
    ],
    entry_points={
        'console_scripts': ['step_parser=step_parser.cli:step_parser_cli'],
    }
)
