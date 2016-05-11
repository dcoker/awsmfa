# coding=utf-8
from __future__ import print_function

import argparse
import datetime
import getpass
import sys

# noinspection PyUnresolvedReferences
from six.moves import configparser

import boto3.session
import botocore
import botocore.exceptions
import botocore.session
import os
import pytz
from six import PY2
from six.moves import shlex_quote
from ._version import VERSION

SIX_HOURS_IN_SECONDS = 21600
OK = 0
USER_RECOVERABLE_ERROR = 1


def main(args=None):
    args = parse_args(args)

    if not os.path.exists(args.aws_credentials):
        print("%s does not exist. Please run 'aws configure' or specify an "
              "alternate credentials file with --aws-credentials."
              % args.aws_credentials, file=sys.stderr)
        return USER_RECOVERABLE_ERROR

    if PY2:
        credentials = configparser.ConfigParser()
    else:
        credentials = configparser.ConfigParser(default_section=None)
    credentials.read(args.aws_credentials)

    status = one_mfa(args, credentials)
    if status != OK:
        return status
    if args.rotate_identity_keys:
        status = rotate(args, credentials)
        if status != OK:
            return status
    if args.env:
        print_env_vars(credentials, args.target_profile)
    return OK


def print_env_vars(credentials, target_profile):
    aws_access_key_id = shlex_quote(credentials.get(
        target_profile, 'aws_access_key_id'))
    aws_secret_access_key = shlex_quote(credentials.get(
        target_profile, 'aws_secret_access_key'))
    aws_session_token = shlex_quote(credentials.get(
        target_profile, 'aws_session_token'))
    print("AWS_ACCESS_KEY_ID=%s; export AWS_ACCESS_KEY_ID;" %
          shlex_quote(aws_access_key_id))
    print("AWS_SECRET_ACCESS_KEY=%s; export AWS_SECRET_ACCESS_KEY;" %
          shlex_quote(aws_secret_access_key))
    print("AWS_SESSION_TOKEN=%s; export AWS_SESSION_TOKEN;" %
          shlex_quote(aws_session_token))


def one_mfa(args, credentials):
    session, session3 = make_session(args.identity_profile)

    if "AWSMFA_TESTING_MODE" in os.environ:
        use_testing_credentials(args, credentials)
        return OK

    mfa_args = {}
    if args.token_code != 'skip':
        serial_number, token_code, err = acquire_code(args, session, session3)
        if err is not OK:
            return err
        mfa_args['SerialNumber'] = serial_number
        mfa_args['TokenCode'] = token_code

    sts = session3.client('sts')
    try:
        if args.role_to_assume:
            mfa_args.update(
                DurationSeconds=min(args.duration, 3600),
                RoleArn=args.role_to_assume,
                RoleSessionName=args.role_session_name)
            response = sts.assume_role(**mfa_args)
        else:
            mfa_args.update(DurationSeconds=args.duration)
            response = sts.get_session_token(**mfa_args)
    except botocore.exceptions.ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            print(str(err), file=sys.stderr)
            return USER_RECOVERABLE_ERROR
        else:
            raise
    print_expiration_time(response['Credentials']['Expiration'])
    update_credentials_file(args.aws_credentials,
                            args.target_profile,
                            args.identity_profile,
                            credentials,
                            response['Credentials'])
    return OK


def use_testing_credentials(args, credentials):
    print("Skipping AWS API calls because AWSMFA_TESTING_MODE is set.",
          file=sys.stderr)
    # AWS returns offset-aware UTC times, so we fake that in order to
    # verify consistent code paths between py2 and py3 datetime.
    fake_expiration = (datetime.datetime.now(tz=pytz.utc) +
                       datetime.timedelta(minutes=5))
    fake_credentials = {
        'AccessKeyId': credentials.get(args.identity_profile,
                                       'aws_access_key_id'),
        'SecretAccessKey': credentials.get(args.identity_profile,
                                           'aws_secret_access_key'),
        'SessionToken': "420",
        'Expiration': fake_expiration,
    }
    print_expiration_time(fake_expiration)
    update_credentials_file(args.aws_credentials,
                            args.target_profile,
                            args.identity_profile,
                            credentials,
                            fake_credentials)


def make_session(identity_profile):
    session = botocore.session.Session(profile=identity_profile)
    try:
        session3 = boto3.session.Session(botocore_session=session)
    except botocore.exceptions.ProfileNotFound as err:
        print(str(err), file=sys.stderr)
        print("Available profiles: %s" %
              ", ".join(sorted(session.available_profiles)), file=sys.stderr)
        return USER_RECOVERABLE_ERROR
    return session, session3


