from setuptools import setup


def get_version():
    return open('awsmfa/_version.py').readline().strip().strip('"')


setup(
    name='awsmfa',
    version=get_version(),
    description='Manage temporary MFA AWS credentials.',
    long_description=open('README.rst').read(),
    author='Doug Coker',
    author_email='dcoker@gmail.com',
    url='https://github.com/dcoker/awsmfa/',
    include_package_data=False,
    package_data={
        'awsmfa': [
            'awsmfa-basic-policies.json'
        ],
    },
    license='https://www.apache.org/licenses/LICENSE-2.0',
    packages=[
        'awsmfa'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Security',
    ],
    zip_safe=False,
    install_requires=[
        'botocore>=1.4.0',
        'boto3>=1.3.0',
        'pytz>=2016.1',
        'six>=1.10.0'
    ],
    entry_points={
        'console_scripts': [
            'awsmfa=awsmfa.__main__:main'
        ]
    },
)
