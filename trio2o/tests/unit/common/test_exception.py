
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

import six
import unittest

from trio2o.common import exceptions


class Trio2oExceptionTestCase(unittest.TestCase):
    def test_default_error_msg(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            message = "default message"

        exc = FakeTrio2oException()
        self.assertEqual('default message', six.text_type(exc))

    def test_error_msg(self):
        self.assertEqual('test',
                         six.text_type(exceptions.Trio2oException('test')))

    def test_default_error_msg_with_kwargs(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            message = "default message: %(code)s"

        exc = FakeTrio2oException(code=500)
        self.assertEqual('default message: 500', six.text_type(exc))

    def test_error_msg_exception_with_kwargs(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            message = "default message: %(misspelled_code)s"

        exc = FakeTrio2oException(code=500)
        self.assertEqual('default message: %(misspelled_code)s',
                         six.text_type(exc))

    def test_default_error_code(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            code = 404

        exc = FakeTrio2oException()
        self.assertEqual(404, exc.kwargs['code'])

    def test_error_code_from_kwarg(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            code = 500

        exc = FakeTrio2oException(code=404)
        self.assertEqual(404, exc.kwargs['code'])

    def test_error_msg_is_exception_to_string(self):
        msg = 'test message'
        exc1 = Exception(msg)
        exc2 = exceptions.Trio2oException(exc1)
        self.assertEqual(msg, exc2.msg)

    def test_exception_kwargs_to_string(self):
        msg = 'test message'
        exc1 = Exception(msg)
        exc2 = exceptions.Trio2oException(kwarg1=exc1)
        self.assertEqual(msg, exc2.kwargs['kwarg1'])

    def test_message_in_format_string(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            message = 'FakeCinderException: %(message)s'

        exc = FakeTrio2oException(message='message')
        self.assertEqual('FakeCinderException: message', six.text_type(exc))

    def test_message_and_kwarg_in_format_string(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            message = 'Error %(code)d: %(message)s'

        exc = FakeTrio2oException(message='message', code=404)
        self.assertEqual('Error 404: message', six.text_type(exc))

    def test_message_is_exception_in_format_string(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            message = 'Exception: %(message)s'

        msg = 'test message'
        exc1 = Exception(msg)
        exc2 = FakeTrio2oException(message=exc1)
        self.assertEqual('Exception: test message', six.text_type(exc2))

    def test_no_message_input_exception_in_format_string(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            message = 'Error: %(message)s'

        exc = FakeTrio2oException()
        out_message = six.text_type(exc)
        self.assertEqual('Error: None', out_message)

    def test_no_kwarg_input_exception_in_format_string(self):
        class FakeTrio2oException(exceptions.Trio2oException):
            message = 'No Kwarg Error: %(why)s, %(reason)s'

        exc = FakeTrio2oException(why='why')
        out_message = six.text_type(exc)
        self.assertEqual('No Kwarg Error: %(why)s, %(reason)s', out_message)
