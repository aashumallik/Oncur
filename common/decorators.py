from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, reverse


def medical_pro_only(view):
    """
    View decorator that can be applied to force a view to only consider
    medical professionals.
    """
    def as_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.profile_type != 'medical_pro':
                return redirect(reverse('users:detail',
                    kwargs={'username': request.user.username}))
        return view(request, *args, **kwargs)

    return as_view


def customer_only(view):
    """
    View decorator that can be applied to force a view to only consider
    customers.
    """
    def as_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.profile_type != 'customer':
                return redirect(reverse('users:detail',
                    kwargs={'username': request.user.username}))
        return view(request, *args, **kwargs)

    return as_view
