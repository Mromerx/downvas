from django import forms


class CanvasConfigForm(forms.Form):
    canvas_url = forms.URLField(
        label="URL de Canvas",
        widget=forms.URLInput(attrs={"placeholder": "https://canvas.ejemplo.cl"}),
    )
    api_token = forms.CharField(
        label="Token de API",
        widget=forms.TextInput(attrs={"placeholder": "Tu token de Canvas"}),
    )
    locale = forms.ChoiceField(
        label="Idioma",
        choices=[("es", "Espanol"), ("en", "English")],
        initial="es",
    )


class CourseInputForm(forms.Form):
    course_input = forms.CharField(
        label="Curso",
        widget=forms.TextInput(attrs={
            "placeholder": "ID del curso o URL completa"
        }),
    )
