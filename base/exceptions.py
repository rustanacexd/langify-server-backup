from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList

from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _


def _get_error_details(data, default_code=None):
    """
    Descend into a nested data structure, forcing any
    lazy translation strings or strings into `ErrorDetail`.

    Keeps None, True, False and integers.
    """
    # A copy from DRF 3.9 except for the change below
    if isinstance(data, list):
        ret = [_get_error_details(item, default_code) for item in data]
        if isinstance(data, ReturnList):
            return ReturnList(ret, serializer=data.serializer)
        return ret
    elif isinstance(data, dict):
        ret = {
            key: _get_error_details(value, default_code)
            for key, value in data.items()
        }
        if isinstance(data, ReturnDict):
            return ReturnDict(ret, serializer=data.serializer)
        return ret

    # Only change:
    if data is None or data is True or data is False or isinstance(data, int):
        return data
    return force_text(data)


class JsonValidationError(APIException):
    # A copy of ValidationError from DRF 3.9
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Invalid input.')
    default_code = 'invalid'

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        # For validation failures, we may collect many errors together,
        # so the details should always be coerced to a list if not already.
        if not isinstance(detail, dict) and not isinstance(detail, list):
            detail = [detail]

        self.detail = _get_error_details(detail, code)

    # Changed methods

    def get_codes(self):
        return self.default_code

    def get_full_details(self):
        raise NotImplementedError
