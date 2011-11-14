from django import forms

class ModelForm(forms.ModelForm):
    css = {}

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        for k, v in self.css.iteritems():
            self.fields[k].widget.attrs['class'] = v
