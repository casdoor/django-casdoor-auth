# Copyright 2022 The Casdoor Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from casdoor_auth.views import sdk


def get_users(self):
    return sdk.get_users()


def get_user(request):
    return sdk.get_user(request.GET.get('name'))


def add_user(request):
    user = request.GET.get("name")
    return sdk.add_user(user)


def update_user(request):
    return sdk.add_user(request.GET.get('user'))


def delete_user(request):
    return sdk.delete_user(request.GET.get('name'))
