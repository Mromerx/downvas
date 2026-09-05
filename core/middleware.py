from django.conf import settings
from django.utils import translation


def _valid_locale(locale):
    if not locale:
        return None
    if not isinstance(locale, str):
        return None
    for code, _ in settings.LANGUAGES:
        if locale == code:
            return code
    return None


class LocaleFromSessionMiddleware:
    """Activate the language selected in the settings form (session only).

    Falls back to settings.LANGUAGE_CODE when the user has not made an
    explicit choice, ignoring the browser's Accept-Language header for a
    predictable experience.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        locale = _valid_locale(request.session.get("locale"))
        if locale is None:
            locale = settings.LANGUAGE_CODE
        translation.activate(locale)
        request.LANGUAGE_CODE = translation.get_language()
        response = self.get_response(request)
        translation.deactivate()
        return response