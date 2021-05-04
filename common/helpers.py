import stripe


def payment_method_serialize(subscription):
    """
    Serializes a DjStripe subscription object's default payment instrument
    for front-end consumption (card data).
    """
    return subscription.default_payment_method.card

def subscription_serialize(subscription):
    """
    Serializes a DjStripe subscription object for front-end consumption
    """
    return {
        "started_at": subscription.current_period_start.strftime("%A, %b %d"),
        "ends_at": subscription.current_period_end.strftime("%A, %b %d"),
        "human_readable_price": subscription.plan.human_readable_price
    }
