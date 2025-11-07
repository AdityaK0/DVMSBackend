# marketplace/apps/subscriptions/views.py
import json
import decimal
import logging
import razorpay
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import Subscription
from .serializers import SubscriptionSerializer

logger = logging.getLogger(__name__)

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    Create a Razorpay order and record it in Subscription.
    Prevents duplicate active subscriptions.
    """
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor profile not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Prevent duplicate active subs
        active_sub = Subscription.objects.filter(
            vendor=vendor, is_active=True, end_date__gt=timezone.now()
        ).first()
        if active_sub:
            return Response(
                {
                    "detail": "You already have an active subscription.",
                    "subscription": SubscriptionSerializer(active_sub).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Safe amount extraction
        rupee_amount = decimal.Decimal(request.data.get("amount", "1"))
        amount_paise = int(rupee_amount * 100)

        # Create order with Razorpay
        order = client.order.create(
            {"amount": amount_paise, "currency": "INR", "payment_capture": 1}
        )

        sub, _ = Subscription.objects.update_or_create(
            vendor=vendor,
            defaults={
                "order_id": order.get("id"),
                "amount": rupee_amount,
                "is_active": False,
                "start_date": timezone.now(),
                "end_date": timezone.now() + timezone.timedelta(days=30),
            },
        )

        return Response(
            {
                "order_id": order.get("id"),
                "razorpay_key": settings.RAZORPAY_KEY_ID,
                "amount": amount_paise,
            },
            status=status.HTTP_200_OK,
        )

    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay API error: {str(e)}")
        return Response(
            {"detail": "Error creating order.", "error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.exception("Unexpected error in create_order")
        return Response(
            {"detail": "Something went wrong."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """
    Verify Razorpay payment and activate subscription.
    """
    data = request.data
    payment_id = data.get("payment_id")
    order_id = data.get("order_id")
    signature = data.get("signature")

    if not all([payment_id, order_id, signature]):
        return Response(
            {"detail": "Missing payment verification fields."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Verify signature integrity
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }
        )
    except razorpay.errors.SignatureVerificationError as e:
        logger.warning(f"Payment signature failed: {str(e)}")
        return Response(
            {"detail": "Signature verification failed.", "error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    sub = Subscription.objects.filter(vendor=vendor, order_id=order_id).first()

    if not sub:
        # Safe fallback if order record missing
        sub = Subscription.objects.create(
            vendor=vendor,
            order_id=order_id,
            payment_id=payment_id,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=30),
            is_active=True,
            amount=decimal.Decimal(data.get("amount", "1")),
        )
    else:
        sub.payment_id = payment_id
        sub.start_date = timezone.now()
        sub.end_date = timezone.now() + timezone.timedelta(days=30)
        sub.is_active = True
        sub.save()

    logger.info(f"Subscription activated for vendor {vendor.id}")

    return Response(
        {"detail": "Subscription activated.", "subscription": SubscriptionSerializer(sub).data},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    """
    Returns current vendor subscription. Deactivates if expired.
    """
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

    sub = getattr(vendor, "subscription", None)
    if not sub:
        return Response({"subscription": None}, status=status.HTTP_200_OK)

    # Auto deactivate expired subs
    if sub.end_date and sub.end_date < timezone.now() and sub.is_active:
        sub.is_active = False
        sub.save(update_fields=["is_active"])

    return Response({"subscription": SubscriptionSerializer(sub).data}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])  # public webhook
def razorpay_webhook(request):
    """
    Razorpay Webhook for production.
    """
    try:
        payload = request.body
        signature = request.headers.get("X-Razorpay-Signature")
        secret = settings.RAZORPAY_WEBHOOK_SECRET

        # verify webhook signature
        client.utility.verify_webhook_signature(payload, signature, secret)
        event = json.loads(payload)

        if event.get("event") == "payment.captured":
            payment = event["payload"]["payment"]["entity"]
            order_id = payment.get("order_id")
            payment_id = payment.get("id")

            sub = Subscription.objects.filter(order_id=order_id).first()
            if sub:
                sub.payment_id = payment_id
                sub.start_date = timezone.now()
                sub.end_date = timezone.now() + timezone.timedelta(days=30)
                sub.is_active = True
                sub.save()
                logger.info(f"Webhook activated subscription for vendor {sub.vendor_id}")

        return Response({"status": "success"}, status=status.HTTP_200_OK)

    except razorpay.errors.SignatureVerificationError as e:
        logger.warning(f"Invalid Razorpay webhook signature: {str(e)}")
        return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Webhook processing error")
        return Response(
            {"error": "Webhook processing failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# # marketplace/apps/subscriptions/views.py
# import razorpay
# from django.conf import settings
# from django.utils import timezone
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework import status
# from .models import Subscription
# from .serializers import SubscriptionSerializer
# from django.views.decorators.csrf import csrf_exempt


# client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def create_order(request):
#     """
#     Create Razorpay order and save order_id in Subscription (create if not exists).
#     """
#     vendor = getattr(request.user, "vendor", None)
#     if not vendor:
#         return Response({"detail": "Vendor profile not found."}, status=status.HTTP_400_BAD_REQUEST)

