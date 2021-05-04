import json
import stripe
import djstripe
from djstripe.models import Product, Price

from .models import CheckoutInformation

from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse

import common.constants
import common.decorators

common_error = 'Something went wrong. Please refresh the page or try again'\
    ' later.'


@login_required
@common.decorators.customer_only
def consultation(request):
    if "checkout_success" in request.session and \
            request.session["checkout_success"]:
        del request.session["checkout_success"]
        messages.success(request, "Your card payment was successful.")
    return render(request, "payments/consultation.html")


@login_required
@common.decorators.customer_only
def checkout(request):
    if request.method not in ['GET', 'POST']:
        return HttpResponse('Method not allowed')

    products = Product.objects.all()
    # XXX: Fix this ID in a constants file, or maybe even make it a setting
    # populated via environment.
    one_time_price = Price.objects\
        .filter(product_id=common.constants.ONE_TIME_PRODUCT_ID)\
        .last()

    if request.method == 'GET':

        return render(request, "payments/checkout.html", {
            "products": products,
            "price": one_time_price,
            # XXX: Change if production
            "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_TEST_PUBLIC_KEY
        })

    elif request.method == 'POST':
        try:
            # XXX: Some sort of validation here? Add form validation maybe.
            data = json.loads(request.body)
            payment_method = data['payment_method']
            reason_for_visit = data['reason_for_visit']
            plan_id = data['plan_id']
            stripe.api_key = djstripe.settings.STRIPE_SECRET_KEY

            # Before making any Stripe calls, make sure that our checkout
            # information "checks out" (heh).
            cf_info = CheckoutInformation(reason_for_visit=reason_for_visit)
            cf_info.clean_fields()

            payment_method_obj = stripe.PaymentMethod.retrieve(payment_method)
            djstripe.models.PaymentMethod\
                .sync_from_stripe_data(payment_method_obj)
            djstripe_customer = request.user.customer\
                .get_or_create_stripe_customer(payment_method)

            if plan_id:
                # If there's a plan ID, we want to subscribe our customer to
                # that particular plan.
                djstripe_sub = request.user.customer\
                    .subscribe_stripe_customer(plan_id, djstripe_customer)
            else:
                # Otherwise we're doing a one-time checkout.
                djstripe_intent = request.user.customer\
                    .charge_stripe_customer(payment_method, djstripe_customer)
                cf_info.stripe_payment_intent = djstripe_intent

            cf_info.stripe_customer = djstripe_customer
            cf_info.save()

            request.session["checkout_success"] = True
            return JsonResponse({
                "next_url": reverse('payments:consultation'),
                "customer_id": djstripe_customer.id,
                "intent_status": "succeeded"
            })

        except ValidationError as e:
            return JsonResponse({
                "error": {
                    'message': "Please fill in all the fields in the checkout"
                               " form properly.",
                    'messages': e.messages,
                    'type': 'FormError'
                }
            }, status=400)

        except (KeyError, ValueError):
            return JsonResponse({
                "error": {
                    'message': common_error,
                    'type': 'RequestError'
                }
            }, status=400)
        except stripe.error.StripeError as e:
            # XXX: When logging is added, log `e` instances.
            return JsonResponse({
                "error":{
                    'message': e.error.message,
                    'type': 'StripeError'
                }
            }, status=500)
        except Exception as e:
            print(e)
            return JsonResponse({
                "error":{
                    'message': common_error,
                    'type': 'ServerError'
                }
            }, status=500)


@login_required
@common.decorators.customer_only
def modify_payment_method(request):
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

    try:
        data = json.loads(request.body)
        payment_method = data['payment_method']
        stripe.api_key = djstripe.settings.STRIPE_SECRET_KEY

        # The payment method must be attached to both the subscription and
        # the customer.
        payment_method_obj = stripe.PaymentMethod.retrieve(payment_method)
        stripe.PaymentMethod.attach(payment_method,
            customer=djstripe_customer.id)
        djstripe.models.PaymentMethod.sync_from_stripe_data(payment_method_obj)

        stripe.PaymentMethod.attach(payment_method,
            customer=djstripe_customer.id)
        subscription = stripe.Subscription.modify(
            djstripe_customer.subscription.id,
            default_payment_method=payment_method
        )
        djstripe.models.Subscription.sync_from_stripe_data(subscription)

        return JsonResponse({
            "payment_method_id": payment_method
        })

    except (KeyError, ValueError):
        return JsonResponse({
            "error": {
                'message': common_error,
                'type': 'RequestError'
            }
        }, status=400)
    except stripe.error.StripeError as e:
        # XXX: When logging is added, log `e` instances.
        return JsonResponse({
            "error":{
                'message': e.error.message,
                'type': 'StripeError'
            }
        }, status=500)
    except Exception as e:
        print(e)
        return JsonResponse({
            "error":{
                'message': common_error,
                'type': 'ServerError'
            }
        }, status=500)


# XXX: Add a webhook to handle subscription invoicing failure (recurring
# payment failure) and fire an email off to the user offering them to
# change their payment method.
