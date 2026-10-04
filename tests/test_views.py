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

import datetime
from unittest import mock
from urllib.parse import parse_qs, urlparse

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from casdoor_auth.models import CasdoorUser


def make_key_and_certificate():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "casdoor-test")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return key, certificate.public_bytes(serialization.Encoding.PEM).decode()


KEY, CERTIFICATE = make_key_and_certificate()
OTHER_KEY, _ = make_key_and_certificate()
CASDOOR_CONFIG = {**settings.CASDOOR_CONFIG, "certificate": CERTIFICATE}


def make_token(key=KEY, **claims):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "owner": "casbin",
        "name": "alice",
        "id": "a1b2c3",
        "sub": "a1b2c3",
        "email": "alice@example.com",
        "firstName": "Alice",
        "lastName": "Liddell",
        "password": "",
        "aud": [CASDOOR_CONFIG["client_id"]],
        "iat": now,
        "exp": now + datetime.timedelta(hours=1),
    }
    payload.update(claims)
    return jwt.encode(payload, key, algorithm="RS256")


@override_settings(CASDOOR_CONFIG=CASDOOR_CONFIG)
class CasdoorAuthTest(TestCase):
    def start_login(self, next_url=None):
        response = self.client.get("/casdoor/login/", {"next": next_url} if next_url else {})
        self.assertEqual(response.status_code, 302)
        return parse_qs(urlparse(response["Location"]).query)["state"][0]

    def sign_in(self, token=None, state=None, next_url=None):
        expected_state = self.start_login(next_url)
        token_response = {"access_token": token or make_token()}
        with mock.patch("casdoor.CasdoorSDK.get_oauth_token", return_value=token_response) as get_oauth_token:
            response = self.client.get("/casdoor/callback/", {"code": "the-code", "state": state or expected_state})
        return response, get_oauth_token

    def current_username(self):
        return self.client.get("/home/").content.decode()

    def test_login_redirects_to_casdoor(self):
        response = self.client.get("/casdoor/login/")
        location = urlparse(response["Location"])
        params = parse_qs(location.query)
        self.assertEqual(location._replace(query="").geturl(), "http://localhost:8000/login/oauth/authorize")
        self.assertEqual(params["client_id"], ["test-client-id"])
        self.assertEqual(params["redirect_uri"], ["http://testserver/casdoor/callback/"])
        self.assertEqual(params["response_type"], ["code"])
        self.assertEqual(params["state"][0], self.client.session["casdoor_state"])
        self.assertGreaterEqual(len(params["state"][0]), 32)

    @override_settings(REDIRECT_URI="https://app.example.com/casdoor/callback/")
    def test_login_uses_configured_redirect_uri(self):
        response = self.client.get("/casdoor/login/")
        params = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(params["redirect_uri"], ["https://app.example.com/casdoor/callback/"])

    def test_sign_in_creates_user(self):
        response, get_oauth_token = self.sign_in()
        get_oauth_token.assert_called_once_with(code="the-code")
        self.assertRedirects(response, "/home/", fetch_redirect_response=False)
        user = get_user_model().objects.get(username="alice")
        self.assertFalse(user.has_usable_password())
        self.assertEqual((user.email, user.first_name, user.last_name), ("alice@example.com", "Alice", "Liddell"))
        self.assertEqual(CasdoorUser.objects.get(user=user).casdoor_id, "a1b2c3")
        self.assertEqual(self.current_username(), "alice")
        self.assertEqual(self.client.session["user"]["name"], "alice")

    def test_sign_in_again_uses_the_linked_user_after_rename(self):
        self.sign_in()
        self.client.logout()
        self.sign_in(token=make_token(name="alice2", email="alice2@example.com"))
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(self.current_username(), "alice")
        self.assertEqual(get_user_model().objects.get().email, "alice2@example.com")
        self.assertEqual(CasdoorUser.objects.get().name, "alice2")

    def test_rejects_wrong_state(self):
        response, get_oauth_token = self.sign_in(state="forged")
        self.assertEqual(response.status_code, 400)
        get_oauth_token.assert_not_called()

    def test_rejects_callback_without_login(self):
        response = self.client.get("/casdoor/callback/", {"code": "the-code", "state": "x"})
        self.assertEqual(response.status_code, 400)

    def test_state_is_single_use(self):
        state = self.start_login()
        with mock.patch("casdoor.CasdoorSDK.get_oauth_token", return_value={"access_token": make_token()}):
            self.client.get("/casdoor/callback/", {"code": "the-code", "state": state})
            self.client.logout()
            response = self.client.get("/casdoor/callback/", {"code": "the-code", "state": state})
        self.assertEqual(response.status_code, 400)

    def test_casdoor_error_is_reported(self):
        self.start_login()
        response = self.client.get("/casdoor/callback/", {"error": "access_denied", "error_description": "denied"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"denied", response.content)

    def test_rejects_token_with_bad_signature(self):
        response, _ = self.sign_in(token=make_token(key=OTHER_KEY))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.exists())

    def test_rejects_expired_token(self):
        response, _ = self.sign_in(token=make_token(exp=datetime.datetime(2020, 1, 1)))
        self.assertEqual(response.status_code, 400)

    def test_rejects_token_for_another_application(self):
        response, _ = self.sign_in(token=make_token(aud=["another-client"]))
        self.assertEqual(response.status_code, 400)

    def test_rejects_user_of_another_organization(self):
        response, _ = self.sign_in(token=make_token(owner="built-in"))
        self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user_model().objects.exists())

    def test_token_error_is_reported(self):
        state = self.start_login()
        error = {"error": "invalid_grant", "error_description": "authorization code has been used"}
        with mock.patch("casdoor.CasdoorSDK.get_oauth_token", return_value=error):
            response = self.client.get("/casdoor/callback/", {"code": "the-code", "state": state})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"authorization code has been used", response.content)

    def test_does_not_take_over_user_with_password(self):
        get_user_model().objects.create_superuser("alice", "root@example.com", "secret")
        response, _ = self.sign_in()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CasdoorUser.objects.exists())
        self.assertEqual(self.current_username(), "")

    @override_settings(CASDOOR_LINK_EXISTING_USERS=True)
    def test_links_user_with_password_when_allowed(self):
        get_user_model().objects.create_user("alice", "alice@example.com", "secret")
        response, _ = self.sign_in()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.current_username(), "alice")

    def test_links_user_created_by_old_version(self):
        get_user_model().objects.create_user("alice", "alice@example.com", "")
        self.sign_in()
        self.assertEqual(self.current_username(), "alice")
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_does_not_link_user_already_linked_to_another_casdoor_user(self):
        self.sign_in()
        self.client.logout()
        response, _ = self.sign_in(token=make_token(id="other-id", sub="other-id"))
        self.assertEqual(response.status_code, 403)

    @override_settings(CASDOOR_CREATE_USERS=False)
    def test_does_not_create_users_when_disabled(self):
        response, _ = self.sign_in()
        self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user_model().objects.exists())

    def test_rejects_inactive_user(self):
        self.sign_in()
        self.client.logout()
        get_user_model().objects.filter(username="alice").update(is_active=False)
        response, _ = self.sign_in()
        self.assertEqual(response.status_code, 403)

    def test_redirects_to_next(self):
        response, _ = self.sign_in(next_url="/admin/")
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)

    def test_ignores_external_next(self):
        response, _ = self.sign_in(next_url="https://evil.example.com/")
        self.assertRedirects(response, "/home/", fetch_redirect_response=False)

    def test_logout(self):
        self.sign_in()
        self.assertEqual(self.client.get("/casdoor/logout/").status_code, 405)
        response = self.client.post("/casdoor/logout/")
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(self.current_username(), "")
