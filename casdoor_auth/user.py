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
