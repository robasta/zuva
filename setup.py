from pathlib import Path

from setuptools import setup, find_packages

from sunsynk.version_info import Version

Version.generate()

requirements_path = Path(__file__).resolve().parent / 'requirements.txt'
install_reqs = [
    line.strip()
    for line in requirements_path.read_text().splitlines()
    if line.strip() and not line.strip().startswith('#')
]

setup(
    name='sunsynk-api-client',
    version=Version.get(),
    description='API client for interacting with SunSynk APIs.',
    long_description='API client for interacting with SunSynk APIs.',
    author='James Ridgway',
    url='https://github.com/jamesridgway/sunsynk-api-client',
    license='MIT',
    packages=find_packages(),
    install_requires=install_reqs
)
