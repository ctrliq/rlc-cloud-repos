from setuptools import setup

setup(
    data_files=[
        ("config", ["config/20_rlc-cloud-repos.cfg"]),
        ("data", ["data/ciq-mirrors.yaml"]),
    ]
)
