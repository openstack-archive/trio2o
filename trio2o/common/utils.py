# Copyright 2015 Huawei Technologies Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six

import pecan
import re
import urlparse

from oslo_log import log as logging

from trio2o.common import constants as cons
import trio2o.common.exceptions as t_exceptions
from trio2o.common.i18n import _
import trio2o.db.api as db_api

LOG = logging.getLogger(__name__)


def get_import_path(cls):
    return cls.__module__ + "." + cls.__name__


def get_ag_name(pod_name):
    return 'ag_%s' % pod_name


def get_az_name(pod_name):
    return 'az_%s' % pod_name


def get_node_name(pod_name):
    return "cascade_%s" % pod_name


def validate_required_fields_set(body, fields):
    for field in fields:
        if field not in body:
            return False
    return True


TRUE_STRINGS = ('1', 't', 'true', 'on', 'y', 'yes')
FALSE_STRINGS = ('0', 'f', 'false', 'off', 'n', 'no')


def is_valid_boolstr(val):
    """Check if the provided string is a valid bool string or not."""
    val = str(val).lower()
    return (val in TRUE_STRINGS) or (val in FALSE_STRINGS)


def bool_from_string(subject, strict=False, default=False):
    """Interpret a string as a boolean.

    A case-insensitive match is performed such that strings matching 't',
    'true', 'on', 'y', 'yes', or '1' are considered True and, when
    `strict=False`, anything else returns the value specified by 'default'.
    Useful for JSON-decoded stuff and config file parsing.
    If `strict=True`, unrecognized values, including None, will raise a
    ValueError which is useful when parsing values passed in from an API call.
    Strings yielding False are 'f', 'false', 'off', 'n', 'no', or '0'.
    """

    if not isinstance(subject, six.string_types):
        subject = six.text_type(subject)

    lowered = subject.strip().lower()

    if lowered in TRUE_STRINGS:
        return True
    elif lowered in FALSE_STRINGS:
        return False
    elif strict:
        acceptable = ', '.join(
            "'%s'" % s for s in sorted(TRUE_STRINGS + FALSE_STRINGS))
        msg = _("Unrecognized value '%(val)s', acceptable values are:"
                " %(acceptable)s") % {'val': subject,
                                      'acceptable': acceptable}
        raise ValueError(msg)
    else:
        return default


def check_string_length(value, name=None, min_len=0, max_len=None):
    """Check the length of specified string

    :param value: the value of the string
    :param name: the name of the string
    :param min_len: the minimum length of the string
    :param max_len: the maximum length of the string

    """
    if not isinstance(value, six.string_types):
        if name is None:
            msg = _("The input is not a string or unicode")
        else:
            msg = _("%s is not a string or unicode") % name
        raise t_exceptions.InvalidInput(message=msg)

    if name is None:
        name = value

    if len(value) < min_len:
        msg = _("%(name)s has a minimum character requirement of "
                "%(min_length)s.") % {'name': name, 'min_length': min_len}
        raise t_exceptions.InvalidInput(message=msg)

    if max_len and len(value) > max_len:
        msg = _("%(name)s has more than %(max_length)s "
                "characters.") % {'name': name, 'max_length': max_len}
        raise t_exceptions.InvalidInput(message=msg)


def get_bottom_network_name(network):
    return '%s#%s' % (network['id'], network['name'])


def format_error(code, message, error_type=None):
    error_type_map = {400: 'badRequest',
                      403: 'forbidden',
                      404: 'itemNotFound',
                      409: 'conflictingRequest',
                      500: 'internalServerError'}
    pecan.response.status = code
    if not error_type:
        if code in error_type_map:
            error_type = error_type_map[code]
        else:
            error_type = 'Error'
    # format error message in this form so nova client can
    # correctly parse it
    return {error_type: {'message': message, 'code': code}}


def format_nova_error(code, message, error_type=None):
    return format_error(code, message, error_type)


def format_cinder_error(code, message, error_type=None):
    return format_error(code, message, error_type)


def get_pod_by_top_id(context, _id):
    """Get pod resource from pod table .

    :param _id: the top id of resource
    :returns: pod resource
    """
    mappings = db_api.get_bottom_mappings_by_top_id(
        context, _id,
        cons.RT_VOLUME)

    if not mappings or len(mappings) != 1:
        return None

    return mappings[0][0]


def url_join(*parts):
    """Convenience method for joining parts of a URL

    Any leading and trailing '/' characters are removed, and the parts joined
    together with '/' as a separator. If last element of 'parts' is an empty
    string, the returned URL will have a trailing slash.
    """
    parts = parts or ['']
    clean_parts = [part.strip('/') for part in parts if part]
    if not parts[-1]:
        # Empty last element should add a trailing slash
        clean_parts.append('')
    return '/'.join(clean_parts)


def remove_trailing_version_from_href(href):
    """Removes the api version from the href.

    Given: 'http://www.nova.com/compute/v1.1'
    Returns: 'http://www.nova.com/compute'

    Given: 'http://www.nova.com/v1.1'
    Returns: 'http://www.nova.com'

    """
    parsed_url = urlparse.urlsplit(href)
    url_parts = parsed_url.path.rsplit('/', 1)

    # NOTE: this should match vX.X or vX
    expression = re.compile(r'^v([0-9]+|[0-9]+\.[0-9]+)(/.*|$)')
    if not expression.match(url_parts.pop()):
        raise ValueError('URL %s does not contain version' % href)

    new_path = url_join(*url_parts)
    parsed_url = list(parsed_url)
    parsed_url[2] = new_path
    return urlparse.urlunsplit(parsed_url)
