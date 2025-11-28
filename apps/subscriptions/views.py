# marketplace/apps/subscriptions/views.py
import json
import decimal
import logging
from typing import Optional
import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import Subscription, SubscriptionPlan, PaymentTransaction
from .serializers import SubscriptionSerializer, SubscriptionPlanSerializer, PaymentTransactionSerializer
from .services import SubscriptionService
from apps.core.authentication import get_request_vendor
logger = logging.getLogger(__name__)


# Elasticsearch sync helper
def sync_vendor_to_elasticsearch(vendor):
    """
    Sync vendor data to Elasticsearch after successful subscription.
    This updates the vendor's subscription status in ES for FastAPI access.
    """
    try:
        from elasticsearch import Elasticsearch
        from elasticsearch.helpers import bulk
        
        # Connect to Elasticsearch
        es = Elasticsearch("http://localhost:9205")
        
        # Update vendor document with subscription status
        vendor_doc = {
            "_index": "vendor_index",
            "_id": vendor.id,
            "_op_type": "update",
            "doc": {
                "is_subscribed": True,
                "subscription_active": True,
                "last_sync": timezone.now().isoformat(),
            },
            "doc_as_upsert": True
        }
        
        # Execute bulk update
        bulk(es, [vendor_doc])
        logger.info(f"Elasticsearch sync completed for vendor {vendor.id}")
        
    except ImportError:
        logger.warning("Elasticsearch not installed. Skipping ES sync.")
    except Exception as e:
        logger.error(f"Elasticsearch sync error: {str(e)}")
        raise


# FIXED: Lazily initialize Razorpay client with error handling to avoid import-time crashes
def get_razorpay_client() -> Optional[razorpay.Client]:
    try:
        key_id = getattr(settings, "RAZORPAY_KEY_ID", None)
        key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", None)
        if not key_id or not key_secret:
            logger.error("Razorpay keys missing in settings")
            return None
        return razorpay.Client(auth=(key_id, key_secret))
    except Exception as exc:
        logger.exception("Failed to initialize Razorpay client: %s", exc)
        return None


# FIXED: Shared helpers for consistent responses and vendor fetching
def error_response(detail: str, http_status: int = status.HTTP_400_BAD_REQUEST, extra: Optional[dict] = None):
    payload = {"detail": detail}
    if extra:
        payload.update(extra)
    return Response(payload, status=http_status)


