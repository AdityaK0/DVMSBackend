# apps/portfolio/services.py
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from apps.portfolio.models import Portfolio, PortfolioCollection
from apps.portfolio.serializers import PortfolioCollectionSerializer
from apps.utils.upload_image import upload_collection_image


def get_vendor_collections(vendor):
    """
    Fetch all collections for a vendor's portfolio.
    """
    collections = PortfolioCollection.objects.filter(
        portfolio__vendor=vendor
    ).order_by('order', 'name')
    
    serializer = PortfolioCollectionSerializer(collections, many=True)
    return serializer.data


def create_vendor_collection(vendor, data, files=None):
    """
    Create a new portfolio collection for a vendor.
    Handles image upload if provided.
    """
    portfolio = get_object_or_404(Portfolio, vendor=vendor)

    serializer = PortfolioCollectionSerializer(data=data)
    if serializer.is_valid():
        collection = serializer.save(portfolio=portfolio)

        # Handle optional image upload
        image_file = None
        if files:
            image_file = files.get('image')
        if image_file:
            upload_collection_image(collection, image_file)

        response_serializer = PortfolioCollectionSerializer(collection)
        return {
            "data": response_serializer.data,
            "status": status.HTTP_201_CREATED
        }
    else:
        return {
            "data": serializer.errors,
            "status": status.HTTP_400_BAD_REQUEST
        }
