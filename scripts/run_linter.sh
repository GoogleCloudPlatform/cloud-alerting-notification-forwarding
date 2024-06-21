# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#!/bin/bash
# Descriptions of the pylint message IDs: http://pylint.pycqa.org/en/latest/technical_reference/features.html

export FLASK_APP_ENV=test
directories="notification_integration/ "
disable="C0116,E1101,R0903,C0115,C0103,C0301,C0114,W0621,W0511,E0611,R0801,R0914,R0915"

pylint3 $directories --disable=$disable
