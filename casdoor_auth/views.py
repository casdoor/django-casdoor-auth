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

import logging
import secrets
from urllib.parse import urlencode

import jwt
from casdoor import CasdoorSDK
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, resolve_url
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from casdoor_auth.users import get_or_create_user

logger = logging.getLogger(__name__)

STATE_SESSION_KEY = "casdoor_state"
NEXT_SESSION_KEY = "casdoor_next"
USER_SESSION_KEY = "user"


def get_sdk():
    conf = settings.CASDOOR_CONFIG
    return CasdoorSDK(
        endpoint=conf["endpoint"],
        client_id=conf["client_id"],
        client_secret=conf["client_secret"],
        certificate=conf["certificate"],
        org_name=conf["org_name"],
        application_name=conf["application_name"],
        front_endpoint=conf.get("front_endpoint"),
    )


def get_redirect_uri(request):
    redirect_uri = getattr(settings, "REDIRECT_URI", None)
    if redirect_uri:
        return redirect_uri
    return request.build_absolute_uri(reverse("callback"))


def _safe_next(request, url):
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return resolve_url(settings.LOGIN_REDIRECT_URL)


def _authentication_backend():
    backends = settings.AUTHENTICATION_BACKENDS
    model_backend = "django.contrib.auth.backends.ModelBackend"
    return model_backend if model_backend in backends else backends[0]


@require_GET
def login(request):
    state = secrets.token_urlsafe(32)
    request.session[STATE_SESSION_KEY] = state
    request.session[NEXT_SESSION_KEY] = _safe_next(request, request.GET.get(REDIRECT_FIELD_NAME))
    conf = settings.CASDOOR_CONFIG
    params = {
        "client_id": conf["client_id"],
        "response_type": "code",
        "redirect_uri": get_redirect_uri(request),
        "scope": conf.get("scope", "read"),
        "state": state,
    }
    front_endpoint = (conf.get("front_endpoint") or conf["endpoint"]).rstrip("/")
    return redirect(f"{front_endpoint}/login/oauth/authorize?{urlencode(params)}")


# kept for projects that reference the view of django-casdoor-auth < 2.0 directly
toLogin = login


@require_GET
def callback(request):
    expected_state = request.session.pop(STATE_SESSION_KEY, None)
    next_url = request.session.pop(NEXT_SESSION_KEY, None) or resolve_url(settings.LOGIN_REDIRECT_URL)

    error = request.GET.get("error")
    if error:
        return HttpResponseBadRequest(f"Casdoor sign-in failed: {request.GET.get('error_description') or error}")

    state = request.GET.get("state", "")
    if not expected_state or not secrets.compare_digest(state, expected_state):
        return HttpResponseBadRequest("Invalid state, please sign in again")

    code = request.GET.get("code")
    if not code:
        return HttpResponseBadRequest("Missing authorization code")

    sdk = get_sdk()
    token = sdk.get_oauth_token(code=code)
    access_token = token.get("access_token") if isinstance(token, dict) else None
    if not access_token:
        description = (token.get("error_description") or token.get("error")) if isinstance(token, dict) else token
        logger.warning("Casdoor token exchange failed: %s", description)
        return HttpResponseBadRequest(f"Casdoor sign-in failed: {description}")

    try:
        claims = sdk.parse_jwt_token(access_token)
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid Casdoor access token: %s", e)
        return HttpResponseBadRequest("Invalid Casdoor access token")

    if claims.get("owner") != settings.CASDOOR_CONFIG["org_name"]:
        raise PermissionDenied("The Casdoor user belongs to another organization")

    user = get_or_create_user(claims)
    if not user.is_active:
        raise PermissionDenied("This account is disabled")

    auth_login(request, user, backend=_authentication_backend())
    request.session[USER_SESSION_KEY] = claims
    return redirect(next_url)


@require_POST
def logout(request):
    auth_logout(request)
    return redirect(resolve_url(getattr(settings, "LOGOUT_REDIRECT_URL", None) or "/"))
