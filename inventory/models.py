from django.db import models
from django.utils import timezone


class InventoryCategory(models.TextChoices):
    BOOKS = "BOOKS", "Books"
    WORKBOOKS = "WORKBOOKS", "Workbooks"
    STUDY_KITS = "STUDY_KITS", "Study Kits"
    LAPTOPS = "LAPTOPS", "Laptops"
    SCHOOL_ESSENTIALS = "SCHOOL_ESSENTIALS", "School Essentials"
    EVENT_MATERIALS = "EVENT_MATERIALS", "Event Materials"


class InventoryItem(models.Model):
    item_name = models.CharField(max_length=200)
    sku = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stock Keeping Unit / Item Code",
    )
    category = models.CharField(
        max_length=30,
        choices=InventoryCategory.choices,
        default=InventoryCategory.BOOKS,
    )
    unit = models.CharField(
        max_length=50,
        default="Pieces",
        help_text="Unit of measurement (e.g. Pieces, Sets, Packs, Units)",
    )
    current_stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Alert triggered when stock falls at or below this level",
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        null=True,
        blank=True,
    )
    location = models.CharField(
        max_length=150,
        blank=True,
        help_text="Warehouse / Room / Shelf location",
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
        default="ACTIVE",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "item_name"]
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"

    def __str__(self):
        return f"{self.item_name} [{self.get_category_display()}] ({self.sku})"

    @property
    def is_low_stock(self):
        return self.current_stock <= self.low_stock_threshold

    @property
    def stock_status(self):
        if self.current_stock == 0:
            return "OUT_OF_STOCK"
        elif self.current_stock <= self.low_stock_threshold:
            return "LOW_STOCK"
        return "IN_STOCK"


class StockTransaction(models.Model):
    class TransactionType(models.TextChoices):
        STOCK_IN = "STOCK_IN", "Stock In"
        STOCK_OUT = "STOCK_OUT", "Stock Out"
        ADJUSTMENT = "ADJUSTMENT", "Stock Adjustment"

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )
    quantity = models.PositiveIntegerField()
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    source_destination = models.CharField(
        max_length=200,
        blank=True,
        help_text="Supplier/Vendor (for Stock In) or School/Student/Event (for Stock Out)",
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="PO / Invoice / Dispatch Ref / Voucher #",
    )
    performed_by = models.CharField(
        max_length=150,
        blank=True,
    )
    transaction_date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stock Transaction"
        verbose_name_plural = "Stock Transactions"

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()} - {self.item.item_name} "
            f"({self.quantity} {self.item.unit})"
        )


class Laptop(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ISSUED = "ISSUED", "Issued"
        RETURNED = "RETURNED", "Returned"
        DAMAGED = "DAMAGED", "Damaged"
        LOST = "LOST", "Lost"
        RETIRED = "RETIRED", "Retired"

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        DAMAGED = "DAMAGED", "Damaged"

    asset_number = models.CharField(
        max_length=50,
        unique=True,
    )
    serial_number = models.CharField(
        max_length=100,
        unique=True,
    )
    brand = models.CharField(
        max_length=100,
    )
    model_name = models.CharField(
        max_length=100,
    )
    purchase_date = models.DateField(
        null=True,
        blank=True,
    )
    purchase_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    condition = models.CharField(
        max_length=20,
        choices=Condition.choices,
        default=Condition.NEW,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    warranty_expiry = models.DateField(
        null=True,
        blank=True,
    )
    notes = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.asset_number} - {self.brand} {self.model_name} ({self.serial_number})"


class LaptopAssignment(models.Model):
    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Issued"
        RETURNED = "RETURNED", "Returned"
        REPLACED = "REPLACED", "Replaced"

    laptop = models.ForeignKey(
        Laptop,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="laptop_assignments",
    )
    academic_year = models.CharField(
        max_length=20,
    )
    issued_date = models.DateField(
        auto_now_add=True,
    )
    returned_date = models.DateField(
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ISSUED,
    )
    issue_notes = models.TextField(
        blank=True,
    )
    return_notes = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.student.student_name} - "
            f"{self.laptop.asset_number}"
        )
