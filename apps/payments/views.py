from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from .models import Payment, PaymentRefund
from .serializers import PaymentSerializer, PaymentCreateSerializer, PaymentRefundSerializer
from shared.permissions import IsOwnerOrReadOnly

class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(order__customer=self.request.user).order_by('-created_at')

class PaymentDetailView(generics.RetrieveAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_queryset(self):
        return Payment.objects.filter(order__customer=self.request.user)

class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Simulate payment processing
        payment = serializer.save()
        
        # In a real implementation, you would integrate with a payment gateway here
        # For now, we'll simulate a successful payment
        if payment.payment_method == 'cash_on_delivery':
            payment.status = 'pending'
        else:
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.transaction_id = f"TXN_{payment.id}_{timezone.now().timestamp()}"
        
        payment.save()
        
        # Update order status
        order = payment.order
        if payment.status == 'completed':
            order.status = 'confirmed'
            order.save()
        
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)