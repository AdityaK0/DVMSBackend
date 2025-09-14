from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderCreateSerializer
from shared.permissions import IsOwnerOrReadOnly

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by('-created_at')

class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user)

class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

class OrderCancelView(generics.UpdateAPIView):
    permission_classes = [IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user)

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        
        if order.status in ['shipped', 'delivered', 'cancelled']:
            return Response(
                {'error': 'Order cannot be cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restore stock
        for item in order.items.all():
            item.product.stock_quantity += item.quantity
            item.product.save()
        
        order.status = 'cancelled'
        order.save()
        
        return Response({'message': 'Order cancelled successfully'})