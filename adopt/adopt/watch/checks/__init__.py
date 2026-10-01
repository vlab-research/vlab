"""The registered checks, name -> module. The interface is in `adopt.watch`."""

from . import ads_budget, number_health, pace, payments, providers

CHECKS = {
    "number_health": number_health,
    "pace": pace,
    "payments": payments,
    "providers": providers,
    "ads_budget": ads_budget,
}
