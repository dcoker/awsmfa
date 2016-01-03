awsmfa
======

awsmfa simplifies multi-factor authentication with AWS by managing your
``~/.aws/credentials`` ``[default]`` profile.

If you are a small team with long-lived AWS access keys sitting on developer machines, and you are
looking for an easy way to improve security, this might be a good starting point for you. The
package includes a sample set of IAM policies (in a CloudFormation template) to get you started.

Example:

::

    $ pip3 install --user awsmfa
    ...
    $ aws configure --profile identity
    ...
    $ awsmfa.py --token-code 123456
    Temporary credentials will expire in 5:59:59.746453.
    $ aws configure --profile identity get aws_access_key_id
    AKIAJ4USW7NKYGKGBBRA
    $ aws configure get aws_access_key_id
    ASIAJNCNEPCCQQRHKTBQ

