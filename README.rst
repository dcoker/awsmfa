======
awsmfa
======

.. image:: https://img.shields.io/pypi/v/awsmfa.svg?maxAge=600   :target:

awsmfa helps AWS users use two factor authentication (MFA) with their
``~/.aws/credentials`` file. awsmfa also makes it easy to rotate your
access keys and to use role assumption. MFA, key rotation, and role
assumption are three best practices to use when securing your AWS
environment from attacks.

awsmfa is ideal for engineering teams that have long-lived AWS access
keys sitting on developer machines. If you are looking for an easy way
to improve your team's security, this might be a good starting
point for you.

--------------------------
When do I want to use MFA?
--------------------------

Most teams give their engineers an AWS Access Key pair and they are
written to an ``~/.aws/credentials`` file, or stuffed in a ``.bashrc``,
and forgotten about. This is a security problem because those
credentials are stored in plaintext and can be exfiltrated by malware,
copied off of stolen laptops, etc.

One simple solution to this is to configure your AWS account so that
those credentials are not useful unless the user has also asserted
their identity by way of two-factor authentication.

IAM, S3, and other types of AWS Policies allow you to require that the user has
recently verified their identity using two-factor authentication (MFA).
This criteria is specified in the policy documents using a ``Condition``
block, like this::

    "Condition": {
        "Bool": {
            "aws:MultiFactorAuthPresent": "true"
        }
    }

Typical deployments involve attaching policies to your users that create two
levels of access.

1. The first level allows very few privileges, such as
only those necessary to identify themselves (iam:GetUser), enable an MFA
device (iam:EnableMFADevice), list or resync their MFA devices (iam:ListMFADevices,
iam:ResyncMFADevice), and to acquire temporary credentials (sts:GetSessionToken).
These are available to the user just by merely proving they have the AWS Access Key ID
and the AWS Secret Access Key.

2. The second level grants more privileges, but requires that the user has recently
authenticated themselves using two-factor authentication. In small teams, the privileges
may be as generous as full administrative access of the AWS account. In more secure
environments, the policies can be arbitrarily fine.

You can read more about using MFA with AWS Policies in the
`AWS documentation <http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_configure-api-require
.html#MFAProtectedAPI-user-mfa>`_.

--------
Policies
--------

If you have pre-existing IAM policies, the easiest way to get started is to just attach the
``sts:MultiFactorAuthPresent`` condition to any of your existing policies that you want to secure.

If you don't have any IAM policies yet, consider using the `starter kit of basic IAM policies
<https://github.com/dcoker/awsmfa/blob/master/awsmfa/awsmfa-basic-policies.json>`_ included
with awsmfa. Most teams -- even teams of one -- will be able to use that template as-is
and as a starting point for more customized policies. You can install these
policies using the CloudFormation Console or using the command line examples from
the template.

---------------
Getting Started
---------------

To use awsmfa, you'll need:

#. an IAM account (or a root account)
#. an MFA device attached to that account
#. to be allowed to call iam:GetUser, iam:ListMfaDevices, and iam:GetSessionToken.
#. your ``~/.aws/credentials`` file configured with your long-lived AWS Access Key pair. If you don't have this, create one with::

    $ pip install --user awscli
    $ aws configure --profile identity

Installing awsmfa is as easy as installing a pip package::

    $ pip install --user awsmfa
    ...

Once installed, running ``awsmfa`` will verify your MFA devices and then prompt you for the MFA code. Once AWS
verifies your MFA code, awsmfa will write out your new temporary credentials to the ``[default]`` section of your
``~/.aws/credentials`` file. The default section is read by most AWS SDKs automatically. Here's an example::

    $ awsmfa
    MFA Token Code: 123456
    Temporary credentials will expire in 5:59:59.746453.

By default, the long-lived credentials (access key and secret key) are read from a profile called ``[identity]`` and
the temporary credentials (access key, secret key, session token) are written to ``[default]``. These are
configurable with the ``--identity-profile`` and ``--target-profile`` flags,
or ``AWS_MFA_IDENTITY_PROFILE`` and ``AWS_MFA_TARGET_PROFILE`` environment variables,
respectively.

You can also provide the code from the command line::

    $ awsmfa --token-code 123456
    Temporary credentials will expire in 5:59:59.746453.

Most awsmfa behaviors are controlled by command line flags or environment variables. Run with ``--help`` for more
details.

::

    $ awsmfa --help
    usage: awsmfa [-h] [--version] [--aws-credentials AWS_CREDENTIALS]
                  [-d DURATION] [-i IDENTITY_PROFILE]
                  [--serial-number SERIAL_NUMBER] [-t TARGET_PROFILE]
                  [--role-session-name ROLE_SESSION_NAME] [-c TOKEN_CODE]
                  [--rotate-identity-keys]
                  [role-to-assume]
    ...

------------
Skipping MFA
------------

By default, awsmfa sends your MFA token code to AWS when acquiring temporary credentials. This is optional behavior.
If you don't want to use MFA, pass ``-c skip`` or set the ``AWS_MFA_TOKEN_CODE`` environment variable to ``skip``.
Example::

    $ awsmfa -c skip

Note that the temporary credentials obtained in this way will not satisfy the ``sts::MultiFactorAuthPresent`` condition
variable.

---------------
Role Assumption
---------------

awsmfa can also help you with `role assumption <http://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html>`_.
If you'd like to assume a role, pass the full ARN of the role as the
first parameter to awsmfa. Example::

    $ awsmfa arn:aws:iam::123456789012:role/s3access

You can also customize the role session name::

    $ awsmfa --role-session-name ingest arn:aws:iam::123456789012:role/s3access

------------
Key Rotation
------------

Rotating your access keys regularly is a good security practice. If your IAM user is allowed to call
iam:ListAccessKeys, iam:DeleteAccessKeys, and iam:CreateAccessKey, awsmfa can also
automatically rotate your access keys automatically when you acquire temporary credentials. Example::

    $ awsmfa --rotate-identity-keys
    MFA Token Code:
    Temporary credentials will expire in 5:59:59.677774.
    Rotating from AKIAIM55UP4UAQDYGNHA to AKIAJCB6F3RJ3GJFIUGQ.
    work-eng profile updated.

If you want to rotate your identity keys every time you acquire temporary credentials, you can set the
AWS_MFA_ROTATE_IDENTITY_KEYS environment variable. Example::

    $ echo AWS_MFA_ROTATE_IDENTITY_KEYS=True >> ~/.bashrc

-----------------------------
Setting Environment Variables
-----------------------------

Some AWS tools can only read credentials from environment variables (``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``,
and ``AWS_SESSION_TOKEN``). ``awsmfa --env`` will print shell commands to define those variables. Example::

    $ awsmfa --env
    Enter MFA Code: 123456
    Temporary credentials will expire in 5:59:59.945582.
    AWS_ACCESS_KEY_ID=ASIAIYM...; export AWS_ACCESS_KEY_ID;
    AWS_SECRET_ACCESS_KEY=uyug...; export AWS_SECRET_ACCESS_KEY;
    AWS_SESSION_TOKEN=FQoDY...; export AWS_SESSION_TOKEN;

The prompt and expiration notice are written to stderr, and the environment variables are written to stdout, so
you can also `eval` the output:

    $ eval $(awsmfa --env)
    Enter MFA Code: 123456
    Temporary credentials will expire in 5:59:59.945582.
    $ echo ${AWS_ACCESS_KEY_ID}
    ASIA...

Note that ``AWS_SESSION_TOKEN`` is not as widely supported as the other variables, so YMMV.
