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

from django.conf import settings
from django.db import models


class CasdoorUser(models.Model):
    """Links a Django user to the Casdoor user (by its immutable ID) that signs in as it."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="casdoor")
    casdoor_id = models.CharField(max_length=100, unique=True)
    organization = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Casdoor user"

    def __str__(self):
        return f"{self.organization}/{self.name}"
