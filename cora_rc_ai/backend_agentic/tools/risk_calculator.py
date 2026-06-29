import json
import logging

logger = logging.getLogger(__name__)

def calculate_transaction_risk(
    amount: float,
    currency: str,
    country: str,
    kyc_verified: bool,
    instrument_type: str,
    product_complexity: str = "simple",
    customer_type: str = "retail"
) -> str:
    """
    Calculate the risk rating and identify risk factors for a financial transaction payload.
    Use this tool to get an objective risk classification based on customer KYC, country risk, and amount.

    Args:
        amount: The transaction value.
        currency: The currency symbol (e.g., USD, INR, EUR).
        country: The counterparty or destination country/jurisdiction (e.g., 'High-risk', 'India', 'Germany', 'USA').
        kyc_verified: Boolean indicating whether Know-Your-Customer verification is completed.
        instrument_type: The transaction instrument type (e.g., 'cross-border payment', 'derivative trade', 'NBFC lending').
        product_complexity: 'simple' or 'complex' (relevant for retail suitability).
        customer_type: 'retail' or 'institutional'.

    Returns:
        A JSON string containing the overall risk_rating ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'),
        a list of flagged risk_factors, and required_actions.
    """
    risk_factors = []
    required_actions = []

    # Coerce LLM-supplied arguments to expected types.
    # Tool-calling models frequently pass numbers and booleans as strings,
    # so normalize them before any numeric/boolean comparisons.
    try:
        amount = float(str(amount).replace(",", "").strip())
    except (TypeError, ValueError):
        amount = 0.0

    if isinstance(kyc_verified, str):
        kyc_verified = kyc_verified.strip().lower() in ("true", "yes", "y", "1", "verified", "completed")

    # 1. KYC Check
    if not kyc_verified:
        risk_factors.append("Customer KYC verification is incomplete/unverified.")
        required_actions.append("Perform full Customer Due Diligence (CDD) and verify identity documents.")
        required_actions.append("Hold transaction processing until KYC verification is complete.")
        
    # 2. Jurisdiction Risk
    #is_high_risk_country = country.strip().lower() in ["high-risk", "high risk", "sanctioned", "restricted", "blacklisted"]
    
    _HIGH_RISK_LABELS = {"high-risk", "high risk", "sanctioned", "restricted", "blacklisted"}
    _HIGH_RISK_COUNTRIES = {
        "iran", "pakistan", "syria", 
        "belarus", "somalia", "yemen",
        "libya", "iraq", "afghanistan"
    }
    is_high_risk_country = country.strip().lower() in (_HIGH_RISK_LABELS | _HIGH_RISK_COUNTRIES)


    if is_high_risk_country:
        risk_factors.append("Destination or counterparty jurisdiction is flagged as high-risk/non-cooperative.")
        required_actions.append("Initiate Enhanced Due Diligence (EDD) for high-risk country cross-border transaction.")
        required_actions.append("Verify source of funds and beneficial ownership.")
        
    # 3. High Value Transaction Check
    amount_in_usd = amount
    if currency.strip().upper() == "INR":
        amount_in_usd = amount / 83.0  # Approx conversion
    elif currency.strip().upper() == "EUR":
        amount_in_usd = amount * 1.08
        
    if amount_in_usd >= 1000000.0:  # $1M threshold
        risk_factors.append(f"Transaction value exceeds large exposure threshold: {currency} {amount:,.2f}")
        required_actions.append("Verify exposure limits and require senior management approval.")
        
    # 4. Suitability Check (MiFID II)
    if customer_type.strip().lower() == "retail" and product_complexity.strip().lower() == "complex":
        risk_factors.append("Retail customer is purchasing a complex financial product without an appropriateness assessment.")
        required_actions.append("Run appropriateness suitability questionnaire (MiFID II compliant).")
        required_actions.append("Provide retail risk disclosure warnings.")

    # Determine risk level
    if not kyc_verified and is_high_risk_country:
        risk_rating = "CRITICAL"
    elif not kyc_verified or is_high_risk_country:
        risk_rating = "HIGH"
    elif len(risk_factors) > 0:
        risk_rating = "MEDIUM"
    else:
        risk_rating = "LOW"
        
    if risk_rating in ["HIGH", "CRITICAL"]:
        required_actions.append("Generate Suspicious Transaction Report (STR) if suspicious activities are detected.")
        required_actions.append("Obtain final compliance officer sign-off.")
    else:
        required_actions.append("Proceed with standard transaction monitoring.")

    response = {
        "risk_rating": risk_rating,
        "flagged_factors": risk_factors,
        "required_actions": list(set(required_actions)), # Deduplicate actions
        "suitability_status": "VIOLATION" if (customer_type.strip().lower() == "retail" and product_complexity.strip().lower() == "complex") else "COMPLIANT"
    }
    
    return json.dumps(response, indent=2)
