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
        'Topic :: Security',
        'Programming Language :: Python',
    ],
    zip_safe=False,
    install_requires=[
        'botocore>=1.3'
    ],
    entry_points={
        'console_scripts': [
            'awsmfa=awsmfa.__main__:main'
        ]
    },
)
