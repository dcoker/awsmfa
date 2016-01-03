awsmfa
======

awsmfa simplifies multi-factor authentication with AWS by managing your
``~/.aws/credentials`` ``[default]`` profile. It allows easy role assumption and includes a set of
sample IAM policies.

If you're a small team with persistent AWS access keys sitting on developer machines looking
for an easy way to significantly improve security, this might be a good starting point for you.

Example:

::

    $ pip install awsmfa
    $ aws configure --profile identity
    ...
    $ awsmfa.py --token-code 123456
    Temporary credentials will expire in 5:59:59.746453.
    $ aws configure --profile identity get aws_access_key_id
    AKIAJ4USW7NKYGKGBBRA
    $ aws configure --profile default get aws_access_key_id
    ASIAJNCNEPCCQQRHKTBQ

