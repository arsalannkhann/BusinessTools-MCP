"""
Stripe payment processing tool for sales operations
Provides comprehensive payment, customer, and subscription management for sales
"""

import json
import logging
from typing import Dict, Any, Optional, List
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal

import mcp.types as types

from .base import SalesTool, ToolResult, validate_required_params

logger = logging.getLogger(__name__)

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("Stripe library not available. Install with: pip install stripe")

class StripeTool(SalesTool):
    """Stripe payment processing tool for sales operations"""
    
    def __init__(self):
        super().__init__("stripe", "Stripe payment processing and customer management for sales")
        self.api_key = None
        self.publishable_key = None
        self.webhook_secret = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialized = False
    
    async def initialize(self, settings, google_auth=None) -> bool:
        """Initialize Stripe tool"""
        if not STRIPE_AVAILABLE:
            self.logger.error("Stripe library not installed")
            return False
        
        try:
            self.api_key = settings.stripe_api_key
            self.publishable_key = settings.stripe_publishable_key
            self.webhook_secret = getattr(settings, 'stripe_webhook_secret', None)
            
            if not self.api_key:
                self.logger.warning("Stripe API key not configured")
                return False
            
            # Set the API key
            stripe.api_key = self.api_key
            
            # Test connection by fetching account info
            loop = asyncio.get_event_loop()
            account = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Account.retrieve()
            )
            
            account_name = getattr(account, 'display_name', None) or getattr(account, 'business_profile', {}).get('name', None) or account.id
            self.logger.info(f"Stripe connection validated for account: {account_name}")
            self._initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Stripe tool: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if Stripe tool is properly configured"""
        return STRIPE_AVAILABLE and self.api_key is not None
    
    async def execute(self, action: str, params: Dict[str, Any]) -> ToolResult:
        """Execute Stripe action"""
        if not self._initialized:
            return self._create_error_result("Stripe tool not initialized")
        
        try:
            if action == "create_customer":
                return await self._create_customer(params)
            elif action == "get_customer":
                return await self._get_customer(params)
            elif action == "update_customer":
                return await self._update_customer(params)
            elif action == "list_customers":
                return await self._list_customers(params)
            elif action == "create_payment_intent":
                return await self._create_payment_intent(params)
            elif action == "get_payment_intent":
                return await self._get_payment_intent(params)
            elif action == "confirm_payment_intent":
                return await self._confirm_payment_intent(params)
            elif action == "create_subscription":
                return await self._create_subscription(params)
            elif action == "get_subscription":
                return await self._get_subscription(params)
            elif action == "update_subscription":
                return await self._update_subscription(params)
            elif action == "cancel_subscription":
                return await self._cancel_subscription(params)
            elif action == "list_subscriptions":
                return await self._list_subscriptions(params)
            elif action == "create_product":
                return await self._create_product(params)
            elif action == "get_product":
                return await self._get_product(params)
            elif action == "list_products":
                return await self._list_products(params)
            elif action == "create_price":
                return await self._create_price(params)
            elif action == "get_price":
                return await self._get_price(params)
            elif action == "list_prices":
                return await self._list_prices(params)
            elif action == "create_invoice":
                return await self._create_invoice(params)
            elif action == "get_invoice":
                return await self._get_invoice(params)
            elif action == "send_invoice":
                return await self._send_invoice(params)
            elif action == "list_invoices":
                return await self._list_invoices(params)
            elif action == "get_balance":
                return await self._get_balance(params)
            elif action == "list_charges":
                return await self._list_charges(params)
            elif action == "refund_payment":
                return await self._refund_payment(params)
            else:
                return self._create_error_result(f"Unknown action: {action}")
                
        except Exception as e:
            self.logger.error(f"Error executing Stripe action {action}: {e}")
            return self._create_error_result(f"Execution error: {str(e)}")
    
    async def _create_customer(self, params: Dict[str, Any]) -> ToolResult:
        """Create a new Stripe customer"""
        try:
            customer_data = {}
            
            if "email" in params:
                customer_data["email"] = params["email"]
            if "name" in params:
                customer_data["name"] = params["name"]
            if "phone" in params:
                customer_data["phone"] = params["phone"]
            if "description" in params:
                customer_data["description"] = params["description"]
            if "metadata" in params:
                customer_data["metadata"] = params["metadata"]
            if "address" in params:
                customer_data["address"] = params["address"]
            
            loop = asyncio.get_event_loop()
            customer = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Customer.create(**customer_data)
            )
            
            return self._create_success_result({
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created,
                "description": customer.description,
                "metadata": customer.metadata
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to create customer: {str(e)}")
    
    async def _get_customer(self, params: Dict[str, Any]) -> ToolResult:
        """Get customer details"""
        error = validate_required_params(params, ["customer_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            loop = asyncio.get_event_loop()
            customer = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Customer.retrieve(params["customer_id"])
            )
            
            return self._create_success_result({
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "phone": customer.phone,
                "created": customer.created,
                "description": customer.description,
                "metadata": customer.metadata,
                "address": customer.address,
                "balance": customer.balance,
                "currency": customer.currency
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get customer: {str(e)}")
    
    async def _update_customer(self, params: Dict[str, Any]) -> ToolResult:
        """Update customer information"""
        error = validate_required_params(params, ["customer_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            customer_id = params.pop("customer_id")
            
            loop = asyncio.get_event_loop()
            customer = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Customer.modify(customer_id, **params)
            )
            
            return self._create_success_result({
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "updated": True
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to update customer: {str(e)}")
    
    async def _list_customers(self, params: Dict[str, Any]) -> ToolResult:
        """List customers with optional filters"""
        try:
            list_params = {}
            if "limit" in params:
                list_params["limit"] = min(int(params["limit"]), 100)
            if "email" in params:
                list_params["email"] = params["email"]
            if "created" in params:
                list_params["created"] = params["created"]
            
            loop = asyncio.get_event_loop()
            customers = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Customer.list(**list_params)
            )
            
            customer_list = []
            for customer in customers.data:
                customer_list.append({
                    "customer_id": customer.id,
                    "email": customer.email,
                    "name": customer.name,
                    "created": customer.created,
                    "description": customer.description
                })
            
            return self._create_success_result({
                "customers": customer_list,
                "has_more": customers.has_more,
                "total_count": len(customer_list)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list customers: {str(e)}")
    
    async def _create_payment_intent(self, params: Dict[str, Any]) -> ToolResult:
        """Create a payment intent"""
        error = validate_required_params(params, ["amount", "currency"])
        if error:
            return self._create_error_result(error)
        
        try:
            payment_data = {
                "amount": int(params["amount"]),  # Amount in cents
                "currency": params["currency"]
            }
            
            if "customer" in params:
                payment_data["customer"] = params["customer"]
            if "description" in params:
                payment_data["description"] = params["description"]
            if "metadata" in params:
                payment_data["metadata"] = params["metadata"]
            if "payment_method" in params:
                payment_data["payment_method"] = params["payment_method"]
            if "confirm" in params:
                payment_data["confirm"] = params["confirm"]
            if "return_url" in params:
                payment_data["return_url"] = params["return_url"]
            
            loop = asyncio.get_event_loop()
            intent = await loop.run_in_executor(
                self.executor,
                lambda: stripe.PaymentIntent.create(**payment_data)
            )
            
            return self._create_success_result({
                "payment_intent_id": intent.id,
                "amount": intent.amount,
                "currency": intent.currency,
                "status": intent.status,
                "client_secret": intent.client_secret,
                "created": intent.created,
                "description": intent.description
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to create payment intent: {str(e)}")
    
    async def _get_payment_intent(self, params: Dict[str, Any]) -> ToolResult:
        """Get payment intent details"""
        error = validate_required_params(params, ["payment_intent_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            loop = asyncio.get_event_loop()
            intent = await loop.run_in_executor(
                self.executor,
                lambda: stripe.PaymentIntent.retrieve(params["payment_intent_id"])
            )
            
            return self._create_success_result({
                "payment_intent_id": intent.id,
                "amount": intent.amount,
                "currency": intent.currency,
                "status": intent.status,
                "created": intent.created,
                "description": intent.description,
                "customer": intent.customer,
                "metadata": intent.metadata
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get payment intent: {str(e)}")
    
    async def _confirm_payment_intent(self, params: Dict[str, Any]) -> ToolResult:
        """Confirm a payment intent"""
        error = validate_required_params(params, ["payment_intent_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            payment_intent_id = params.pop("payment_intent_id")
            
            loop = asyncio.get_event_loop()
            intent = await loop.run_in_executor(
                self.executor,
                lambda: stripe.PaymentIntent.confirm(payment_intent_id, **params)
            )
            
            return self._create_success_result({
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency,
                "confirmed": True
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to confirm payment intent: {str(e)}")
    
    async def _create_subscription(self, params: Dict[str, Any]) -> ToolResult:
        """Create a subscription"""
        error = validate_required_params(params, ["customer", "items"])
        if error:
            return self._create_error_result(error)
        
        try:
            subscription_data = {
                "customer": params["customer"],
                "items": params["items"]
            }
            
            if "trial_period_days" in params:
                subscription_data["trial_period_days"] = params["trial_period_days"]
            if "metadata" in params:
                subscription_data["metadata"] = params["metadata"]
            if "collection_method" in params:
                subscription_data["collection_method"] = params["collection_method"]
            
            loop = asyncio.get_event_loop()
            subscription = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Subscription.create(**subscription_data)
            )
            
            return self._create_success_result({
                "subscription_id": subscription.id,
                "customer": subscription.customer,
                "status": subscription.status,
                "current_period_start": getattr(subscription, 'current_period_start', None),
                "current_period_end": getattr(subscription, 'current_period_end', None),
                "created": subscription.created,
                "metadata": subscription.metadata
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to create subscription: {str(e)}")
    
    async def _get_subscription(self, params: Dict[str, Any]) -> ToolResult:
        """Get subscription details"""
        error = validate_required_params(params, ["subscription_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            loop = asyncio.get_event_loop()
            subscription = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Subscription.retrieve(params["subscription_id"])
            )
            
            return self._create_success_result({
                "subscription_id": subscription.id,
                "customer": subscription.customer,
                "status": subscription.status,
                "current_period_start": getattr(subscription, 'current_period_start', None),
                "current_period_end": getattr(subscription, 'current_period_end', None),
                "created": subscription.created,
                "items": [{"price": item.price.id, "quantity": item.quantity} for item in subscription.items.data],
                "metadata": subscription.metadata
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get subscription: {str(e)}")
    
    async def _update_subscription(self, params: Dict[str, Any]) -> ToolResult:
        """Update subscription"""
        error = validate_required_params(params, ["subscription_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            subscription_id = params.pop("subscription_id")
            
            loop = asyncio.get_event_loop()
            subscription = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Subscription.modify(subscription_id, **params)
            )
            
            return self._create_success_result({
                "subscription_id": subscription.id,
                "status": subscription.status,
                "updated": True
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to update subscription: {str(e)}")
    
    async def _cancel_subscription(self, params: Dict[str, Any]) -> ToolResult:
        """Cancel subscription"""
        error = validate_required_params(params, ["subscription_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            loop = asyncio.get_event_loop()
            subscription = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Subscription.delete(params["subscription_id"])
            )
            
            return self._create_success_result({
                "subscription_id": subscription.id,
                "status": subscription.status,
                "canceled": True,
                "canceled_at": subscription.canceled_at
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to cancel subscription: {str(e)}")
    
    async def _list_subscriptions(self, params: Dict[str, Any]) -> ToolResult:
        """List subscriptions"""
        try:
            list_params = {}
            if "customer" in params:
                list_params["customer"] = params["customer"]
            if "status" in params:
                list_params["status"] = params["status"]
            if "limit" in params:
                list_params["limit"] = min(int(params["limit"]), 100)
            
            loop = asyncio.get_event_loop()
            subscriptions = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Subscription.list(**list_params)
            )
            
            subscription_list = []
            for sub in subscriptions.data:
                subscription_list.append({
                    "subscription_id": sub.id,
                    "customer": sub.customer,
                    "status": sub.status,
                    "current_period_start": getattr(sub, 'current_period_start', None),
                    "current_period_end": getattr(sub, 'current_period_end', None),
                    "created": sub.created
                })
            
            return self._create_success_result({
                "subscriptions": subscription_list,
                "has_more": subscriptions.has_more,
                "total_count": len(subscription_list)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list subscriptions: {str(e)}")
    
    async def _create_product(self, params: Dict[str, Any]) -> ToolResult:
        """Create a product"""
        error = validate_required_params(params, ["name"])
        if error:
            return self._create_error_result(error)
        
        try:
            product_data = {"name": params["name"]}
            
            if "description" in params:
                product_data["description"] = params["description"]
            if "metadata" in params:
                product_data["metadata"] = params["metadata"]
            if "images" in params:
                product_data["images"] = params["images"]
            if "url" in params:
                product_data["url"] = params["url"]
            
            loop = asyncio.get_event_loop()
            product = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Product.create(**product_data)
            )
            
            return self._create_success_result({
                "product_id": product.id,
                "name": product.name,
                "description": product.description,
                "created": product.created,
                "metadata": product.metadata
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to create product: {str(e)}")
    
    async def _get_product(self, params: Dict[str, Any]) -> ToolResult:
        """Get product details"""
        error = validate_required_params(params, ["product_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            loop = asyncio.get_event_loop()
            product = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Product.retrieve(params["product_id"])
            )
            
            return self._create_success_result({
                "product_id": product.id,
                "name": product.name,
                "description": product.description,
                "created": product.created,
                "updated": product.updated,
                "metadata": product.metadata,
                "images": product.images
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get product: {str(e)}")
    
    async def _list_products(self, params: Dict[str, Any]) -> ToolResult:
        """List products"""
        try:
            list_params = {}
            if "limit" in params:
                list_params["limit"] = min(int(params["limit"]), 100)
            if "active" in params:
                list_params["active"] = params["active"]
            
            loop = asyncio.get_event_loop()
            products = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Product.list(**list_params)
            )
            
            product_list = []
            for product in products.data:
                product_list.append({
                    "product_id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "created": product.created,
                    "active": product.active
                })
            
            return self._create_success_result({
                "products": product_list,
                "has_more": products.has_more,
                "total_count": len(product_list)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list products: {str(e)}")
    
    async def _create_price(self, params: Dict[str, Any]) -> ToolResult:
        """Create a price for a product"""
        error = validate_required_params(params, ["currency", "product"])
        if error:
            return self._create_error_result(error)
        
        try:
            price_data = {
                "currency": params["currency"],
                "product": params["product"]
            }
            
            if "unit_amount" in params:
                price_data["unit_amount"] = int(params["unit_amount"])
            if "recurring" in params:
                price_data["recurring"] = params["recurring"]
            if "metadata" in params:
                price_data["metadata"] = params["metadata"]
            if "nickname" in params:
                price_data["nickname"] = params["nickname"]
            
            loop = asyncio.get_event_loop()
            price = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Price.create(**price_data)
            )
            
            return self._create_success_result({
                "price_id": price.id,
                "product": price.product,
                "unit_amount": price.unit_amount,
                "currency": price.currency,
                "recurring": price.recurring,
                "created": price.created
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to create price: {str(e)}")
    
    async def _get_price(self, params: Dict[str, Any]) -> ToolResult:
        """Get price details"""
        error = validate_required_params(params, ["price_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            loop = asyncio.get_event_loop()
            price = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Price.retrieve(params["price_id"])
            )
            
            return self._create_success_result({
                "price_id": price.id,
                "product": price.product,
                "unit_amount": price.unit_amount,
                "currency": price.currency,
                "recurring": price.recurring,
                "created": price.created,
                "metadata": price.metadata
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get price: {str(e)}")
    
    async def _list_prices(self, params: Dict[str, Any]) -> ToolResult:
        """List prices"""
        try:
            list_params = {}
            if "product" in params:
                list_params["product"] = params["product"]
            if "limit" in params:
                list_params["limit"] = min(int(params["limit"]), 100)
            if "active" in params:
                list_params["active"] = params["active"]
            
            loop = asyncio.get_event_loop()
            prices = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Price.list(**list_params)
            )
            
            price_list = []
            for price in prices.data:
                price_list.append({
                    "price_id": price.id,
                    "product": price.product,
                    "unit_amount": price.unit_amount,
                    "currency": price.currency,
                    "recurring": price.recurring,
                    "created": price.created
                })
            
            return self._create_success_result({
                "prices": price_list,
                "has_more": prices.has_more,
                "total_count": len(price_list)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list prices: {str(e)}")
    
    async def _create_invoice(self, params: Dict[str, Any]) -> ToolResult:
        """Create an invoice"""
        error = validate_required_params(params, ["customer"])
        if error:
            return self._create_error_result(error)
        
        try:
            invoice_data = {"customer": params["customer"]}
            
            if "description" in params:
                invoice_data["description"] = params["description"]
            if "metadata" in params:
                invoice_data["metadata"] = params["metadata"]
            if "collection_method" in params:
                invoice_data["collection_method"] = params["collection_method"]
            if "auto_advance" in params:
                invoice_data["auto_advance"] = params["auto_advance"]
            
            loop = asyncio.get_event_loop()
            invoice = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Invoice.create(**invoice_data)
            )
            
            return self._create_success_result({
                "invoice_id": invoice.id,
                "customer": invoice.customer,
                "status": invoice.status,
                "total": invoice.total,
                "currency": invoice.currency,
                "created": invoice.created,
                "due_date": invoice.due_date
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to create invoice: {str(e)}")
    
    async def _get_invoice(self, params: Dict[str, Any]) -> ToolResult:
        """Get invoice details"""
        error = validate_required_params(params, ["invoice_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            loop = asyncio.get_event_loop()
            invoice = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Invoice.retrieve(params["invoice_id"])
            )
            
            return self._create_success_result({
                "invoice_id": invoice.id,
                "customer": invoice.customer,
                "status": invoice.status,
                "total": invoice.total,
                "subtotal": invoice.subtotal,
                "currency": invoice.currency,
                "created": invoice.created,
                "due_date": invoice.due_date,
                "hosted_invoice_url": invoice.hosted_invoice_url,
                "invoice_pdf": invoice.invoice_pdf
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get invoice: {str(e)}")
    
    async def _send_invoice(self, params: Dict[str, Any]) -> ToolResult:
        """Send an invoice"""
        error = validate_required_params(params, ["invoice_id"])
        if error:
            return self._create_error_result(error)
        
        try:
            loop = asyncio.get_event_loop()
            invoice = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Invoice.send_invoice(params["invoice_id"])
            )
            
            return self._create_success_result({
                "invoice_id": invoice.id,
                "status": invoice.status,
                "sent": True
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to send invoice: {str(e)}")
    
    async def _list_invoices(self, params: Dict[str, Any]) -> ToolResult:
        """List invoices"""
        try:
            list_params = {}
            if "customer" in params:
                list_params["customer"] = params["customer"]
            if "status" in params:
                list_params["status"] = params["status"]
            if "limit" in params:
                list_params["limit"] = min(int(params["limit"]), 100)
            
            loop = asyncio.get_event_loop()
            invoices = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Invoice.list(**list_params)
            )
            
            invoice_list = []
            for invoice in invoices.data:
                invoice_list.append({
                    "invoice_id": invoice.id,
                    "customer": invoice.customer,
                    "status": invoice.status,
                    "total": invoice.total,
                    "currency": invoice.currency,
                    "created": invoice.created,
                    "due_date": invoice.due_date
                })
            
            return self._create_success_result({
                "invoices": invoice_list,
                "has_more": invoices.has_more,
                "total_count": len(invoice_list)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list invoices: {str(e)}")
    
    async def _get_balance(self, params: Dict[str, Any]) -> ToolResult:
        """Get account balance"""
        try:
            loop = asyncio.get_event_loop()
            balance = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Balance.retrieve()
            )
            
            return self._create_success_result({
                "available": balance.available,
                "pending": balance.pending,
                "connect_reserved": balance.connect_reserved,
                "livemode": balance.livemode,
                "object": balance.object
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to get balance: {str(e)}")
    
    async def _list_charges(self, params: Dict[str, Any]) -> ToolResult:
        """List charges"""
        try:
            list_params = {}
            if "customer" in params:
                list_params["customer"] = params["customer"]
            if "limit" in params:
                list_params["limit"] = min(int(params["limit"]), 100)
            if "created" in params:
                list_params["created"] = params["created"]
            
            loop = asyncio.get_event_loop()
            charges = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Charge.list(**list_params)
            )
            
            charge_list = []
            for charge in charges.data:
                charge_list.append({
                    "charge_id": charge.id,
                    "amount": charge.amount,
                    "currency": charge.currency,
                    "customer": charge.customer,
                    "description": charge.description,
                    "paid": charge.paid,
                    "refunded": charge.refunded,
                    "status": charge.status,
                    "created": charge.created
                })
            
            return self._create_success_result({
                "charges": charge_list,
                "has_more": charges.has_more,
                "total_count": len(charge_list)
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to list charges: {str(e)}")
    
    async def _refund_payment(self, params: Dict[str, Any]) -> ToolResult:
        """Refund a payment"""
        if "charge" not in params and "payment_intent" not in params:
            return self._create_error_result("Either charge or payment_intent is required")
        
        try:
            refund_data = {}
            if "charge" in params:
                refund_data["charge"] = params["charge"]
            if "payment_intent" in params:
                refund_data["payment_intent"] = params["payment_intent"]
            if "amount" in params:
                refund_data["amount"] = int(params["amount"])
            if "reason" in params:
                refund_data["reason"] = params["reason"]
            if "metadata" in params:
                refund_data["metadata"] = params["metadata"]
            
            loop = asyncio.get_event_loop()
            refund = await loop.run_in_executor(
                self.executor,
                lambda: stripe.Refund.create(**refund_data)
            )
            
            return self._create_success_result({
                "refund_id": refund.id,
                "amount": refund.amount,
                "currency": refund.currency,
                "charge": refund.charge,
                "payment_intent": refund.payment_intent,
                "status": refund.status,
                "reason": refund.reason,
                "created": refund.created
            })
            
        except Exception as e:
            return self._create_error_result(f"Failed to refund payment: {str(e)}")
    
    def get_mcp_tool_definition(self) -> types.Tool:
        """Get MCP tool definition for Stripe operations"""
        return types.Tool(
            name="stripe",
            description="Comprehensive Stripe payment processing and customer management for sales operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "create_customer", "get_customer", "update_customer", "list_customers",
                            "create_payment_intent", "get_payment_intent", "confirm_payment_intent",
                            "create_subscription", "get_subscription", "update_subscription", 
                            "cancel_subscription", "list_subscriptions",
                            "create_product", "get_product", "list_products",
                            "create_price", "get_price", "list_prices",
                            "create_invoice", "get_invoice", "send_invoice", "list_invoices",
                            "get_balance", "list_charges", "refund_payment"
                        ],
                        "description": "The Stripe action to perform"
                    },
                    "customer_id": {
                        "type": "string",
                        "description": "Stripe customer ID (required for customer operations)"
                    },
                    "payment_intent_id": {
                        "type": "string",
                        "description": "Payment intent ID (required for payment intent operations)"
                    },
                    "subscription_id": {
                        "type": "string",
                        "description": "Subscription ID (required for subscription operations)"
                    },
                    "product_id": {
                        "type": "string",
                        "description": "Product ID (required for product operations)"
                    },
                    "price_id": {
                        "type": "string",
                        "description": "Price ID (required for price operations)"
                    },
                    "invoice_id": {
                        "type": "string",
                        "description": "Invoice ID (required for invoice operations)"
                    },
                    "email": {
                        "type": "string",
                        "description": "Customer email address"
                    },
                    "name": {
                        "type": "string",
                        "description": "Customer or product name"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Customer phone number"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description for various objects"
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Amount in cents (for payments)"
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code (e.g., 'usd')"
                    },
                    "customer": {
                        "type": "string",
                        "description": "Customer ID for various operations"
                    },
                    "product": {
                        "type": "string",
                        "description": "Product ID for price creation"
                    },
                    "items": {
                        "type": "array",
                        "description": "Subscription items (array of {price: price_id, quantity: number})"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Metadata key-value pairs"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (max 100)"
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status (for listing operations)"
                    }
                },
                "required": ["action"]
            }
        )
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            self.executor.shutdown(wait=True)
            self.logger.info("Stripe tool cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during Stripe tool cleanup: {e}")
