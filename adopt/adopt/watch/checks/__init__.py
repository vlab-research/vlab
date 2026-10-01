"""The registered checks, name -> module. The interface is in `adopt.watch`."""

from . import ads_budget, number_health, pace, payments

CHECKS = {
    "number_health": number_health,
    "pace": pace,
    "payments": payments,
    "ads_budget": ads_budget,
}
