import os

from setuptools import find_packages, setup


def parse_requirements( filename ):
    with open( filename ) as fp:
        return list(filter(None, (r.strip('\n ').partition('#')[0] for r in fp.readlines())))


version_tag = "1.2.0"

kwargs = {}

with open('README.md') as f:
    kwargs['long_description'] = f.read()

# Parse requirement file and transform it to setuptools requirements'''
requirements = 'requirements.txt'
if os.path.exists(requirements):
    kwargs['install_requires']=parse_requirements( requirements )

setup(
    name='wmtscache-qgis-plugin',
    version=version_tag,
    author='3Liz',
    author_email='infos@3liz.org',
    maintainer='David Marteau',
    maintainer_email='dmarteau@3liz.org',
    description="WMTS cache implementation for qgis server",
    url='',
    packages=find_packages(include=['wmtsCacheServer']),
    entry_points={
        'console_scripts': [
            'wmtscache = wmtsCacheServer.cachemngr:main',
        ],
    },
    # Add manifest to main package
    include_package_data=True,
    package_data={"pyqgisserver": ['metadata.txt'] },
    classifiers=[
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
    **kwargs
)
