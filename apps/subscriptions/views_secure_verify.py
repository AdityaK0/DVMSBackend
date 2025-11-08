# This file contains the SECURE version of verify_payment with all attack protections
# Replace the verify_payment function in views.py with this implementation

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
            payment_txn = PaymentTransaction.objects.select_for_update().select_related('plan', 'vendor').get(
                razorpay_order_id=order_id,
                vendor=vendor  # ✅ CRITICAL: Vendor ownership check
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
