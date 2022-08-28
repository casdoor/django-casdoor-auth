# django-casdoor-auth


[![Version](https://img.shields.io/pypi/v/casdoor-auth.svg)](https://pypi.org/project/casdoor-auth/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/casdoor-auth.svg)](https://pypi.org/project/casdoor-auth/)
[![Pyversions](https://img.shields.io/pypi/pyversions/casdoor-auth.svg)](https://pypi.org/project/casdoor-auth/)

Casdoor's SDK for Django will allow you to easily connect your application to the Casdoor authentication system without having to implement it from scratch.

## Step1. install app

casdoor-auth is available on PyPI:

```console
$ pip install casdoor-auth
```

casdoor-auth is simple to use. We will show you the steps below.
## Step2. Config
setting.py

Add "casdoor_auth" in INSTALLED_APPS
```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "casdoor_auth"
]
```

Initialization requires 6 parameters, which are all str type:

| Name (in order)  | Must | Description                                         |
| ---------------- | ---- | --------------------------------------------------- |
| endpoint         | Yes  | Casdoor Server Url, such as `http://localhost:8000` |
| client_id         | Yes  | Application.client_id                               |
| client_secret     | Yes  | Application.client_secret                           |
| certificate       | Yes  | The public key for the Casdoor application's cert   |
| org_name | Yes  | Application.organization                                    |
| application_name | Yes | Application.name |

```python
CASDOOR_CONFIG = {
    'endpoint': 'http://localhost:8000',
    'client_id': '<client-id>',
    'client_secret': '<client-secret>',
    'certificate': '''<certificate>''',
    'org_name': 'built-in',
    'application_name': 'app-built-in'
}
```

The redirect url, is the URL that your APP is configured to listen to the response from Casdoor.
```python
REDIRECT_URI = 'http://127.0.0.1:8000/casdoor/callback/'
```
The login redirect url, after login successfully, you will jump to this page.
```python
LOGIN_REDIRECT_URL = '/'
```
## Step3. router
urls.py

```python
urlpatterns = [
    ...
    path('casdoor/', include('casdoor_auth.urls')),
    ...
]
```
The casdoor_auth provider two functions for using Casdoor.
```python
urlpatterns = [
    path('login/', views.toLogin, name='casdoor_sso'),
    path('callback/', views.callback, name='callback'),
]
```
To add a button for using the Casdoor login,  for example:
```html
<button><a href="{% url 'casdoor_sso' %}">casdoor</a></button>`
```


