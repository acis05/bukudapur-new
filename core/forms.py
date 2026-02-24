from django import forms
from .models import Contract, DailyEntry

class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ["name", "start_date", "duration_days", "price_per_portion", "target_portions_per_day", "target_margin_pct", "is_active"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "duration_days": forms.NumberInput(attrs={"class": "form-control"}),
            "price_per_portion": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "target_portions_per_day": forms.NumberInput(attrs={"class": "form-control"}),
            "target_margin_pct": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class DailyEntryForm(forms.ModelForm):
    class Meta:
        model = DailyEntry
        fields = ["date", "portions", "cost_material", "cost_labor", "cost_overhead", "notes", "payment_type", "paid_amount", "credit_due_date",]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "portions": forms.NumberInput(attrs={"class": "form-control"}),
            "cost_material": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "cost_labor": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "cost_overhead": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
    