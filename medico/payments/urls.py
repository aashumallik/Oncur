from django.urls import path

from medico.payments.views import checkout, consultation, modify_payment_method

app_name = "payments"
urlpatterns = [
    path("checkout/", view=checkout, name="checkout"),
    path("consultation/", view=consultation, name="consultation"),
    path("modify-payment-method/", view=modify_payment_method,
        name="modify-payment-method"),
]
