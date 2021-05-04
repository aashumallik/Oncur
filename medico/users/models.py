import stripe
import djstripe
from djstripe.models import Price
from datetime import date
import localflavor.us.models
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill

from django.conf import settings
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse

import common.constants


class User(AbstractUser):
    """
    User fields and logic common to both customers and healthcare pros
    go here.
    """

    MALE = 0
    FEMALE = 1
    OTHER = 2

    GENDER = (
        (MALE, "Male"),
        (FEMALE, "Female"),
        (OTHER, "Other")
    )

    # XXX: Move message to a file that contains common messages
    # XXX: Move constants such as phone max length to a constant file
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'."
                "Up to 15 digits allowed.")

    # first_name, last_name, email, username and password are covered in
    # AbstractUser.
    gender = models.IntegerField(choices=GENDER, default=MALE)
    phone_number = models.CharField(validators=[phone_regex], max_length=17,
        default="")

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})


class Customer(models.Model):
    """
    Fields and logic specific to the customer side of the app
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='customer')
    dob = models.DateField(default=date.today)

    @property
    def name_with_title(self):
        full_name = self.user.get_full_name()
        titled = "{title} {name}"

        if self.user.gender == User.MALE:
            return titled.format(title="Mr.", name=full_name)
        else:
            return titled.format(title="Ms.", name=full_name)

    def charge_stripe_customer(self, payment_method, djstripe_customer):
        """
        Creates a Stripe payment intent and confirms the one-time payment.
        Returns a DjStripe PaymentIntent model object.

        Calls to this function best enclosed in error-catching blocks as it
        makes API calls over the Internet.

        :param payment_method: ID of the Stripe payment method to be associated
        with this customer.
        :param djstripe_customer: DjStripe customer model object
        """
        price = Price.objects\
            .filter(product_id=common.constants.ONE_TIME_PRODUCT_ID).last()

        # Create and confirm a payment intent to charge the customer.
        payment_intent = stripe.PaymentIntent.create(
            amount=price.unit_amount, # in cents
            currency=price.currency,
            confirm=True,
            customer=djstripe_customer.id,
            description=price.product.description,
            payment_method=payment_method
        )
        return djstripe.models.PaymentIntent\
            .sync_from_stripe_data(payment_intent)

    def get_or_create_stripe_customer(self, payment_method):
        """
        Returns a DjStripe customer model object if it already exists for this
        user or creates one if it doesn't exist via the Stripe API, and then
        syncs with DjStripe model data.
        Calls to this function best enclosed in error-catching blocks as it
        makes API calls over the Internet.

        May be considered a bit redundant as DjStripe's own methods exist,
        but according to https://www.ordinarycoders.com/blog/article/django-stripe-monthly-subscription
        this seems to be the safe way of doing it.

        :param payment_method: ID of the Stripe payment method to be associated
        with this customer.
        """
        if not self.user.djstripe_customers.exists():
            customer = stripe.Customer.create(
                name=self.user.get_full_name(),
                payment_method=payment_method,
                email=self.user.email,
                invoice_settings={
                    'default_payment_method': payment_method
                },
                # Add a test address so that payment intent creation
                # works. This is due to export regulations in India.
                # Comment out the address code below when using a Stripe
                # account based in the US.
                address={
                    "city": "Los Angeles",
                    "country": "US",
                    "line1": "Test",
                    "line2": "Test",
                    "postal_code": "90001",
                    "state": "California"
                }
            )

            djstripe_customer = djstripe.models.Customer\
                .sync_from_stripe_data(customer)
            self.user.djstripe_customers.add(djstripe_customer)

        return self.user.djstripe_customers.first()

    def subscribe_stripe_customer(self, plan_id, djstripe_customer):
        """
        Subscribes a Stripe customer to a given plan/price and internally
        confirms the payment.

        Calls to this function best enclosed in error-catching blocks as it
        makes API calls over the Internet.

        :param plan_id: Stripe subscription plan ID
        :param djstripe_customer: DjStripe customer model object
        """
        subscription = stripe.Subscription.create(
            customer=djstripe_customer.id,
            items=[
                {
                    "price": plan_id
                }
            ],
            default_payment_method=djstripe_customer.default_payment_method_id,
            expand=["latest_invoice.payment_intent"]
        )

        return djstripe.models.Subscription.sync_from_stripe_data(subscription)


class MedicalProfessional(models.Model):
    """
    Fields and logic specific to the doctor side of the app
    """

    class StaffType(models.IntegerChoices):
        # The new way to declare choices for a particular field
        DOCTOR = 0, 'MD'
        NURSE = 1, 'Nurse Practitioner'
        SECONDARY_STAFF = 2, 'Physician Assistant'

    class DoctorMedicalSpecialty(models.IntegerChoices):
        FAMILY_MEDICINE = 0, 'Family Medicine'
        INTERNAL_MEDICINE = 1, 'Internal Medicine'
        EMERGENCY_MEDICINE = 2, 'Emergency Medicine'
        PEDIATRICS = 3, 'Pediatrics'

    class OtherMedicalSpecialty(models.IntegerChoices):
        REGISTERED_NURSE = 0, 'Registered Nurse'
        FAMILY_NURSE = 1, 'Family Nurse'
        CARDIAC_NURSE = 2, 'Cardiac Nurse'
        ANESTHETIST = 3, 'Anesthetist'
        RADIOLOGIST = 4, 'Radiologist'

    user = models.OneToOneField(settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='medical_pro')
    staff_type = models.IntegerField(choices=StaffType.choices,
        default=StaffType.DOCTOR)
    state_of_license = localflavor.us.models.USStateField(default="CA")
    is_verified = models.BooleanField(default=False)

    # Specifically for doctors
    doctor_specialty = models.IntegerField(null=True,
        choices=DoctorMedicalSpecialty.choices,
        default=DoctorMedicalSpecialty.INTERNAL_MEDICINE)
    # For nurses and other staff
    other_specialty = models.IntegerField(null=True,
        choices=OtherMedicalSpecialty.choices,
        default=OtherMedicalSpecialty.REGISTERED_NURSE)

    profile_picture = models.ImageField(upload_to='profile_pictures')
    # Store a thumbnail to show to customers on the doctor selection page
    profile_thumbnail = ImageSpecField(source='profile_picture',
        processors=[ResizeToFill(common.constants.PICTURE_WIDTH,
                                 common.constants.PICTURE_HEIGHT)],
        format=common.constants.PICTURE_FORMAT,
        options={'quality': common.constants.PICTURE_QUALITY})

    medical_license = models.FileField(upload_to='medical_licenses')

    @property
    def name_with_title(self):
        full_name = self.user.get_full_name()
        titled = "{title} {name}"

        if self.staff_type == MedicalProfessional.StaffType.DOCTOR:
            return titled.format(title="Dr.", name=full_name)
        elif self.user.gender == User.MALE:
            return titled.format(title="Mr.", name=full_name)
        else:
            return titled.format(title="Ms.", name=full_name)
