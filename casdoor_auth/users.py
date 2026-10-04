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
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction

from casdoor_auth.models import CasdoorUser


def _can_link(user):
    """
    Whether an existing Django user that is not linked to any Casdoor user yet may be
    taken over by the Casdoor user with the same name.

    Users created by django-casdoor-auth < 2.0 got the (always empty) password of the JWT
    or no password at all, so they are linked automatically. Users with a real password
    (e.g. a local superuser named "admin") are only linked when CASDOOR_LINK_EXISTING_USERS
    is enabled, otherwise anyone signing up in Casdoor with that name would get the account.
    """
    if getattr(settings, "CASDOOR_LINK_EXISTING_USERS", False):
        return True
    return not user.has_usable_password() or user.check_password("")


def _sync_fields(user, claims):
    changed = False
    values = {
        "email": claims.get("email") or "",
        "first_name": claims.get("firstName") or "",
        "last_name": claims.get("lastName") or "",
    }
    for field, value in values.items():
        if value and hasattr(user, field) and getattr(user, field) != value:
            setattr(user, field, value)
            changed = True
    if changed:
        user.save()


@transaction.atomic
def get_or_create_user(claims):
    """Return the Django user for the claims of a verified Casdoor access token."""
    casdoor_id = claims.get("id") or claims.get("sub")
    name = claims.get("name")
    organization = claims.get("owner")
    if not casdoor_id or not name:
        raise PermissionDenied("The Casdoor token has no user ID or name")

    link = CasdoorUser.objects.select_related("user").filter(casdoor_id=casdoor_id).first()
    if link is not None:
        user = link.user
    else:
        User = get_user_model()
        user = User.objects.filter(**{User.USERNAME_FIELD: name}).first()
        if user is None:
            if not getattr(settings, "CASDOOR_CREATE_USERS", True):
                raise PermissionDenied(f'There is no account for the Casdoor user "{name}"')
            user = User(**{User.USERNAME_FIELD: name})
            user.set_unusable_password()
            user.save()
        elif CasdoorUser.objects.filter(user=user).exists() or not _can_link(user):
            raise PermissionDenied(f'The account "{name}" belongs to someone else')
        link = CasdoorUser.objects.create(user=user, casdoor_id=casdoor_id, organization=organization, name=name)

    if link.name != name:
        link.name = name
        link.save(update_fields=["name"])
    _sync_fields(user, claims)
    return user
