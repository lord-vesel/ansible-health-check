#!/usr/bin/env python
# Copyright TrueAccord 2014
#
# Author: Nadav S. Samet <nadavsr@trueaccord.com>

DOCUMENTATION = '''
---
module: health_check
short_description: Checks that an HTTP server is responding as expected.
description:
    - Sends multiple HTTP requests to a URL until the expected response is
      received. The number of retries, the delay between retries as well as
      the expected response are configurable.

    - Install this module by putting the file C(health_check) in a directory
      named C(library) under your playbook or role directory.

notes:
    - Requires urllib2

options:
    url:
        description:
            - URLs to perform health checks on.
        required: true
    headers:
        description:
            - Dictionary of HTTP headers to send in the request.
        default: null
    initial_delay:
        description:
            - Number of seconds to wait before sending the first request.
        default: '0'
    delay_between_tries:
        description:
            - Number of seconds to wait between tries.
        default: 5
    max_retries:
        description:
            - Number of times to try before giving up.
        default: 10
    timeout:
        description:
            - Number of seconds to wait for a response for each request. If
              a response is not received within this number of second, the
              attempt is considered to be a failure.
        default: 10
    expected_status:
        description:
           - Expected HTTP status code. If the server responds with a
             different status code, then the attempt is considered to be
             a failure.
        default: 200
    expected_regexp:
        description:
           - An optional regular expression that can be used to validate the
             response from the server. If the response body does not match the
             regular expression the attempt is considered as failed. Note that
             the regular expression tries to match from the beginning of the
             response. If you want to search anywhere within the response body
             use an expression like ".*OK"
        required: false
        default: null
'''

EXAMPLES = '''
# Performs a health check for a remote server from the machine running the
# play.

- name: Wait for server to pass health-checks
  health_check:
  url: http://{{ inventory_name }}
  delegate_to: 127.0.0.1

# Runs a health check for an HTTP server running on the current host.
# passes an Host header to reach the virtual host we want to test.

- name: Wait for API to pass health-check
  health_check:
    url: http://127.0.0.1/api/v1/ok
    delay_between_tries: 5
    max_retries: 20
    headers:
      Host: api.example.com
    expected_regexp: 'ok'
'''

from ansible.module_utils.basic import *
#import httplib2
import re
import socket
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


def check_server_status(url, headers, timeout, expected_status,
                        expected_regexp):
    request = Request(url, headers=headers)
    try:
        fp = urlopen(request, timeout=timeout)
    except (URLError, HTTPError, socket.error) as e:
        return False, str(e)

    if fp.getcode() != expected_status:
        return False, 'Expected status %d, actual: %d' % (
            expected_status, fp.getcode())

    content = fp.read()
    fp.close()

    if expected_regexp and not re.match(expected_regexp, content):
        return False, 'Content did not match expected regexp.'

    return True, 'OK'


def main():
    module = AnsibleModule(
        argument_spec = dict(
            url = dict(required=True),
            headers = dict(required=False, type='dict', default=None),
            initial_delay = dict(required=False, type='int', default=0),
            delay_between_tries = dict(required=False, type='int', default=5),
            max_retries = dict(required=False, type='int', default=10),
            timeout = dict(request=False, type='int', default=10),
            expected_status = dict(request=False, type='int', default=200),
            expected_regexp = dict(request=False, default=None)
        )
    )

    url = module.params['url']
    headers = module.params['headers'] or {}
    initial_delay = module.params['initial_delay']
    delay_between_tries = module.params['delay_between_tries']
    max_retries = module.params['max_retries']
    timeout = module.params['timeout']
    expected_status = module.params['expected_status']
    expected_regexp = module.params['expected_regexp']

    time.sleep(initial_delay)
    info = ''
    for attempt in range(max_retries):
        if attempt != 0:
            time.sleep(delay_between_tries)
        success, info = check_server_status(
                url=url, headers=headers, timeout=timeout,
                expected_status=expected_status,
                expected_regexp=expected_regexp)
        if success:
            module.exit_json(failed_attempts=attempt)
    else:
        module.fail_json(msg='Maximum attempts reached: ' + info,
                         failed_attempts=attempt)

if __name__ == '__main__':
    main()
