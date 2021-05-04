import copy
import localflavor.us.forms

from django import forms
from django.contrib.auth import forms as admin_forms
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _

from allauth.account.forms import SignupForm
import medico.users.models
import common.constants

User = get_user_model()


class AccountSignupForm(SignupForm):
    """
    Note: The save() method is not called on this form; it is called in the
    child forms representing customers and healthcare professionals respectively.
    """
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'."
                " Up to 15 digits allowed.")

    gender = forms.TypedChoiceField(label="Gender",
        choices=medico.users.models.User.GENDER)
    phone = forms.CharField(label="Phone Number", validators=[phone_regex])
    first_name = forms.CharField(label="First Name")
    last_name = forms.CharField(label="Last Name")

    def _set_common_fields(self, account):
        account.gender = self.cleaned_data['gender']
        account.phone = self.cleaned_data['phone']
        account.first_name = self.cleaned_data['first_name']
        account.last_name = self.cleaned_data['last_name']


class CustomerSignupForm(AccountSignupForm):
    """
    Validation specific to the customer
    """
    dob = forms.DateField(label="Date of Birth", widget=forms.DateInput({
        'placeholder': '__/__/____', 'class': 'form-control', 'type': 'date'
    }))

    def clean_dob(self):
        today_18_yrs = localtime(now())
        today_18_yrs = today_18_yrs.replace(year=today_18_yrs.year - 18)
        dob = self.cleaned_data['dob']

        if dob > today_18_yrs.date():
            self.add_error('dob', "You must be at-least 18 years old to use"
                                  " this website.")

        return dob

    def save(self, request):
        account = super().save(request)
        self._set_common_fields(account)
        account.save()

        # Create customer object and attach to user
        medico.users.models.Customer.objects.create(user=account,
            dob=self.cleaned_data['dob'])

        return account


class MedicalProSignupForm(AccountSignupForm):
    staff_type = forms.TypedChoiceField(label="You are",
        choices=medico.users.models.MedicalProfessional.StaffType.choices)
    state_of_license = localflavor.us.forms.USStateField(
        label="State of Licensure", widget=localflavor.us.forms.USStateSelect)
    doctor_specialty = forms.TypedChoiceField(required=False,
        label="Board certified specialty",
        choices=medico.users.models.MedicalProfessional
                      .DoctorMedicalSpecialty.choices)
    other_specialty = forms.TypedChoiceField(required=False,
        label="Your specialty",
        choices=medico.users.models.MedicalProfessional
                      .OtherMedicalSpecialty.choices)
    # XXX: Figure out how to validate extensions, size, etc of the image/file
    profile_picture = forms.ImageField()
    medical_license = forms.FileField()

    def clean(self):
        cleaned_data = super().clean()
        staff_type = cleaned_data.get('staff_type')
        doctor_specialty = cleaned_data.get('doctor_specialty')
        other_specialty = cleaned_data.get('other_specialty')

        if staff_type is None:
            # Do nothing here
            return cleaned_data

        if staff_type == medico.users.models.MedicalProfessional\
                .StaffType.DOCTOR:
            if doctor_specialty is None:
                self.add_error('doctor_specialty',
                    common.constants.REQUIRED_MESSAGE)
        else:
            if other_specialty is None:
                self.add_error('other_specialty',
                    common.constants.REQUIRED_MESSAGE)

        return cleaned_data

    def save(self, request):
        account = super().save(request)
        self._set_common_fields(account)
        account.save()

        # XXX: Hardcoding of User model field names
        exclude_fields = ["first_name", "last_name", "gender", "phone", "email",
            "username", "password1", "password2"]
        create_kwargs = {k: v for k, v in self.cleaned_data.items() if
                         k not in exclude_fields}

        # Create medical professional object and attach to user
        medico.users.models.MedicalProfessional.objects.create(user=account,
            **create_kwargs)

        return account


class UserChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(admin_forms.UserCreationForm):
    class Meta(admin_forms.UserCreationForm.Meta):
        model = User

        error_messages = {
            "username": {"unique": _("This username has already been taken.")}
        }
