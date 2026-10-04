# django-casdoor-auth

[![GitHub Action](https://github.com/casdoor/django-casdoor-auth/workflows/build/badge.svg?branch=master)](https://github.com/casdoor/django-casdoor-auth/actions)
[![Version](https://img.shields.io/pypi/v/django-casdoor-auth.svg)](https://pypi.org/project/django-casdoor-auth/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/django-casdoor-auth.svg)](https://pypi.org/project/django-casdoor-auth/)
[![Pyversions](https://img.shields.io/pypi/pyversions/django-casdoor-auth.svg)](https://pypi.org/project/django-casdoor-auth/)
[![Discord](https://img.shields.io/discord/1022748306096537660?logo=discord&label=discord&color=5865F2)](https://discord.gg/5rPsrAzK7S)

A Django app that lets users sign in to your Django site with [Casdoor](https://casdoor.ai) (OAuth 2.0 authorization code flow), built on [casdoor-python-sdk](https://github.com/casdoor/casdoor-python-sdk).

- The `state` parameter is random, stored in the session and checked on the callback (no login CSRF).
- The access token's signature, expiry and audience are verified with your application's certificate, and only users of the configured organization are accepted.
- Each Django user is linked to a Casdoor user by its immutable Casdoor ID, so renaming a user in Casdoor keeps the same Django account, and nobody can take over an existing Django account (e.g. a local `admin` superuser) by signing up in Casdoor with the same name.
- Users created through Casdoor get an unusable password: they can only sign in through Casdoor.

Requires Python 3.10+ and Django 4.2+.

## Install

```shell
pip install django-casdoor-auth
```

## Configure

Add `casdoor_auth` to `INSTALLED_APPS` in `settings.py` (it needs `django.contrib.auth` and `django.contrib.sessions`):

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "casdoor_auth",
]
```

Then add your Casdoor application:

```python
CASDOOR_CONFIG = {
    "endpoint": "https://door.casdoor.com",
    "client_id": "<client-id>",
    "client_secret": "<client-secret>",
    "certificate": """-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----""",
    "org_name": "casbin",
    "application_name": "app-example",
}

LOGIN_REDIRECT_URL = "/"
```

| Key                | Required | Description                                                                                           |
| ------------------ | -------- | ----------------------------------------------------------------------------------------------------- |
| `endpoint`         | Yes      | Casdoor server URL, e.g. `http://localhost:8000`                                                      |
| `client_id`        | Yes      | Client ID of the Casdoor application                                                                  |
| `client_secret`    | Yes      | Client secret of the Casdoor application                                                              |
| `certificate`      | Yes      | Public certificate (PEM) of the application's cert in Casdoor, used to verify access tokens           |
| `org_name`         | Yes      | Organization of the application; users of other organizations are rejected                           |
| `application_name` | Yes      | Name of the Casdoor application                                                                       |
| `front_endpoint`   | No       | Casdoor URL that browsers use, if it differs from `endpoint` (e.g. `endpoint` is an internal address) |
| `scope`            | No       | OAuth scope, `read` by default                                                                        |

Other settings:

| Setting                       | Default                 | Description                                                                                                                                                            |
| ----------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `REDIRECT_URI`                | the callback view's URL | Callback URL sent to Casdoor. Set it when Django is behind a proxy and cannot build its public URL                                                                     |
| `LOGIN_REDIRECT_URL`          | `/accounts/profile/`    | Where users go after signing in, unless the login URL has a safe `?next=`                                                                                              |
| `LOGOUT_REDIRECT_URL`         | `/`                     | Where users go after signing out                                                                                                                                       |
| `CASDOOR_CREATE_USERS`        | `True`                  | Create a Django user the first time a Casdoor user signs in. When `False`, Casdoor users without a Django account are rejected |
| `CASDOOR_LINK_EXISTING_USERS` | `False`                 | Let a Casdoor user sign in as an existing Django user of the same name that has a password. Only enable it if every name in your Casdoor organization is trustworthy |

In the Casdoor application, add the callback URL (e.g. `https://example.com/casdoor/callback/`) to **Redirect URLs**.

Run the migrations to create the table that links Django users to Casdoor users:

```shell
python manage.py migrate
```

## Routes

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("casdoor/", include("casdoor_auth.urls")),
]
```

| URL                 | Name             | Description                                                            |
| ------------------- | ---------------- | ---------------------------------------------------------------------- |
| `/casdoor/login/`   | `casdoor_sso`    | Redirects to Casdoor. Accepts `?next=` to return to a page afterwards  |
| `/casdoor/callback/`| `callback`       | Casdoor redirects here; signs the user in                              |
| `/casdoor/logout/`  | `casdoor_logout` | Signs the user out of Django (POST only, like Django's `LogoutView`)   |

```html
<a href="{% url 'casdoor_sso' %}?next={{ request.path|urlencode }}">Sign in with Casdoor</a>

<form method="post" action="{% url 'casdoor_logout' %}">
  {% csrf_token %}
  <button type="submit">Sign out</button>
</form>
```

After signing in, `request.user` is the Django user and `request.session["user"]` holds the claims of the Casdoor access token (name, display name, email, roles, permissions, ...).

## Upgrading from 1.x

- Run `python manage.py migrate`.
- Users that 1.x created are linked to their Casdoor user the next time they sign in. A Django user with a real password is not taken over by a Casdoor user of the same name unless `CASDOOR_LINK_EXISTING_USERS = True`.
- The logout view only accepts POST.
- The helper views in `casdoor_auth.user` are removed; call [casdoor-python-sdk](https://github.com/casdoor/casdoor-python-sdk) directly instead.

## Development

```shell
pip install -e . black ruff
python -m django test --settings=tests.settings --pythonpath=.
black casdoor_auth tests && ruff check casdoor_auth tests
```

## License

[Apache 2.0](LICENSE)
