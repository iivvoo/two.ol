from setuptools import setup, find_packages
import os

version = '0.9'

setup(name='two.ol',
      version=version,
      description="It takes Two do Django. A django mini framework",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='',
      author='Ivo van der Wijk',
      author_email='two@in.m3r.nl',
      url='http://github.com/iivvoo/two.ol',
      license='BSD',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['two'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
      ],
      entry_points={
        "console_scripts":[
            "newrelic=two.ol.newrelicfix:main",
            "nr-run=two.ol.newrelicfix:runner",
        ]
      },

      )

