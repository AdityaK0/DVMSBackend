# core/handlers/vendor.py

class VendorUpdatedSubscriber:
    queue = "vendor"

    def __call__(self, event):
        print("Trigger webhook for vendor:", event.vendor_id)
