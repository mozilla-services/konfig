from setuptools import setup, find_packages


with open('README.rst') as f:
    README = f.read()


mplv2 = "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)"
classifiers = ["Programming Language :: Python", mplv2,
               "Development Status :: 5 - Production/Stable"]


setup(name='konfig',
      version='1.0',
      url='https://github.com/mozilla-services/konfig',
      packages=find_packages(),
      long_description=README,
      description=("Yet Another Config Parser."),
      author="Tarek Ziade",
      author_email="tarek@mozilla.com",
      include_package_data=True,
      install_requires = [
        'configparser', 'argparse'
      ],
      zip_safe=False,
      classifiers=classifiers,
      )

