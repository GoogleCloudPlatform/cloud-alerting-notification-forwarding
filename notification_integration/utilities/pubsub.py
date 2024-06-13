# Copyright 2021 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module to extract notification data for a generic Pubsub message."""

import base64
import binascii
import json
from typing import Any, Dict, Text


class Error(Exception):
  """Base class for all errors raised in this module."""


class DataParseError(Error):
  """Raised when the encoded 'data' field of a Pub/Sub message cannot be parsed."""


def ExtractNotificationFromPubSubMsg(
    pubsub_msg: Dict[Text, Any],
) -> Dict[Text, Any]:
  """Parses notification messages from Pub/Sub.

  Args:
      pubsub_msg: Dictionary containing the Pub/Sub message. The message itself
        should be a base64-encoded string.

  Returns:
      The decoded 'data' value of the provided Pub/Sub message, returned as a
      json dictory.

  Raises:
      DataParseError: If data cannot be parsed.
  """
  try:
    data_base64_string = pubsub_msg['message']['data']
  except (KeyError, TypeError) as e:
    raise DataParseError('invalid Pub/Sub message format') from e

  try:
    data_bytes = base64.b64decode(data_base64_string)
  except (binascii.Error, ValueError) as e:
    raise DataParseError('data should be base64-encoded') from e
  except TypeError as e:
    raise DataParseError('data should be in a string format') from e

  data_string = data_bytes.decode('utf-8')
  data_string = data_string.strip()

  try:
    data_json = json.loads(data_string)
  except json.JSONDecodeError as e:
    raise DataParseError(
        'data can not be loaded as a json object: {}'.format(e), 400
    )

  return data_json
