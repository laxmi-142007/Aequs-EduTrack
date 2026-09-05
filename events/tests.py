from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from inventory.models import InventoryItem, StockTransaction, InventoryCategory
from events.models import Event

User = get_user_model()


class EventInventoryRequestTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="testadmin",
            email="admin@example.com",
            password="password123",
            role="ADMIN",
        )
        self.client.force_login(self.user)
        self.item = InventoryItem.objects.create(
            item_name="Event Banners",
            sku="EVT-BAN-01",
            category=InventoryCategory.EVENT_MATERIALS,
            current_stock=50,
            unit="Pieces",
        )

    def test_event_creation_with_inventory_request(self):
        url = reverse("events:create")
        data = {
            "title": "Annual Science Fair",
            "description": "Science exhibition for partner schools",
            "event_date": "2026-10-15",
            "location": "Main Auditorium",
            "organizer": "Education Team",
            "inventory_item": self.item.pk,
            "inventory_quantity": 5,
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Check event saved with requested resource
        event = Event.objects.get(title="Annual Science Fair")
        self.assertEqual(event.requested_item, self.item)
        self.assertEqual(event.requested_quantity, 5)

        # Check inventory stock updated
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_stock, 45)

        # Check StockTransaction recorded
        tx = StockTransaction.objects.filter(item=self.item).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.transaction_type, StockTransaction.TransactionType.STOCK_OUT)
        self.assertEqual(tx.quantity, 5)
        self.assertEqual(tx.previous_stock, 50)
        self.assertEqual(tx.new_stock, 45)
        self.assertIn("Annual Science Fair", tx.source_destination)
