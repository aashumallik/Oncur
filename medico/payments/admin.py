from django.contrib import admin

import medico.payments.models

admin.site.register(medico.payments.models.CheckoutInformation)
