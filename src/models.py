"""
Data models for the application.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class OrderStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass
class Address:
    street: str
    city: str
    country: str
    postal_code: str
    state: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "street": self.street,
            "city": self.city,
            "country": self.country,
            "postal_code": self.postal_code,
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Address":
        return cls(
            street=data["street"],
            city=data["city"],
            country=data["country"],
            postal_code=data["postal_code"],
            state=data.get("state"),
        )

    def __str__(self) -> str:
        parts = [self.street, self.city]
        if self.state:
            parts.append(self.state)
        parts.append(self.postal_code)
        parts.append(self.country)
        return ", ".join(parts)


@dataclass
class Product:
    id: str
    name: str
    price: float
    stock: int
    category: str
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def is_available(self) -> bool:
        return self.stock > 0

    def apply_discount(self, percent: float) -> float:
        if percent < 0 or percent > 100:
            raise ValueError(f"Discount percent must be between 0 and 100, got {percent}")
        return self.price * (1 - percent / 100)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "stock": self.stock,
            "category": self.category,
            "description": self.description,
            "tags": self.tags,
        }


@dataclass
class OrderItem:
    product: Product
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.unit_price * self.quantity

    def to_dict(self) -> dict:
        return {
            "product_id": self.product.id,
            "product_name": self.product.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
        }


@dataclass
class Order:
    id: str
    customer_id: str
    items: List[OrderItem]
    shipping_address: Address
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self.items)

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    def can_cancel(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.PROCESSING)

    def cancel(self) -> None:
        if not self.can_cancel():
            raise ValueError(
                f"Cannot cancel order with status '{self.status.value}'"
            )
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def ship(self) -> None:
        if self.status != OrderStatus.PROCESSING:
            raise ValueError(
                f"Can only ship orders in PROCESSING status, current: '{self.status.value}'"
            )
        self.status = OrderStatus.SHIPPED
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "items": [item.to_dict() for item in self.items],
            "shipping_address": self.shipping_address.to_dict(),
            "status": self.status.value,
            "total": self.total,
            "item_count": self.item_count,
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
        }
