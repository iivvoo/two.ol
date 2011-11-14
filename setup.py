from setuptools import setup, find_packages
import os

version = '1.0'

setup(name='qr.funqr',
      version=version,
      description="FunQR (pronounced as Funkier) allows creation of simple and funky QR codes",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='',
      author='Ivo van der Wijk',
      author_email='ivo@m3r.nl',
      url='http://qr.nl/',
      license='Closed, propietary',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['qr'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'qrencode'
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )

