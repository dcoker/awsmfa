.. image:: https://img.shields.io/pypi/v/awsmfa.svg?maxAge=600   :target: 

awsmfa
======

awsmfa simplifies multi-factor authentication for developers using AWS by fetching temporary
credentials from STS and storing it in your ``~/.aws/credentials`` file.

If you are a small team with long-lived AWS access keys sitting on developer machines, and you are
looking for an easy way to improve security, this might be a good starting point for you. The
package includes a sample set of IAM policies (in a CloudFormation template) to get you started.

awsmfa is intended to be used by organizations that use MFA with STS AssumeRole and IAM
policies with the aws:MultiFactorAuthPresent condition variable. The following are common
scenarios where this tool is useful:

1. Developer has a restrictive set of IAM policies attached to their account, and a
   less-restrictive set of policies that require aws:MultiFactorAuthPresent.
2. Developer has a restrictive set of IAM policies attached to their account, and uses role
   assumption for specific job/role functions, and the IAM policies for AssumeRole require
   aws:MultiFactorAuthPresent.

By default, the long-lived credentials (access key and secret key) are expected
in a profile called ``[identity]`` and the temporary credentials (access key,
secret key, session token) are stored in ``[default]``. These are
configurable with the ``--identity-profile`` and ``--target-profile`` flags,
respectively.

The MFA token can be passed on the command line with ``--token-code`` or
entered interactively.

Run ``awsmfa -h`` for additional information.

Getting started:

::

    $ pip3 install --user awsmfa
    ...
    $ aws configure --profile identity
    ... specify your long-lived credentials
    $ awsmfa --token-code 123456
    Temporary credentials will expire in 5:59:59.746453.
    $ aws configure --profile identity get aws_access_key_id
    AKIAJ4USW7NKYGKGBBRA
    $ aws configure get aws_access_key_id
    ASIAJNCNEPCCQQRHKTBQ


Example w/role assumption:

::

    $ awsmfa arn:aws:iam::123456789012:role/s3access


