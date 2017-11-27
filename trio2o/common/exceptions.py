# Copyright 2015 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Trio2o base exception handling.
"""

import six

from oslo_log import log as logging
from trio2o.common.i18n import _
from trio2o.common.i18n import _LE

LOG = logging.getLogger(__name__)


class Trio2oException(Exception):
    """Base Trio2o Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred.")
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):

        self.kwargs = kwargs
        self.kwargs['message'] = message

        if 'code' not in self.kwargs:
            self.kwargs['code'] = self.code

        for k, v in self.kwargs.items():
            if isinstance(v, Exception):
                self.kwargs[k] = six.text_type(v)

        if self._should_format():
            try:
                message = self.message % kwargs
            except Exception:

                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                exc_info = _('Exception class %s in string '
                             'format operation') % type(self).__name__
                format_str = _('%(exception_info)s ; %(format_key)s : '
                               '%(format_value)s')
                for name, value in kwargs.items():
                    exc_info = format_str % {
                        'exception_info': exc_info,
                        'format_key': name,
                        'format_value': six.text_type(value)}

                exc_info = _('%(message)s ; %(exception_info)s') % {
                    'message': self.message, 'exception_info': exc_info}
                LOG.exception(exc_info)

                # no rerasie
                # exc_info = sys.exc_info()
                # if CONF.fatal_exception_format_errors:
                #    six.reraise(*exc_info)

                # at least get the core message out if something happened
                message = self.message

        elif isinstance(message, Exception):
            message = six.text_type(message)

        self.msg = message
        super(Trio2oException, self).__init__(message)

    def _should_format(self):

        if self.kwargs['message'] is None and '%(message)' in self.message:
            LOG.error(_LE('\%(message)s in message '
                          'but init parameter is None'))

        return self.kwargs['message'] is None or '%(message)' in self.message

    def __unicode__(self):
        return six.text_type(self.msg)


class BadRequest(Trio2oException):
    message = _('Bad %(resource)s request: %(msg)s')


class NotFound(Trio2oException):
    message = _("Resource could not be found.")
    code = 404
    safe = True


class Conflict(Trio2oException):
    pass


class NotAuthorized(Trio2oException):
    message = _("Not authorized.")


class ServiceUnavailable(Trio2oException):
    message = _("The service is unavailable")


class AdminRequired(NotAuthorized):
    message = _("User does not have admin privileges")


class PolicyNotAuthorized(NotAuthorized):
    message = _("Policy doesn't allow this operation to be performed.")


class InUse(Trio2oException):
    message = _("The resource is inuse")


class InvalidConfigurationOption(Trio2oException):
    message = _("An invalid value was provided for %(opt_name)s: "
                "%(opt_value)s")


class EndpointNotAvailable(Trio2oException):
    message = "Endpoint %(url)s for %(service)s is not available"

    def __init__(self, service, url):
        super(EndpointNotAvailable, self).__init__(service=service, url=url)


class EndpointNotUnique(Trio2oException):
    message = "Endpoint for %(service)s in %(pod)s not unique"

    def __init__(self, pod, service):
        super(EndpointNotUnique, self).__init__(pod=pod, service=service)


class EndpointNotFound(Trio2oException):
    message = "Endpoint for %(service)s in %(pod)s not found"

    def __init__(self, pod, service):
        super(EndpointNotFound, self).__init__(pod=pod, service=service)


class ResourceNotFound(Trio2oException):
    message = "Could not find %(resource_type)s: %(unique_key)s"

    def __init__(self, model, unique_key):
        resource_type = model.__name__.lower()
        super(ResourceNotFound, self).__init__(resource_type=resource_type,
                                               unique_key=unique_key)


class ResourceNotSupported(Trio2oException):
    message = "%(method)s method not supported for %(resource)s"

    def __init__(self, resource, method):
        super(ResourceNotSupported, self).__init__(resource=resource,
                                                   method=method)


class Invalid(Trio2oException):
    message = _("Unacceptable parameters.")
    code = 400


class InvalidInput(Invalid):
    message = _("Invalid input received: %(reason)s")


class InvalidMetadata(Invalid):
    message = _("Invalid metadata: %(reason)s")


class InvalidMetadataSize(Invalid):
    message = _("Invalid metadata size: %(reason)s")


class MetadataLimitExceeded(Trio2oException):
    message = _("Maximum number of metadata items exceeds %(allowed)d")


class InvalidReservationExpiration(Invalid):
    message = _("Invalid reservation expiration %(expire)s.")


class InvalidQuotaValue(Invalid):
    message = _("Change would make usage less than 0 for the following "
                "resources: %(unders)s")


class QuotaNotFound(NotFound):
    message = _("Quota could not be found")


class QuotaResourceUnknown(QuotaNotFound):
    message = _("Unknown quota resources %(unknown)s.")


class ProjectQuotaNotFound(QuotaNotFound):
    message = _("Quota for project %(project_id)s could not be found.")


class QuotaClassNotFound(QuotaNotFound):
    message = _("Quota class %(class_name)s could not be found.")


class QuotaUsageNotFound(QuotaNotFound):
    message = _("Quota usage for project %(project_id)s could not be found.")


class ReservationNotFound(QuotaNotFound):
    message = _("Quota reservation %(uuid)s could not be found.")


class OverQuota(Trio2oException):
    message = _("Quota exceeded for resources: %(overs)s")


class TooManyInstances(Trio2oException):
    message = _("Quota exceeded for %(overs)s: Requested %(req)s,"
                " but already used %(used)s of %(allowed)s %(overs)s")


class OnsetFileLimitExceeded(Trio2oException):
    message = _("Personality file limit exceeded")


class OnsetFilePathLimitExceeded(OnsetFileLimitExceeded):
    message = _("Personality file path too long")


class OnsetFileContentLimitExceeded(OnsetFileLimitExceeded):
    message = _("Personality file content too long")


class ExternalNetPodNotSpecify(Trio2oException):
    message = "Pod for external network not specified"

    def __init__(self):
        super(ExternalNetPodNotSpecify, self).__init__()


class PodNotFound(NotFound):
    message = "Pod %(pod_name)s could not be found."

    def __init__(self, pod_name):
        super(PodNotFound, self).__init__(pod_name=pod_name)


class ChildQuotaNotZero(Trio2oException):
    message = _("Child projects having non-zero quota")


# parameter validation error
class ValidationError(Trio2oException):
    message = _("%(msg)s")
    code = 400


# parameter validation error
class HTTPForbiddenError(Trio2oException):
    message = _("%(msg)s")
    code = 403


class VolumeTypeNotFound(NotFound):
    message = _("Volume type %(volume_type_id)s could not be found.")


class VolumeTypeNotFoundByName(VolumeTypeNotFound):
    message = _("Volume type with name %(volume_type_name)s "
                "could not be found.")


class VolumeTypeExtraSpecsNotFound(NotFound):
    message = _("Volume Type %(volume_type_id)s has no extra specs with "
                "key %(extra_specs_key)s.")


class Duplicate(Trio2oException):
    pass


class VolumeTypeExists(Duplicate):
    message = _("Volume Type %(id)s already exists.")


class VolumeTypeUpdateFailed(Trio2oException):
    message = _("Cannot update volume_type %(id)s")


class ClassNotFound(NotFound):
    msg_fmt = _("Class %(class_name)s could not be found: %(exception)s")
