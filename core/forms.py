from django import forms


class CanvasConfigForm(forms.Form):
    canvas_url = forms.URLField(
        label="Canvas URL",
        widget=forms.URLInput(attrs={"placeholder": "https://canvas.example.com"}),
    )
    api_token = forms.CharField(
        label="API Token",
        required=False,
        widget=forms.PasswordInput(attrs={"placeholder": "Your Canvas API token"}),
    )
    locale = forms.ChoiceField(
        label="Language",
        choices=[("en", "English"), ("es", "Spanish")],
        initial="en",
    )


class CourseInputForm(forms.Form):
    course_input = forms.CharField(
        label="Course",
        widget=forms.TextInput(attrs={
            "placeholder": "Course ID or full URL"
        }),
    )
