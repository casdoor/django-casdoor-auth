from casdoor import CasdoorSDK
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import redirect

conf = settings.CASDOOR_CONFIG

sdk = CasdoorSDK(conf.get('endpoint'),
                 conf.get('client_id'),
                 conf.get('client_secret'),
                 conf.get('certificate'),
                 conf.get('org_name'),
                 conf.get('application_name'),
                 conf.get('endpoint'))


def toLogin(request):
    redirect_url = sdk.get_auth_link(redirect_uri=settings.REDIRECT_URI)
    return redirect(redirect_url)


def callback(request):
    code = request.GET.get('code')
    token = sdk.get_oauth_token(code)
    user = sdk.parse_jwt_token(token)
    request.session['user'] = user
    try:
        in_user = User.objects.get(username=user.get('name'))
    except:
        in_user = User.objects.create_user(user.get('name'), user.get('email'), user.get('password'))
        in_user.save()
    in_user = authenticate(username=user.get('name'), password=user.get('password'))
    login(request, in_user)
    return redirect(settings.LOGIN_REDIRECT_URL)
