services.uploads import UploadService

def upload_vendor_logo(vendor, file):
    service = UploadService()
    upload_record = service.upload(file, folder=f"vendors/{vendor.id}/logo/", link_to=vendor)
    vendor.logo = upload_record.url
    vendor.save(update_fields=["logo"])
    return upload_record
