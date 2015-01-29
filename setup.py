import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand

import walnut


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['--pep8']
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)


setup(
    name='walnut',
    version=walnut.__version__,
    description='An asynchronous cache for Twisted',
    long_description='An asynchronous cache for Twisted',
    license='MIT',
    author='Ryan Johnson',
    author_email='escattone@gmail.com',
    url='http://github.com/escattone/walnut/',
    packages=['walnut'],
    install_requires=['twisted'],
    cmdclass=dict(test=PyTest),
    tests_require=['pytest', 'pytest-twisted', 'pytest-pep8', 'txredisapi'],
    test_suite='walnut.test',
    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
