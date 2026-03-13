"""
Notification system for order and inventory events.
"""
from typing import List, Callable, Dict, Any
from .models import Order, OrderStatus, Product


class NotificationChannel:
    """Abstract notification channel."""

    def send(self, recipient: str, subject: str, body: str) -> bool:
        raise NotImplementedError


class EmailChannel(NotificationChannel):
    """Sends notifications via email (stub)."""

    def __init__(self, smtp_host: str, smtp_port: int = 587):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self._sent: List[dict] = []  # for testing

    def send(self, recipient: str, subject: str, body: str) -> bool:
        # In production this would use smtplib
        self._sent.append({"to": recipient, "subject": subject, "body": body})
        return True

    @property
    def sent_messages(self):
        return list(self._sent)


class SMSChannel(NotificationChannel):
    """Sends notifications via SMS (stub)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._sent: List[dict] = []

    def send(self, recipient: str, subject: str, body: str) -> bool:
        self._sent.append({"to": recipient, "message": body})
        return True


class NotificationService:
    """Dispatches notifications based on order/inventory events."""

    def __init__(self, channel: NotificationChannel):
        self.channel = channel

    def notify_order_placed(self, customer_email: str, order: Order) -> bool:
        subject = f"Order Confirmation #{order.id}"
        body = (
            f"Thank you for your order!\n\n"
            f"Order ID: {order.id}\n"
            f"Items: {order.item_count}\n"
            f"Total: ${order.total:.2f}\n\n"
            f"Shipping to: {order.shipping_address}"
        )
        return self.channel.send(customer_email, subject, body)

    def notify_order_shipped(self, customer_email: str, order: Order) -> bool:
        subject = f"Your order #{order.id} has shipped!"
        body = (
            f"Great news! Your order is on its way.\n\n"
            f"Order ID: {order.id}\n"
            f"Shipping to: {order.shipping_address}\n\n"
            f"Expected delivery: 3-5 business days"
        )
        return self.channel.send(customer_email, subject, body)

    def notify_order_cancelled(self, customer_email: str, order: Order) -> bool:
        subject = f"Order #{order.id} cancelled"
        body = (
            f"Your order has been cancelled.\n\n"
            f"Order ID: {order.id}\n"
            f"Refund of ${order.total:.2f} will be processed within 5-7 business days."
        )
        return self.channel.send(customer_email, subject, body)

    def notify_low_stock(self, admin_email: str, product: Product) -> bool:
        subject = f"Low stock alert: {product.name}"
        body = (
            f"Product is running low on stock.\n\n"
            f"Product: {product.name} (ID: {product.id})\n"
            f"Current stock: {product.stock}\n"
            f"Please reorder soon."
        )
        return self.channel.send(admin_email, subject, body)

    def notify_out_of_stock(self, admin_email: str, product: Product) -> bool:
        subject = f"OUT OF STOCK: {product.name}"
        body = (
            f"URGENT: Product is out of stock!\n\n"
            f"Product: {product.name} (ID: {product.id})\n"
            f"Category: {product.category}\n"
            f"Immediate restocking required."
        )
        return self.channel.send(admin_email, subject, body)
