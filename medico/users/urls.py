from django.urls import path

from medico.users.views import (
    customer_signup_view,
    medical_signup_view,
    user_detail_view,
    user_redirect_view,
    user_update_view,
    cancel_subscription,
    manage_subscription
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("subscription/", view=manage_subscription, name="subscription"),
    path("cancel-subscription/", view=cancel_subscription,
        name="cancel-subscription"),
    path("customer-signup/", view=customer_signup_view, name="customer-signup"),
    path("medical-signup/", view=medical_signup_view, name="medical-signup"),
    # Note: The user detail view should be at the last, otherwise any
    # URL with "/users/something" will trigger the detail view with "something"
    # as the username, instead of the intended view.
    path("<str:username>/", view=user_detail_view, name="detail"),
]
