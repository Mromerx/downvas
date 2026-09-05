from django import forms
from django.utils.translation import gettext_lazy as _


class CanvasConfigForm(forms.Form):
    canvas_url = forms.URLField(
        label=_("Canvas URL"),
        widget=forms.URLInput(attrs={"placeholder": "https://canvas.example.com"}),
    )
    api_token = forms.CharField(
        label=_("API Token"),
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": _("Your Canvas API token")}),
    )
    locale = forms.ChoiceField(
        label=_("Language"),
        choices=[("en", _("English")), ("es", _("Spanish"))],
        initial="en",
    )


class CourseInputForm(forms.Form):
    course_input = forms.CharField(
        label=_("Course"),
        widget=forms.TextInput(attrs={
            "placeholder": _("Course ID or full URL")
        }),
    )