def acquire_code(args, session, session3):
    """returns the user's token serial number, MFA token code, and an
    error code."""
    serial_number = find_mfa_for_user(args.serial_number, session, session3)
    if not serial_number:
        print("There are no MFA devices associated with this user.",
              file=sys.stderr)
        return None, None, USER_RECOVERABLE_ERROR

    token_code = args.token_code
    if token_code is None:
        while token_code is None or len(token_code) != 6:
            token_code = getpass.getpass("MFA Token Code: ")
    return serial_number, token_code, OK


def print_expiration_time(aws_expiration):
    remaining = aws_expiration - datetime.datetime.now(
        tz=pytz.utc)
    print("Temporary credentials will expire in %s." % remaining,
          file=sys.stderr)


def rotate(args, credentials):
    """rotate the identity profile's AWS access key pair."""
    current_access_key_id = credentials.get(
        args.identity_profile, 'aws_access_key_id')

    # create new sessions using the MFA credentials
    session, session3 = make_session(args.target_profile)
    iam = session3.resource('iam')

    # find the AccessKey corresponding to the identity profile and delete it.
    current_access_key = next((key for key
                               in iam.CurrentUser().access_keys.all()
                               if key.access_key_id == current_access_key_id),
                              None)
    current_access_key.delete()

    # create the new access key pair
    iam_service = session3.client('iam')
    new_access_key_pair = iam_service.create_access_key()["AccessKey"]

    print("Rotating from %s to %s." % (current_access_key.access_key_id,
                                       new_access_key_pair['AccessKeyId']),
          file=sys.stderr)
    update_credentials_file(args.aws_credentials,
                            args.identity_profile,
                            args.identity_profile,
                            credentials,
                            new_access_key_pair)
    print("%s profile updated." % args.identity_profile, file=sys.stderr)

    return OK


def parse_args(args):
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog='awsmfa',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version',
                        action='version',
                        version=VERSION,
                        help='Display version number and exit.')
    parser.add_argument('role_to_assume',
                        nargs='?',
                        metavar='role-to-assume',
                        default=os.environ.get('AWS_MFA_ROLE_TO_ASSUME'),
                        help='Full ARN of the role you wish to assume. If not '
                             'provided, the temporary credentials will '
                             'inherit the user\'s policies. The temporary '
                             'credentials will also satisfy the '
                             'aws:MultiFactorAuthPresent condition variable. '
                             'If the AWS_MFA_ROLE_TO_ASSUME environment '
                             'variable is set, it will be used as the default '
                             'value.')
    parser.add_argument('--aws-credentials',
                        default=os.path.join(os.path.expanduser('~'),
                                             '.aws/credentials'),
                        help='Full path to the ~/.aws/credentials file.')
    parser.add_argument('-d', '--duration',
                        type=int,
                        default=int(os.environ.get('AWS_MFA_DURATION',
                                                   SIX_HOURS_IN_SECONDS)),
                        help='The number of seconds that you wish the '
                             'temporary credentials to be valid for. For role '
                             'assumption, this will be limited to an hour. If '
                             'the AWS_MFA_DURATION environment variable is '
                             'set, it will be used as the default value.')
    parser.add_argument('-i', '--identity-profile',
                        default=os.environ.get('AWS_MFA_IDENTITY_PROFILE',
                                               'identity'),
                        help='Name of the section in the credentials file '
                             'representing your long-lived credentials. '
                             'All values in this section '
                             '(including custom parameters such as "region" '
                             'or "s3") will be copied to the '
                             '--target-profile, with the access key, secret '
                             'key, and session key replaced by the temporary '
                             'credentials. If the AWS_MFA_IDENTITY_PROFILE '
                             'environment variable is set, it will be used as '
                             'the default value.')
    parser.add_argument('--serial-number',
                        default=os.environ.get('AWS_MFA_SERIAL_NUMBER', None),
                        help='Full ARN of the MFA device. If not provided, '
                             'this will be read from the '
                             'AWS_MFA_SERIAL_NUMBER environment variable or '
                             'queried from IAM automatically. For automatic '
                             'detection to work, your identity profile must '
                             'have IAM policies that allow "aws iam '
                             'get-user" and "aws iam list-mfa-devices".')
    parser.add_argument('-t', '--target-profile',
                        default=os.environ.get('AWS_MFA_TARGET_PROFILE',
                                               'default'),
                        help='Name of the section in the credentials file to '
                             'overwrite with temporary credentials. This '
                             'defaults to "default" because most tools read '
                             'that profile. The existing values in this '
                             'profile will be overwritten. If the '
                             'AWS_MFA_TARGET_PROFILE environment variable is '
                             'set, it will be used as the default value.')
    parser.add_argument('--role-session-name',
                        default='awsmfa_%s' % datetime.datetime.now().strftime(
                            '%Y%m%dT%H%M%S'),
                        help='The name of the temporary session. Applies only '
                             'when assuming a role.')
    parser.add_argument('-c', '--token-code',
                        default=os.environ.get('AWS_MFA_TOKEN_CODE'),
                        help='The 6 digit numeric MFA code generated by your '
                             'device, or "skip". If the AWS_MFA_TOKEN_CODE '
                             'environment variable is set, it will be used as '
                             'the default value. If this is \"skip\", '
                             'temporary credentials will still be acquired '
                             'but they will not satisfy the '
                             'sts:MultiFactorAuthPresent condition.')
    parser.add_argument('--rotate-identity-keys',
                        default=safe_bool(os.environ.get(
                            'AWS_MFA_ROTATE_IDENTITY_KEYS', False)),
                        action='store_true',
                        help='Rotate the identity profile access keys '
                             'immediately upon successful acquisition of '
                             'temporary credentials. This deletes your '
                             'identity profile access keys from the '
                             '--aws-credentials file and from AWS using the '
                             'IAM DeleteAccessKey API, and then writes a new '
                             'identity access key pair using the results of '
                             'IAM CreateAccessKey. If the '
                             'AWS_MFA_ROTATE_IDENTITY_KEYS environment '
                             'variable is set to True, this behavior is '
                             'enabled by default.')
    parser.add_argument('--env',
                        default=safe_bool(os.environ.get(
                            'AWS_MFA_ENV', False)),
                        action='store_true',
                        help='Print the AWS_ACCESS_KEY_ID, '
                             'AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN '
                             'environment variables in a form suitable for '
                             'evaluation in a shell.')
    args = parser.parse_args(args)
    return args


