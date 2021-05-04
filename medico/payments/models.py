from django.db import models

import medico.payments.validators as validators
import common.constants


class CheckoutInformation(models.Model):
    """
    Stores extra information not related to Stripe's models on the checkout
    page.
    """
    reason_for_visit = models.TextField(blank=True,
        max_length=common.constants.TEXTFIELD_MAX_LENGTH,
        validators=[validators.validate_max_length])
    stripe_payment_intent = models.OneToOneField("djstripe.PaymentIntent",
        on_delete=models.SET_NULL, null=True, blank=True)
    stripe_customer = models.ForeignKey("djstripe.Customer", null=True,
        on_delete=models.CASCADE, blank=True)

    class Meta:
        verbose_name_plural = "checkout information objects"

    def __str__(self):
        return "Checkout information for customer {0}"\
            .format(self.stripe_customer.name)
