#!/usr/bin/python3
"""
awsmfa.py simplifies the use of IAM Roles and MFA tokens by managing your 'default' AWS credentials.

Using awsmfa, the long-lived developer credentials that often linger in insecure places can be
restricted to harmless operations. Defining the privileged IAM policies to require the
aws:MultiFactorAuthPresent Condition allows you to restrict privileged operations to developers
who have recently authenticated with their multi-factor authentication token.

awsmfa.py facilitates this by managing the 'default' section in the ~/.aws/credentials
file for you. It sends your MFA code to STS using your "identity" profile, and then stores the
response as your "default" profile so that it is available to the myriad of tools that know how
to read ~/.aws/credentials.

awsmfa is intended to be used by organizations that use MFA with STS AssumeRole and IAM
policies with the aws:MultiFactorAuthPresent condition variable. The following are common
scenarios where this tool is useful:

1. Developer has a limited set of IAM policies attached to their account, and uses role
assumption to interact with AWS resources, and IAM policies for STS AssumeRole requires MFA.

2. Developer is allowed to manage AWS resources, but IAM policies require MFA.

Requirements
============
- You must have an "identity" profile in your ~/.aws/credentials file. This need not be named
  "identity", but it must be named something other than "default" and it must contain your
  long-lived AWS access key and secret key. The easiest way to get this created is to run "aws
  configure --profile identity". You can specify a different profile name with the
  --identity-profile flag.
- Your identity profile must be allowed to iam:GetUser, iam:ListMFADevices,
  and sts:GetSessionToken. For a complete example, see the awsmfa-policies.json CloudFormation
  template.
- If your organization is using role assumption, your identity must also be allowed
  to sts:AssumeRole for each of the roles you wish to assume.
"""

import argparse
import configparser
import datetime
import getpass
import os
import sys

import botocore
import botocore.session

from ._version import VERSION

SIX_HOURS_IN_SECONDS = 21600


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog='awsmfa',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version',
                        default=False,
                        action='store_true',
                        help='Display version number and exit.')
    parser.add_argument('role_to_assume',
                        nargs='?',
                        metavar='role-to-assume',
                        help='Full ARN of the role you wish to assume. If not provided, '
                             'the temporary credentials will inherit the user\'s policies. '
                             'The temporary credentials will also satisfy the '
                             'aws:MultiFactorAuthPresent condition variable.')
    parser.add_argument('--aws-credentials',
                        default=os.path.join(os.path.expanduser('~'), '.aws/credentials'),
                        help='Full path to the ~/.aws/credentials file.')
    parser.add_argument('--duration',
                        type=int,
                        default=SIX_HOURS_IN_SECONDS,
                        help='The number of seconds that you wish the temporary credentials to be '
                             'valid for.')
    parser.add_argument('--identity-profile',
                        default=os.environ.get('AWS_MFA_IDENTITY_PROFILE', 'identity'),
                        help='Name of the section in the credentials file representing your '
                             'long-lived credentials. Values in this section will be copied '
                             'to the --target-profile, with the access key, secret key, '
                             'and session key replaced by the temporary credentials. If the '
                             'AWS_MFA_IDENTITY_PROFILE environment variable is set, it will be '
                             'used.')
    parser.add_argument('--serial-number',
                        default=os.environ.get('AWS_MFA_SERIAL_NUMBER', None),
                        help='Full ARN of the MFA device. If not provided, this will be read from '
                             'the AWS_MFA_SERIAL_NUMBER environment variable or queried from IAM '
                             'automatically. For automatic detection to work, your identity '
                             'profile must be permitted to call "aws iam get-user".')
    parser.add_argument('--target-profile',
                        default='default',
                        help='Name of the section in the credentials file to overwrite with '
                             'temporary credentials. This defaults to "default" because most '
                             'tools read that profile. The existing values in this profile will '
                             'be overwritten.')
    parser.add_argument('--token-code',
                        help='The 6 digit numeric MFA code generated by your device.')
    args = parser.parse_args(args)

    if args.version:
        print(VERSION)
        return

    credentials = configparser.ConfigParser(default_section=None)
    credentials.read(args.aws_credentials)

    session = botocore.session.Session(profile=args.identity_profile)
    iam = session.create_client('iam')

    username = iam.get_user()['User']['UserName']
    if not args.serial_number:
        devices = iam.list_mfa_devices(UserName=username)
        if not len(devices["MFADevices"]):
            raise Exception("No MFA devices are attached with this IAM user.")
        args.serial_number = devices["MFADevices"][0]["SerialNumber"]

    if args.token_code is None:
        while args.token_code is None or len(args.token_code) != 6:
            args.token_code = getpass.getpass("MFA Token Code: ")

    sts = session.create_client('sts')
    if args.role_to_assume:
        role_session_name = 'awsmfa_%s' % datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
        response = sts.assume_role(RoleArn=args.role_to_assume, RoleSessionName=role_session_name,
                                   DurationSeconds=args.duration, SerialNumber=args.serial_number,
                                   TokenCode=args.token_code)
    else:
        response = sts.get_session_token(DurationSeconds=args.duration,
                                         SerialNumber=args.serial_number,
                                         TokenCode=args.token_code)
    remaining = response['Credentials']['Expiration'] - datetime.datetime.now(
        tz=datetime.timezone.utc)
    print("Temporary credentials will expire in %s." % remaining)
    update_credentials_file(args, credentials, response['Credentials'])


def update_credentials_file(args, credentials, temporary_credentials):
    credentials.remove_section(args.target_profile)
    credentials.add_section(args.target_profile)
    for k, v in credentials.items(args.identity_profile):
        credentials.set(args.target_profile, k, v)
    credentials.set(args.target_profile, 'aws_access_key_id', temporary_credentials['AccessKeyId'])
    credentials.set(args.target_profile, 'aws_secret_access_key',
                    temporary_credentials['SecretAccessKey'])
    credentials.set(args.target_profile, 'aws_session_token', temporary_credentials['SessionToken'])
    credentials.set(args.target_profile, 'awsmfa_expiration',
                    temporary_credentials['Expiration'].isoformat())
    temp_credentials_file = args.aws_credentials + ".tmp"
    with open(temp_credentials_file, "w") as out:
        credentials.write(out)
    os.rename(temp_credentials_file, args.aws_credentials)


if __name__ == '__main__':
    main()