def safe_bool(s):
    return str(s).lower() == "true"


def find_mfa_for_user(user_specified_serial, botocore_session, boto3_session):
    if user_specified_serial:
        return user_specified_serial

    iam = boto3_session.client('iam')
    user = iam.get_user()
    if user['User']['Arn'].endswith(':root'):
        # The root user MFA device is not in the same way as non-root
        # users, so we must find the root MFA devices using a different
        # method than we do for normal users.
        devices = boto3_session.resource('iam').CurrentUser().mfa_devices.all()
        serials = (x.serial_number for x in devices)
    else:
        # Non-root users can have a restrictive policy that allows them
        # only to list devices associated with their user but it requires
        # using the low level IAM client to compose the proper request.
        username = user['User']['UserName']
        devices = botocore_session.create_client('iam').list_mfa_devices(
            UserName=username)
        serials = (x['SerialNumber'] for x in devices['MFADevices'])

    serials = list(serials)
    if not serials:
        return None
    if len(serials) > 1:
        print("Warning: user has %d MFA devices. Using the first." %
              len(devices), file=sys.stderr)
    return serials[0]


def update_credentials_file(filename, target_profile, source_profile,
                            credentials, new_access_key):
    if target_profile != source_profile:
        credentials.remove_section(target_profile)
        # Hack: Python 2's implementation of ConfigParser rejects new sections
        # named 'default'.
        if PY2 and target_profile == 'default':
            # noinspection PyProtectedMember
            credentials._sections[
                target_profile] = configparser._default_dict()
        else:
            credentials.add_section(target_profile)

        for k, v in credentials.items(source_profile):
            credentials.set(target_profile, k, v)

    credentials.set(target_profile, 'aws_access_key_id',
                    new_access_key['AccessKeyId'])
    credentials.set(target_profile, 'aws_secret_access_key',
                    new_access_key['SecretAccessKey'])
    if 'SessionToken' in new_access_key:
        credentials.set(target_profile, 'aws_session_token',
                        new_access_key['SessionToken'])
        credentials.set(target_profile, 'awsmfa_expiration',
                        new_access_key['Expiration'].isoformat())
    else:
        credentials.remove_option(target_profile, 'aws_session_token')
        credentials.remove_option(target_profile, 'awsmfa_expiration')

    temp_credentials_file = filename + ".tmp"
    with open(temp_credentials_file, "w") as out:
        credentials.write(out)
    os.rename(temp_credentials_file, filename)


if __name__ == '__main__':
    status = main()
    sys.exit(status)
