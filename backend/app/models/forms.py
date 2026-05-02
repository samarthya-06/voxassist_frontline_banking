"""Banking form definitions for AI-driven voice form filling.

Each form defines its fields in order, with the question the AI will ask
and the entity key to extract from the customer's spoken answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FormType(str, Enum):
    KYC = "kyc"
    ACCOUNT_OPENING = "account_opening"
    FD_APPLICATION = "fd_application"
    LOAN_APPLICATION = "loan_application"
    CARD_APPLICATION = "card_application"


@dataclass
class FormField:
    """One field inside a banking form."""

    key: str                        # e.g. "full_name"
    label: str                      # Display label: "Full Name"
    question: str                   # English question the AI asks
    field_type: str = "text"        # text | date | number | select
    options: list[str] | None = None  # For select fields
    required: bool = True
    validation_hint: str = ""       # Hint for AI to validate/format


@dataclass
class FormDefinition:
    """Complete definition of a banking form."""

    form_type: FormType
    title: str
    description: str
    icon: str                       # Lucide icon name for the frontend
    fields: list[FormField] = field(default_factory=list)

    @property
    def total_fields(self) -> int:
        return len(self.fields)

    def field_at(self, index: int) -> FormField | None:
        if 0 <= index < len(self.fields):
            return self.fields[index]
        return None

    def to_dict(self) -> dict:
        return {
            "formType": self.form_type.value,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "totalFields": self.total_fields,
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "question": f.question,
                    "fieldType": f.field_type,
                    "options": f.options,
                    "required": f.required,
                }
                for f in self.fields
            ],
        }


@dataclass
class FormSession:
    """Runtime state for an active form-filling interview."""

    form_type: FormType
    current_field_index: int = 0
    filled_fields: dict[str, str] = field(default_factory=dict)
    is_complete: bool = False

    @property
    def progress(self) -> float:
        definition = FORM_REGISTRY[self.form_type]
        if definition.total_fields == 0:
            return 100.0
        return (len(self.filled_fields) / definition.total_fields) * 100

    @property
    def filled_count(self) -> int:
        return len(self.filled_fields)

    def to_dict(self) -> dict:
        definition = FORM_REGISTRY[self.form_type]
        return {
            "formType": self.form_type.value,
            "currentFieldIndex": self.current_field_index,
            "filledFields": self.filled_fields,
            "totalFields": definition.total_fields,
            "filledCount": self.filled_count,
            "progress": round(self.progress, 1),
            "isComplete": self.is_complete,
        }


# ══════════════════════════════════════════════════════════════════════════════
# FORM DEFINITIONS — all standard Indian banking forms
# ══════════════════════════════════════════════════════════════════════════════

KYC_FORM = FormDefinition(
    form_type=FormType.KYC,
    title="KYC Verification",
    description="Know Your Customer identity verification form",
    icon="UserCheck",
    fields=[
        FormField(
            key="full_name",
            label="Full Name",
            question="What is your full name as it appears on your ID?",
            validation_hint="Full name with first and last name",
        ),
        FormField(
            key="date_of_birth",
            label="Date of Birth",
            question="What is your date of birth?",
            field_type="date",
            validation_hint="Format: DD/MM/YYYY",
        ),
        FormField(
            key="pan_number",
            label="PAN Number",
            question="What is your PAN card number?",
            validation_hint="10-character alphanumeric PAN: ABCDE1234F",
        ),
        FormField(
            key="aadhaar_number",
            label="Aadhaar Number",
            question="What is your Aadhaar number?",
            validation_hint="12-digit Aadhaar number",
        ),
        FormField(
            key="address",
            label="Residential Address",
            question="What is your current residential address?",
            validation_hint="Full address with house number and street",
        ),
        FormField(
            key="city",
            label="City",
            question="Which city do you live in?",
        ),
        FormField(
            key="state",
            label="State",
            question="Which state?",
        ),
        FormField(
            key="pin_code",
            label="PIN Code",
            question="What is your area PIN code?",
            validation_hint="6-digit PIN code",
        ),
        FormField(
            key="phone",
            label="Phone Number",
            question="What is your mobile phone number?",
            validation_hint="10-digit Indian mobile number",
        ),
        FormField(
            key="email",
            label="Email Address",
            question="What is your email address?",
            required=False,
            validation_hint="Valid email address",
        ),
        FormField(
            key="occupation",
            label="Occupation",
            question="What is your occupation?",
        ),
        FormField(
            key="annual_income",
            label="Annual Income",
            question="What is your approximate annual income?",
            field_type="number",
            validation_hint="Amount in INR",
        ),
    ],
)

ACCOUNT_OPENING_FORM = FormDefinition(
    form_type=FormType.ACCOUNT_OPENING,
    title="Account Opening",
    description="New bank account application form",
    icon="Landmark",
    fields=[
        FormField(
            key="full_name",
            label="Full Name",
            question="What is your full name?",
        ),
        FormField(
            key="date_of_birth",
            label="Date of Birth",
            question="What is your date of birth?",
            field_type="date",
            validation_hint="Format: DD/MM/YYYY",
        ),
        FormField(
            key="pan_number",
            label="PAN Number",
            question="Please tell me your PAN number.",
            validation_hint="10-character alphanumeric PAN",
        ),
        FormField(
            key="aadhaar_number",
            label="Aadhaar Number",
            question="What is your Aadhaar number?",
            validation_hint="12-digit number",
        ),
        FormField(
            key="phone",
            label="Phone Number",
            question="What is your mobile number?",
            validation_hint="10-digit Indian mobile number",
        ),
        FormField(
            key="address",
            label="Address",
            question="What is your residential address?",
        ),
        FormField(
            key="account_type",
            label="Account Type",
            question="What type of account would you like to open — Savings or Current?",
            field_type="select",
            options=["Savings", "Current"],
        ),
        FormField(
            key="nominee_name",
            label="Nominee Name",
            question="Who would you like to nominate for this account?",
        ),
        FormField(
            key="nominee_relation",
            label="Nominee Relationship",
            question="What is your relationship with the nominee?",
        ),
        FormField(
            key="initial_deposit",
            label="Initial Deposit Amount",
            question="How much would you like to deposit as the opening amount?",
            field_type="number",
            validation_hint="Amount in INR",
        ),
    ],
)

FD_APPLICATION_FORM = FormDefinition(
    form_type=FormType.FD_APPLICATION,
    title="Fixed Deposit Application",
    description="Fixed deposit opening application form",
    icon="PiggyBank",
    fields=[
        FormField(
            key="full_name",
            label="Full Name",
            question="What is your full name?",
        ),
        FormField(
            key="pan_number",
            label="PAN Number",
            question="What is your PAN number?",
            validation_hint="10-character alphanumeric PAN",
        ),
        FormField(
            key="account_number",
            label="Linked Account Number",
            question="What is your existing bank account number for this FD?",
        ),
        FormField(
            key="deposit_amount",
            label="Deposit Amount",
            question="How much would you like to invest in the fixed deposit?",
            field_type="number",
            validation_hint="Amount in INR",
        ),
        FormField(
            key="tenure",
            label="Tenure (Months)",
            question="For how many months would you like the fixed deposit?",
            field_type="number",
            validation_hint="Number of months",
        ),
        FormField(
            key="interest_payout",
            label="Interest Payout",
            question="Would you like monthly interest payout or reinvestment at maturity?",
            field_type="select",
            options=["Monthly Payout", "Quarterly Payout", "Reinvest at Maturity"],
        ),
        FormField(
            key="nominee_name",
            label="Nominee Name",
            question="Who is the nominee for this fixed deposit?",
        ),
    ],
)

LOAN_APPLICATION_FORM = FormDefinition(
    form_type=FormType.LOAN_APPLICATION,
    title="Loan Application",
    description="Personal / Home / Vehicle loan application form",
    icon="HandCoins",
    fields=[
        FormField(
            key="full_name",
            label="Full Name",
            question="What is your full name?",
        ),
        FormField(
            key="pan_number",
            label="PAN Number",
            question="What is your PAN number?",
            validation_hint="10-character alphanumeric PAN",
        ),
        FormField(
            key="phone",
            label="Phone Number",
            question="What is your mobile number?",
            validation_hint="10-digit Indian mobile number",
        ),
        FormField(
            key="loan_type",
            label="Loan Type",
            question="What type of loan are you looking for — Personal, Home, or Vehicle?",
            field_type="select",
            options=["Personal Loan", "Home Loan", "Vehicle Loan", "Education Loan"],
        ),
        FormField(
            key="loan_amount",
            label="Loan Amount",
            question="How much loan amount do you need?",
            field_type="number",
            validation_hint="Amount in INR",
        ),
        FormField(
            key="loan_purpose",
            label="Purpose of Loan",
            question="What is the purpose of this loan?",
        ),
        FormField(
            key="employment_type",
            label="Employment Type",
            question="Are you salaried, self-employed, or a business owner?",
            field_type="select",
            options=["Salaried", "Self-Employed", "Business Owner", "Professional"],
        ),
        FormField(
            key="monthly_income",
            label="Monthly Income",
            question="What is your monthly income?",
            field_type="number",
            validation_hint="Amount in INR",
        ),
        FormField(
            key="existing_loans",
            label="Existing Loan EMIs",
            question="Do you have any existing loan EMIs? If yes, what is the total monthly EMI amount?",
            required=False,
            validation_hint="Amount in INR or 'None'",
        ),
    ],
)

CARD_APPLICATION_FORM = FormDefinition(
    form_type=FormType.CARD_APPLICATION,
    title="Card Application",
    description="Debit / Credit card application form",
    icon="CreditCard",
    fields=[
        FormField(
            key="full_name",
            label="Full Name",
            question="What is your full name as you want it printed on the card?",
        ),
        FormField(
            key="pan_number",
            label="PAN Number",
            question="What is your PAN number?",
            validation_hint="10-character alphanumeric PAN",
        ),
        FormField(
            key="phone",
            label="Phone Number",
            question="What is your registered mobile number?",
            validation_hint="10-digit Indian mobile number",
        ),
        FormField(
            key="card_type",
            label="Card Type",
            question="Would you like a Debit card or a Credit card?",
            field_type="select",
            options=["Debit Card", "Credit Card"],
        ),
        FormField(
            key="credit_limit",
            label="Preferred Credit Limit",
            question="What credit limit would you prefer? You can say a range.",
            field_type="number",
            required=False,
            validation_hint="Amount in INR",
        ),
        FormField(
            key="billing_address",
            label="Billing Address",
            question="What address should be used for billing?",
        ),
        FormField(
            key="delivery_address",
            label="Card Delivery Address",
            question="Where should we deliver the card? Same as billing address or a different one?",
        ),
    ],
)


# ── Global registry ──────────────────────────────────────────────────────────
FORM_REGISTRY: dict[FormType, FormDefinition] = {
    FormType.KYC: KYC_FORM,
    FormType.ACCOUNT_OPENING: ACCOUNT_OPENING_FORM,
    FormType.FD_APPLICATION: FD_APPLICATION_FORM,
    FormType.LOAN_APPLICATION: LOAN_APPLICATION_FORM,
    FormType.CARD_APPLICATION: CARD_APPLICATION_FORM,
}


def get_form_definition(form_type: str) -> FormDefinition | None:
    """Look up a form definition by its string key."""
    try:
        return FORM_REGISTRY[FormType(form_type)]
    except (ValueError, KeyError):
        return None


def get_all_form_types() -> list[dict]:
    """Return a summary list of all available form types for the frontend."""
    return [
        {
            "formType": fd.form_type.value,
            "title": fd.title,
            "description": fd.description,
            "icon": fd.icon,
            "totalFields": fd.total_fields,
        }
        for fd in FORM_REGISTRY.values()
    ]