#     # Amount in rupees; we store integer rupees. Convert to paise
#     rupee_amount = float(request.data.get("amount", 1))
#     amount_paise = int(rupee_amount * 100)

#     order = client.order.create({
#         "amount": amount_paise,
#         "currency": "INR",
#         "payment_capture": 1
#     })

#     sub, _ = Subscription.objects.update_or_create(
#         vendor=vendor,
#         defaults={
#             "order_id": order.get("id"),
#             "amount": rupee_amount,
#             "is_active": False,
#             "start_date": timezone.now()
#         }
#     )

#     return Response({
#         "order_id": order.get("id"),
#         "razorpay_key": settings.RAZORPAY_KEY_ID,
#         "amount": amount_paise
#     })


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def verify_payment(request):
#     """
#     Verify payment signature returned by Razorpay popup and activate subscription.
#     Payload: { payment_id, order_id, signature }
#     """
#     data = request.data
#     payment_id = data.get("payment_id")
#     order_id = data.get("order_id")
#     signature = data.get("signature")

#     if not all([payment_id, order_id, signature]):
#         return Response({"detail": "Missing payment verification fields."}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         # verifies signature - raises SignatureVerificationError on invalid
#         client.utility.verify_payment_signature({
#             "razorpay_order_id": order_id,
#             "razorpay_payment_id": payment_id,
#             "razorpay_signature": signature
#         })
#     except Exception as e:
#         return Response({"detail": "Signature verification failed.", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

#     vendor = getattr(request.user, "vendor", None)
#     if not vendor:
#         return Response({"detail": "Vendor not found."}, status=status.HTTP_400_BAD_REQUEST)

#     sub = Subscription.objects.filter(vendor=vendor, order_id=order_id).first()
#     if not sub:
#         # create record if not present
#         sub = Subscription.objects.create(
#             vendor=vendor,
#             order_id=order_id,
#             payment_id=payment_id,
#             start_date=timezone.now(),
#             end_date=timezone.now() + timezone.timedelta(days=30),
#             is_active=True,
#             amount=sub.amount if sub else float(request.data.get("amount", 1))
#         )
#     else:
#         sub.payment_id = payment_id
#         sub.start_date = timezone.now()
#         sub.end_date = timezone.now() + timezone.timedelta(days=30)
#         sub.is_active = True
#         sub.save()

#     return Response({"detail": "Subscription activated.", "subscription": SubscriptionSerializer(sub).data}, status=status.HTTP_200_OK)


# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def subscription_status(request):
#     vendor = getattr(request.user, "vendor", None)
#     if not vendor:
#         return Response({"detail": "Vendor not found."}, status=status.HTTP_400_BAD_REQUEST)
#     sub = getattr(vendor, "subscription", None)
#     if not sub:
#         return Response({"subscription": None})
#     return Response({"subscription": SubscriptionSerializer(sub).data})



# @api_view(['POST'])
# @permission_classes([])  # public endpoint
# @csrf_exempt
# def razorpay_webhook(request):
#     payload = request.body
#     signature = request.headers.get('X-Razorpay-Signature')
#     secret = settings.RAZORPAY_WEBHOOK_SECRET

#     try:
#         client.utility.verify_webhook_signature(payload, signature, secret)
#     except razorpay.errors.SignatureVerificationError:
#         return Response({"error": "Invalid signature"}, status=400)

#     event = json.loads(payload)
#     if event.get("event") == "payment.captured":
#         payment = event["payload"]["payment"]["entity"]
#         order_id = payment["order_id"]
#         payment_id = payment["id"]

#         sub = Subscription.objects.filter(order_id=order_id).first()
#         if sub:
#             sub.payment_id = payment_id
#             sub.is_active = True
#             sub.start_date = timezone.now()
#             sub.end_date = timezone.now() + timezone.timedelta(days=30)
#             sub.save()

#     return Response({"status": "success"})
