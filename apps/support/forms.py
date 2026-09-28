from django import forms

from .models import ServiceRequest


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ["category", "subject", "description"]  # customer can never set status/priority/assignee

    def clean_subject(self):
        s = self.cleaned_data["subject"].strip()
        if len(s) < 5:
            raise forms.ValidationError("Subject must be at least 5 characters.")
        return s

    def clean_description(self):
        d = self.cleaned_data["description"].strip()
        if not 20 <= len(d) <= 2000:
            raise forms.ValidationError("Description must be 20-2000 characters.")
        return d


class StaffTicketForm(forms.Form):
    status = forms.ChoiceField(choices=ServiceRequest.Status.choices)
    priority = forms.ChoiceField(choices=ServiceRequest.Priority.choices)
    admin_response = forms.CharField(widget=forms.Textarea, required=False, max_length=2000)
