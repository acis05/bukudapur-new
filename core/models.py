from django.db import models

class Contract(models.Model):
    name = models.CharField(max_length=160, default="Kontrak MBG")
    start_date = models.DateField()
    duration_days = models.PositiveIntegerField(default=30)

    price_per_portion = models.DecimalField(max_digits=12, decimal_places=2)
    target_portions_per_day = models.PositiveIntegerField(default=1000)

    target_margin_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20)  # 20.00 = 20%

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({'aktif' if self.is_active else 'nonaktif'})"


class DailyEntry(models.Model):
    PAYMENT_CHOICES = [
        ("CASH", "Tunai"),
        ("CREDIT", "Kredit"),
    ]
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="entries")
    date = models.DateField()

    portions = models.PositiveIntegerField()

    cost_material = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost_labor = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cost_overhead = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("contract", "date")]
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} - {self.portions} porsi"

    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="CASH")
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit_due_date = models.DateField(null=True, blank=True)

    @property
    def sales_amount(self):
        # nilai penjualan = porsi * harga kontrak
        if self.contract_id and self.portions:
            return float(self.portions) * float(self.contract.price_per_portion)
        return 0.0
        
    @property
    def total_cost(self):
        return (self.cost_material or 0) + (self.cost_labor or 0) + (self.cost_overhead or 0)

    @property
    def revenue(self):
        # diisi di view (pakai price_per_portion dari contract)
        return None