def get_request_vendor_or_404(request):
    vendor = getattr(request.user, "vendor", None)
    if not vendor:
        raise_value = error_response("Vendor profile not found.", status.HTTP_404_NOT_FOUND)
        return None, raise_value
    return vendor, None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_order(request):
    """
    🔒 SECURE: Create a Razorpay order WITHOUT activating subscription.
    Only creates PaymentTransaction with status='created'.
    Subscription is activated ONLY after payment verification.
    """
    vendor, err = get_request_vendor_or_404(request)
    if err:
        return err

    try:
        # Check for existing active subscription
        active_sub = Subscription.objects.filter(
            vendor=vendor, 
            is_active=True, 
            end_date__gt=timezone.now()
        ).first()
        
        if active_sub:
            return Response(
                {
                    "detail": "You already have an active subscription.",
                    "subscription": SubscriptionSerializer(active_sub).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get plan_id from request
        plan_id = request.data.get('plan_id')
        if not plan_id:
            return error_response("plan_id is required.", status.HTTP_400_BAD_REQUEST)
        
        # Fetch subscription plan
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return error_response("Invalid or inactive subscription plan.", status.HTTP_404_NOT_FOUND)
        
        amount_paise = plan.price_in_paise

        # Create Razorpay order
        client = get_razorpay_client()
        if client is None:
            return error_response("Payment gateway not configured.", status.HTTP_500_INTERNAL_SERVER_ERROR)

        razorpay_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'payment_capture': 1,  # Auto-capture after authorization
            'notes': {
                'vendor_id': vendor.id,
                'plan_id': plan.id,
                'plan_name': plan.name,
            }
        })

        # 🔒 SECURITY: Create PaymentTransaction, NOT Subscription
        with transaction.atomic():
            payment_txn = PaymentTransaction.objects.create(
                vendor=vendor,
                plan=plan,
                razorpay_order_id=razorpay_order['id'],
                amount=amount_paise,
                currency='INR',
                status='created',
                razorpay_response=razorpay_order
            )
        
        logger.info(f"Order created for vendor {vendor.id}: {razorpay_order['id']}")

        return Response(
            {
                "order_id": razorpay_order['id'],
                "amount": amount_paise,
                "currency": "INR",
                "key": settings.RAZORPAY_KEY_ID,
                "plan": SubscriptionPlanSerializer(plan).data,
                "transaction_id": payment_txn.id,
            },
            status=status.HTTP_201_CREATED,
        )

    except razorpay.errors.BadRequestError as e:
        logger.error(f"Razorpay API error: {str(e)}")
        return error_response("Error creating order with payment gateway.", status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Unexpected error in create_order")
        return error_response("Internal server error. Please try again.", status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    
    """
    🔐 SECURE: Verify Razorpay payment signature and activate subscription.
    
    Security Features:
    - Replay attack prevention (payment_id/signature uniqueness check)
    - Race condition protection (select_for_update locking)
    - Amount tampering detection (cross-verify with Razorpay API)
    - Vendor ownership validation (prevent cross-vendor attacks)
    - JWT claim validation (prevent token manipulation)
    """
    data = request.data
    payment_id = data.get("razorpay_payment_id") or data.get("payment_id")
    order_id = data.get("razorpay_order_id") or data.get("order_id")
    signature = data.get("razorpay_signature") or data.get("signature")

    if not all([payment_id, order_id, signature]):
        return error_response(
            "Missing payment verification fields (payment_id, order_id, signature).",
            status.HTTP_400_BAD_REQUEST
        )

    vendor, err = get_request_vendor_or_404(request)
    if err:
        return err

    # ✅ SECURITY CHECK 1: Replay Attack Prevention - Check if payment_id already used
    if PaymentTransaction.objects.filter(razorpay_payment_id=payment_id).exclude(razorpay_order_id=order_id).exists():
        logger.error(f"🚨 REPLAY ATTACK DETECTED: payment_id {payment_id} already used for different order")
        return error_response(
            "This payment ID has already been used. Contact support if this is an error.",
            status.HTTP_400_BAD_REQUEST
        )
    
    # ✅ SECURITY CHECK 2: Signature Replay Prevention - Check if signature already used
    if PaymentTransaction.objects.filter(razorpay_signature=signature).exclude(razorpay_order_id=order_id).exists():
        logger.error(f"🚨 SIGNATURE REPLAY DETECTED: signature reused for different order")
        return error_response(
            "Invalid payment signature. Possible replay attack detected.",
            status.HTTP_400_BAD_REQUEST
        )

    # ✅ SECURITY CHECK 3: Verify Razorpay signature (cryptographic proof)
    try:
        client = get_razorpay_client()
        if client is None:
            return error_response("Payment gateway not configured.", status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        logger.info(f"✅ Payment signature verified for order {order_id}")
        
    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"❌ Payment signature verification failed for order {order_id}: {str(e)}")
        return error_response(
            "Payment signature verification failed. This payment cannot be trusted.",
            status.HTTP_400_BAD_REQUEST,
            {"error": str(e)}
        )

    # ✅ SECURITY CHECK 4: Race Condition Protection - Use database-level locking
    try:
        with transaction.atomic():
            # Lock the payment transaction row to prevent concurrent processing
            # payment_txn = PaymentTransaction.objects.select_for_update().select_related('plan', 'vendor').get(
            #     razorpay_order_id=order_id,
            #     vendor=vendor  # ✅ CRITICAL: Vendor ownership check
            # )
            
            
            payment_txn = PaymentTransaction.objects.select_for_update().get(
                    razorpay_order_id=order_id,
                    vendor=vendor,
                )
            
            # ✅ SECURITY CHECK 5: Additional vendor ownership validation
            if payment_txn.vendor.id != vendor.id:
                logger.error(
                    f"🚨 OWNERSHIP VIOLATION: User {request.user.id} (vendor {vendor.id}) "
                    f"tried to verify payment for vendor {payment_txn.vendor.id}"
                )
                return error_response(
                    "You are not authorized to verify this payment.",
                    status.HTTP_403_FORBIDDEN
                )
            
            # ✅ SECURITY CHECK 6: JWT claim validation
            if hasattr(request.auth, 'payload'):
                token_vendor_id = request.auth.payload.get('vendor_id')
                if token_vendor_id and token_vendor_id != vendor.id:
                    logger.error(
                        f"🚨 JWT CLAIM MISMATCH: Token claims vendor {token_vendor_id} "
                        f"but user has vendor {vendor.id}"
                    )
                    return error_response(
                        "Authentication error. Please login again.",
                        status.HTTP_401_UNAUTHORIZED
                    )
            
            # Double-check status within the locked transaction (idempotency)
            if payment_txn.status in ['captured', 'authorized']:
                logger.warning(f"⚠️ Race condition prevented: payment already processed")
                existing_sub = Subscription.objects.filter(vendor=vendor).first()
                return Response({
                    "detail": "Payment already processed.",
                    "subscription": SubscriptionSerializer(existing_sub).data if existing_sub else None,
                }, status=status.HTTP_200_OK)
            
            # Mark as processing immediately to prevent concurrent updates
            payment_txn.status = 'processing'
            payment_txn.save(update_fields=['status'])
            
    except PaymentTransaction.DoesNotExist:
        logger.error(
            f"🚨 CROSS-VENDOR ATTACK ATTEMPT: User {request.user.id} tried to access "
            f"order {order_id} which doesn't exist or doesn't belong to them"
        )
        return error_response(
            "Payment transaction not found or unauthorized.",
            status.HTTP_404_NOT_FOUND
        )

    # ✅ SECURITY CHECK 7: Amount Tampering Detection - Verify actual amount paid
    try:
        client = get_razorpay_client()
        if client:
            razorpay_payment = client.payment.fetch(payment_id)
            actual_amount_paid = razorpay_payment['amount']  # in paise
            expected_amount = payment_txn.amount  # from our transaction
            
            if actual_amount_paid != expected_amount:
                logger.error(
                    f"🚨 AMOUNT TAMPERING DETECTED: "
                    f"Expected {expected_amount} paise, but {actual_amount_paid} paise paid"
                )
                # Rollback transaction
                with transaction.atomic():
                    payment_txn = PaymentTransaction.objects.select_for_update().get(id=payment_txn.id)
                    payment_txn.status = 'failed'
                    payment_txn.error_message = f"Amount mismatch: expected {expected_amount}, got {actual_amount_paid}"
                    payment_txn.save()
                
                return error_response(
                    "Payment amount does not match plan price. Transaction rejected.",
                    status.HTTP_400_BAD_REQUEST,
                    {"expected": expected_amount, "received": actual_amount_paid}
                )
            
            logger.info(f"✅ Amount verification passed: {actual_amount_paid} paise")
            
    except razorpay.errors.BadRequestError as e:
        logger.error(f"Failed to fetch payment details from Razorpay: {str(e)}")
        # Rollback
        with transaction.atomic():
            payment_txn = PaymentTransaction.objects.select_for_update().get(id=payment_txn.id)
            payment_txn.status = 'failed'
            payment_txn.error_message = f"Could not verify payment: {str(e)}"
            payment_txn.save()
        return error_response("Could not verify payment details", status.HTTP_400_BAD_REQUEST)

    # ✅ STEP 8: Activate subscription in atomic transaction
    try:
        with transaction.atomic():
            payment_txn = PaymentTransaction.objects.select_for_update().get(id=payment_txn.id)
            payment_txn.razorpay_payment_id = payment_id
            payment_txn.razorpay_signature = signature
            payment_txn.status = 'captured'
            payment_txn.verified_at = timezone.now()
            payment_txn.save()
            
            # Create or update subscription (use get_or_create for idempotency)
            plan = payment_txn.plan
            start_date = timezone.now()
            end_date = start_date + timezone.timedelta(days=plan.duration_days)
            
            sub, created = Subscription.objects.get_or_create(
                vendor=vendor,
                defaults={
                    'plan': plan,
                    'transaction': payment_txn,
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_active': True,
                    'amount': decimal.Decimal(payment_txn.amount) / 100,
                    'order_id': order_id,
                    'payment_id': payment_id,
                }
            )
            
            # If subscription already existed, update it
            if not created:
                sub.plan = plan
                sub.transaction = payment_txn
                sub.end_date = end_date
                sub.is_active = True
                sub.amount = decimal.Decimal(payment_txn.amount) / 100
                sub.save()
            
            logger.info(f"✅ Subscription {'created' if created else 'updated'} for vendor {vendor.id}")
            
            # Sync to Elasticsearch (non-critical, don't fail if it errors)
            try:
                sync_vendor_to_elasticsearch(vendor)
                logger.info(f"✅ Vendor {vendor.id} synced to Elasticsearch")
            except Exception as es_error:
                logger.error(f"⚠️ Elasticsearch sync failed for vendor {vendor.id}: {str(es_error)}")
                # Don't fail the payment - ES sync is secondary
            
            return Response({
                "success": True,
                "detail": f"Payment verified and subscription {'created' if created else 'updated'} successfully.",
                "subscription": SubscriptionSerializer(sub).data,
                "transaction": PaymentTransactionSerializer(payment_txn).data,
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.exception(f"❌ Error activating subscription for vendor {vendor.id}")
        # Mark transaction as failed
        try:
            payment_txn.mark_as_failed(str(e))
        except:
            pass
        return error_response(
            "Failed to activate subscription. Please contact support.",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_plans(request):
    """
    List all available subscription plans.
    """
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response({"plans": serializer.data}, status=status.HTTP_200_OK)


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def subscription_status(request):
#     """
#     Returns current vendor subscription. Deactivates if expired.
#     """
#     vendor, err = get_request_vendor_or_404(request)
#     if err:
#         return err

#     sub = getattr(vendor, "subscription", None)
#     if not sub:
#         return Response({"subscription": None}, status=status.HTTP_200_OK)

#     # Auto deactivate expired subs
#     if sub.end_date and sub.end_date < timezone.now() and sub.is_active:
#         # FIXED: Use minimal write and update_fields for efficiency
#         sub.is_active = False
#         sub.save(update_fields=["is_active"])

#     return Response({"subscription": SubscriptionSerializer(sub).data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription_status(request):
    """
    Returns current vendor subscription. Deactivates if expired.
    """
    vendor_id = get_request_vendor(request)

    if not vendor_id:
        return Response({"subscription": None}, status=200)



    sub = SubscriptionService.get_vendor_subscription(vendor_id)

    if not sub:
        return Response({"subscription": None}, status=status.HTTP_200_OK)
    
    return Response({"subscription": sub}, status=status.HTTP_200_OK)




@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])  # public webhook
def razorpay_webhook(request):
    """
    🔐 SECURE: Razorpay Webhook Handler for production.
    Handles automatic payment notifications from Razorpay.
    
    Events handled:
    - payment.captured: Activate subscription
    - payment.failed: Mark transaction as failed
    """
    try:
        payload = request.body
        signature = request.headers.get("X-Razorpay-Signature")
        webhook_secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)

        if not webhook_secret:
            logger.error("RAZORPAY_WEBHOOK_SECRET not configured")
            return Response({"status": "error", "message": "Webhook not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 🔐 Verify webhook signature
        client = get_razorpay_client()
        if client is None:
            return Response({"status": "error", "message": "Payment gateway not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        client.utility.verify_webhook_signature(payload.decode('utf-8'), signature, webhook_secret)
        event = json.loads(payload)
        
        event_type = event.get("event")
        logger.info(f"📥 Webhook received: {event_type}")
        print("++"*30,event)

        # Handle payment.captured event
        if event_type == "payment.captured":
            payment = event["payload"]["payment"]["entity"]
            order_id = payment.get("order_id")
            payment_id = payment.get("id")
            
            # Find transaction
            try:
                payment_txn = PaymentTransaction.objects.select_related('plan', 'vendor').get(
                    razorpay_order_id=order_id
                )
            except PaymentTransaction.DoesNotExist:
                logger.warning(f"⚠️ PaymentTransaction not found for order {order_id}")
                return Response({"status": "ignored", "message": "Transaction not found"}, status=status.HTTP_200_OK)
            
            # Idempotency check
            if payment_txn.status == 'captured':
                logger.info(f"⚠️ Webhook replay ignored for order {order_id}")
                return Response({"status": "success", "message": "Already processed"}, status=status.HTTP_200_OK)
            
            # Activate subscription
            with transaction.atomic():
                # Extract signature from payment metadata (if available)
                signature_from_webhook = payment.get("signature", "")
                payment_txn.mark_as_captured(payment_id, signature_from_webhook)
                
                # Get plan from transaction
                plan = payment_txn.plan
                vendor = payment_txn.vendor
                start_date = timezone.now()
                duration = plan.duration_days if plan else 30
                end_date = start_date + timezone.timedelta(days=duration)
                
                # Create or update subscription
                sub, created = Subscription.objects.update_or_create(
                    vendor=vendor,
                    defaults={
                        'plan': plan,
                        'transaction': payment_txn,
                        'start_date': start_date,
                        'end_date': end_date,
                        'is_active': True,
                        'after_webhook_called':True,
                        'amount': decimal.Decimal(payment_txn.amount) / 100,
                        'order_id': order_id,
                        'payment_id': payment_id,
                    }
                )
                
                logger.info(f"✅ Webhook activated subscription for vendor {vendor.id}")
                
                # Sync to Elasticsearch
                try:
                    sync_vendor_to_elasticsearch(vendor)
                except Exception as es_error:
                    logger.error(f"⚠️ ES sync failed in webhook: {str(es_error)}")
        
        # Handle payment.failed event
        elif event_type == "payment.failed":
            payment = event["payload"]["payment"]["entity"]
            order_id = payment.get("order_id")
            error_description = payment.get("error_description", "Payment failed")
            
            try:
                payment_txn = PaymentTransaction.objects.get(razorpay_order_id=order_id)
                payment_txn.mark_as_failed(error_description)
                logger.info(f"❌ Payment failed for order {order_id}: {error_description}")
            except PaymentTransaction.DoesNotExist:
                logger.warning(f"⚠️ Transaction not found for failed payment {order_id}")

        return Response({"status": "success"}, status=status.HTTP_200_OK)

    except razorpay.errors.SignatureVerificationError as e:
        logger.error(f"❌ Invalid Razorpay webhook signature: {str(e)}")
        return Response({"status": "error", "message": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("❌ Webhook processing error")
        return Response({"status": "error", "message": "Webhook processing failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
