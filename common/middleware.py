import django


class UserTypeMiddleware:
    """
    This middleware adds two attributes to the Django HttpRequest object,
    namely `profile` and `profile_type`, which stand for the associated
    customer/medical professional object and the type of user respectively.

    It runs before *every* request on the platform, and the two attributes
    will be used extensively to differentiate between user types.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if hasattr(request.user, 'customer'):
                setattr(request, 'profile_type', 'customer')
                setattr(request, 'profile', request.user.customer)
            elif hasattr(request.user, 'medical_pro'):
                setattr(request, 'profile_type', 'medical_pro')
                setattr(request, 'profile', request.user.medical_pro)
            else:
                setattr(request, 'profile_type', 'anonymous')
        else:
            setattr(request, 'profile_type', 'anonymous')

        return self.get_response(request)
