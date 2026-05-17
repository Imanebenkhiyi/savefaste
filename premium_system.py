import os
import stripe
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from firebase_admin import firestore, auth as firebase_auth
import base64
import requests
from dotenv import load_dotenv

# ===== تحميل المتغيرات من .env =====
load_dotenv()

# ===== Firestore =====
db = firestore.client()

# ===== Stripe Config =====
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_PRICE_MONTHLY = os.getenv("STRIPE_PRICE_MONTHLY")
STRIPE_PRICE_YEARLY = os.getenv("STRIPE_PRICE_YEARLY")

# ===== PayPal Config =====
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID")
PAYPAL_API_BASE = "https://api-m.paypal.com"  # استخدم sandbox أثناء التطوير

# ===== Blueprint =====
premium_bp = Blueprint("premium", __name__)

# ==================================================
# 🔥 Firestore: دوال Premium
# ==================================================
def set_premium(uid, provider, sub_id, status="active", until_ts=None):
    data = {
        "is_premium": status == "active",
        "subscription": {"provider": provider, "id": sub_id, "status": status},
        "premium_until": until_ts
    }
    db.collection("users").document(uid).set(data, merge=True)

def clear_premium(uid):
    db.collection("users").document(uid).set({
        "is_premium": False,
        "premium_until": None,
        "subscription": firestore.DELETE_FIELD
    }, merge=True)

def get_uid_from_request():
    id_token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        id_token = auth_header.split(" ", 1)[1].strip()
    else:
        id_token = request.cookies.get("firebase_token")

    if not id_token:
        return None
    try:
        decoded = firebase_auth.verify_id_token(id_token)
        return decoded["uid"]
    except:
        return None

# ==================================================
# 🔥 Stripe: Config للـ frontend
# ==================================================
@premium_bp.route('/stripe-config', methods=['GET'])
def stripe_config():
    return jsonify({"publishableKey": STRIPE_PUBLISHABLE_KEY})

# ==================================================
# 🔥 PayPal: Client ID للـ frontend
# ==================================================
@premium_bp.route('/paypal-client-id', methods=['GET'])
def paypal_client_id():
    return jsonify({"clientId": PAYPAL_CLIENT_ID})

# ==================================================
# 🔥 Stripe: إنشاء اشتراك
# ==================================================
@premium_bp.route('/create-stripe-subscription', methods=['POST'])
def create_stripe_subscription():
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthenticated"}), 401

    data = request.json
    plan = data.get("plan")  # monthly / yearly

    user_doc = db.collection("users").document(uid).get().to_dict() or {}
    stripe_customer_id = user_doc.get("stripeCustomerId")
    if not stripe_customer_id:
        cust = stripe.Customer.create()
        stripe_customer_id = cust["id"]
        db.collection("users").document(uid).set({"stripeCustomerId": stripe_customer_id}, merge=True)

    price = STRIPE_PRICE_MONTHLY if plan == "monthly" else STRIPE_PRICE_YEARLY
    sub = stripe.Subscription.create(
        customer=stripe_customer_id,
        items=[{"price": price}],
        expand=["latest_invoice.payment_intent"]
    )

    db.collection("users").document(uid).set({
        "subscription": {"provider": "stripe", "id": sub.id, "status": sub.status}
    }, merge=True)

    return jsonify({"subscriptionId": sub.id, "status": sub.status})

# ==================================================
# 🔥 PayPal: إنشاء اشتراك
# ==================================================
def paypal_get_access_token():
    auth_str = f"{PAYPAL_CLIENT_ID}:{PAYPAL_SECRET}"
    b64 = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {b64}", "Content-Type": "application/x-www-form-urlencoded"}
    res = requests.post(f"{PAYPAL_API_BASE}/v1/oauth2/token", headers=headers, data={"grant_type": "client_credentials"})
    return res.json().get("access_token")

@premium_bp.route('/create-paypal-subscription', methods=['POST'])
def create_paypal_subscription():
    uid = get_uid_from_request()
    if not uid:
        return jsonify({"error": "unauthenticated"}), 401

    data = request.json
    plan = data.get("plan")  # monthly / yearly
    paypal_plan_id = "P-MONTHLY" if plan == "monthly" else "P-YEARLY"

    token = paypal_get_access_token()
    body = {
        "plan_id": paypal_plan_id,
        "custom_id": uid,
        "application_context": {
            "brand_name": "MySite",
            "return_url": "https://your-site.com/success",
            "cancel_url": "https://your-site.com/cancel"
        }
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    res = requests.post(f"{PAYPAL_API_BASE}/v1/billing/subscriptions", json=body, headers=headers)

    if res.status_code >= 400:
        return jsonify({"error": res.json()}), 400

    sub = res.json()
    sub_id = sub.get("id")

    db.collection("users").document(uid).set({
        "subscription": {"provider": "paypal", "id": sub_id, "status": "PENDING"}
    }, merge=True)

    return jsonify({"subscriptionId": sub_id})

# ==================================================
# 🔥 Stripe Webhook
# ==================================================
@premium_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except:
        return jsonify({"error": "signature error"}), 400

    if event["type"] == "invoice.payment_succeeded":
        inv = event["data"]["object"]
        sub_id = inv.get("subscription")
        sub = stripe.Subscription.retrieve(sub_id)
        period_end = datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)
        users = db.collection("users").where("subscription.id", "==", sub_id).get()
        for doc in users:
            set_premium(doc.id, "stripe", sub_id, "active", period_end)

    if event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        sub_id = sub["id"]
        users = db.collection("users").where("subscription.id", "==", sub_id).get()
        for doc in users:
            clear_premium(doc.id)

    return jsonify({"status": "ok"})

# ==================================================
# 🔥 PayPal Webhook
# ==================================================
@premium_bp.route('/webhook/paypal', methods=['POST'])
def paypal_webhook():
    event = request.json or {}
    event_type = event.get("event_type")
    resource = event.get("resource", {})

    if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
        sub_id = resource.get("id")
        uid = resource.get("custom_id")
        set_premium(uid, "paypal", sub_id, "active")

    if event_type == "BILLING.SUBSCRIPTION.CANCELLED":
        sub_id = resource.get("id")
        users = db.collection("users").where("subscription.id", "==", sub_id).get()
        for doc in users:
            clear_premium(doc.id)

    return jsonify({"status": "ok"})
