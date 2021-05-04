import stripe
from allauth.account.views import SignupView

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

import common.decorators
import common.helpers
from .forms import CustomerSignupForm, MedicalProSignupForm

User = get_user_model()


class CustomerSignupView(SignupView):
    template_name = 'account/customer_signup.html'
    form_class = CustomerSignupForm
    view_name = 'customer-signup'


customer_signup_view = CustomerSignupView.as_view()


class MedicalProSignupView(SignupView):
    template_name = 'account/medical_signup.html'
    form_class = MedicalProSignupForm
    view_name = 'medical-signup'


medical_signup_view = MedicalProSignupView.as_view()


class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = User
    # XXX: Add more fields in here when making a profile page where users can
    # update their details.
    fields = ["first_name", "last_name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        return reverse("users:detail",
            kwargs={"username": self.request.user.username})

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail",
            kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


@login_required
@common.decorators.customer_only
def cancel_subscription(request):
    if request.method != 'POST':
        return HttpResponse('Method not allowed')

    djstripe_customer = request.user.djstripe_customers.first()

    if not (djstripe_customer and djstripe_customer.subscription):
        return JsonResponse({
            "error": {
                'message': 'No subscription was found on this user.',
                'type': 'NotFoundError'
            }
        }, status=404)

    sub_id = djstripe_customer.subscription.id
    try:
        # Terminate immediately by setting at_period_end False
        djstripe_customer.subscription.cancel(at_period_end=False)
    except stripe.error.StripeError as e:
        return JsonResponse({
            "error": {
                'message': e.error.message,
                'type': 'StripeError'
            }
        })

    return JsonResponse({
        "next_url": reverse('home'),
        "deleted_sub_id": sub_id
    })


@login_required
@common.decorators.customer_only
def manage_subscription(request):
    if request.method != 'GET':
        return HttpResponse('Method not allowed')

    djstripe_customer = request.user.djstripe_customers.first()
    subscription = djstripe_customer and djstripe_customer.subscription

    return render(request, "users/subscription.html", {
        "subscription": subscription and \
            common.helpers.subscription_serialize(subscription) or None,
        "card_data": subscription and \
            common.helpers.payment_method_serialize(subscription) or None,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_TEST_PUBLIC_KEY
    })
