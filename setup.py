from setuptools import setup

with open('requirements.txt') as req_file:
    reqs = [line.strip() for line in req_file]

setup(name='majestic',
      version='0.4.2',
      description='A basic static website generator',
      url='https://github.com/robjwells/majestic',
      author='Rob Wells',
      author_email='rob@robjwells.com',
      license='MIT',
      packages=['majestic'],
      install_requires=reqs,
      zip_safe=False,
      scripts=['bin/majestic'],
      )
