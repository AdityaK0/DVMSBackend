from rest_framework import serializers
from .models import Invoice, InvoiceChangeLog, InvoicePayment, Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone', 'is_active', 'created_at']
        read_only_fields = ['registered_at']



from rest_framework import serializers
class InvoicePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoicePayment
        fields = ["id", "amount", "note", "created_at"]
        read_only_fields = ["created_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    payments = InvoicePaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "customer_name",
            "customer_phone",
            "items",
            "total_amount",
            "paid_amount",
            "pending_amount",
            "is_udhaari",
            "invoice_date",
            "is_locked",
            "is_edited",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "is_locked", "paid_amount", "pending_amount"]

    def validate(self, data):
        """
        Enforce consistency:
        1. Recalculate total_amount from items.
        2. Validate price/qty.
        3. Compute pending_amount based on total, paid, and is_udhaari.
        """
        # Handle partial updates: fallback to instance data if field missing
        items = data.get("items")
        if items is None and self.instance:
            items = self.instance.items
        
        # If items is still None (e.g. create without items), default to empty list
        items = items or []

        # If locked, prevent item changes
        if self.instance and self.instance.is_locked:
            # If items are being sent and they are different, raise error
            # For simplicity, we just ignore the input items if locked and use instance items
            # But strictly speaking we should probably raise an error if they try to change it.
            # However, the requirement says "Do NOT allow changes to items". 
            # We will enforce this by not allowing 'items' to be updated if locked.
            if "items" in data:
                 # If user tries to change items on locked invoice, ignore it or error.
                 # Let's ignore it to be safe and just use existing items.
                 items = self.instance.items
                 data["items"] = items

        if not items:
             # For create, we require items. For update, if we ended up with no items, that's an issue.
             raise serializers.ValidationError({"items": "At least one item is required."})

        calculated_total = 0.0
        validated_items = []

        for item in items:
            # item might be a dict or OrderedDict
            name = item.get("name", "").strip()
            try:
                price = float(item.get("price", 0))
                qty = float(item.get("qty", 1))
            except (ValueError, TypeError):
                raise serializers.ValidationError({"items": "Price and Quantity must be valid numbers."})

            if not name:
                raise serializers.ValidationError({"items": "Item name is required."})
            if price < 0:
                raise serializers.ValidationError({"items": f"Price for '{name}' cannot be negative."})
            if qty < 1:
                raise serializers.ValidationError({"items": f"Quantity for '{name}' must be at least 1."})

            total = price * qty
            calculated_total += total
            
            validated_items.append({
                "name": name,
                "price": price,
                "qty": qty,
                "total": total
            })

        # Always override items and total_amount
        data["items"] = validated_items
        data["total_amount"] = calculated_total

        # Paid Amount - managed via payments now, but for create we might accept initial paid
        # For update, paid_amount is read-only (managed by payments)
        if self.instance:
            paid_amount = self.instance.paid_amount
        else:
            paid_amount = float(data.get("paid_amount", 0))
        
        if paid_amount < 0:
            raise serializers.ValidationError({"paid_amount": "Paid amount cannot be negative."})
        
        # Ensure paid doesn't exceed total (basic check, though payments API will enforce stricter)
        if paid_amount > calculated_total:
             # On create, clamp it? Or error? Requirement says "paid_amount cannot exceed total_amount"
             # Let's error to be clear
             raise serializers.ValidationError({"paid_amount": "Paid amount cannot exceed Total amount."})

        data["paid_amount"] = paid_amount

        # Udhaari Status
        is_udhaari = data.get("is_udhaari")
        if is_udhaari is None and self.instance:
            is_udhaari = self.instance.is_udhaari
        # Default to False if not found anywhere (e.g. create)
        if is_udhaari is None:
            is_udhaari = False

        # Compute Pending Amount
        if not is_udhaari:
            data["pending_amount"] = 0.0
        else:
            pending = calculated_total - paid_amount
            data["pending_amount"] = max(pending, 0.0)

        return data


class InvoiceChangeLogSerializer(serializers.ModelSerializer):
    changed_by = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceChangeLog
        fields = ["id", "change_type", "changes", "created_at", "changed_by"]

    def get_changed_by(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.username
        return None

