from core.services.uploads import UploadService

def upload_portfolio_banner(portfolio, file):
    service = UploadService()
    upload_record = service.upload(file, folder=f"portfolio/{portfolio.id}/banner/", link_to=portfolio)
    portfolio.banner_image = upload_record.url
    portfolio.save(update_fields=["banner_image"])
    return upload_record

def upload_portfolio_carousel(portfolio, files):
    service = UploadService()
    uploaded_urls = []
    for file in files:
        upload_record = service.upload(file, folder=f"portfolio/{portfolio.id}/carousel/", link_to=portfolio)
        uploaded_urls.append(upload_record.url)
    return uploaded_urls



def upload_collection_image(collection, file):
    service = UploadService()
    upload_record = service.upload(file, folder=f"collections/{collection.id}/", link_to=collection)
    collection.cover_image = upload_record.url
    collection.save(update_fields=["cover_image"])
    return upload_record