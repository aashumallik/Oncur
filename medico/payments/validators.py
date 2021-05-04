from django.core.exceptions import ValidationError

import common.constants


def validate_max_length(value):
    value_len = len(value)
    exp_value = common.constants.TEXTFIELD_MAX_LENGTH

    if value_len > exp_value:
        raise ValidationError("You have exceeded the character limit. Please"
                              " remove {0} characters.".format(
                                value_len - exp_value))
