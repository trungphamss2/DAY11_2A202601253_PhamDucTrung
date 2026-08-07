"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 11: Confidence Router
  TODO 12: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 11: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        # 1. High-risk actions ALWAYS escalate regardless of confidence score
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        # 2. Threshold checks for general actions
        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )
        elif confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )
        else:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason="Low confidence — escalating",
                priority="high",
                requires_human=True,
            )


# ============================================================
# TODO 12: Design 3 HITL decision points + a review lifecycle
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
# - approval_path: What approve/reject/timeout decision is recorded?
# - audit_fields: Which correlation ID, intent and proposed action/diff are logged?
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "Change Beneficiary & High-Value Money Transfer",
        "trigger": "User requests updating beneficiary account details or initiating a money transfer over $5,000",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Old vs new beneficiary account, recipient bank code, transfer amount, account risk score, transaction anomaly flags",
        "example": "Customer asks: 'Transfer 50,000,000 VND to a newly added external account at 2 AM'",
        "approval_path": "Approving executes transfer; Rejecting cancels transaction and notifies user; Timeout (after 10 minutes) automatically HOLDS and REJECTS the transfer (never auto-sends on timeout)",
        "audit_fields": "request_id, correlation_id, user_id, intent='transfer_money', old_beneficiary, new_beneficiary, amount, reviewer_id, reviewer_decision, timeout_occurred, timestamp, layer='hitl_gate'",
    },
    {
        "id": 2,
        "name": "Account Closure & Data Deletion",
        "trigger": "User requests to close bank account or delete personal data (GDPR/PII deletion)",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Account status, remaining balance, open loans/credit cards, identity verification document status",
        "example": "Customer asks agent: 'Close my bank account and erase all my personal transaction records'",
        "approval_path": "Reviewer verifies zero balance and ID proof. Approving marks account for closure; Rejecting notifies user of pending balance/loans; Timeout automatically HOLDS request without deleting data",
        "audit_fields": "request_id, correlation_id, user_id, intent='close_account', account_balance, active_loans, reviewer_id, reviewer_decision, timeout_occurred, timestamp, layer='hitl_gate'",
    },
    {
        "id": 3,
        "name": "Medium Confidence Answer Queue Review",
        "trigger": "LLM response confidence score falls between 0.70 and 0.89 for complex banking inquiries",
        "hitl_model": "human-on-the-loop",
        "context_needed": "User prompt history, retrieved RAG document chunks, model draft response, confidence score",
        "example": "Customer asks about obscure home loan interest adjustment clauses and retrieved RAG chunks contain conflicting interest rates",
        "approval_path": "Reviewer can approve draft, edit response diff, or reject; Timeout auto-sends fallback response asking customer to contact support desk",
        "audit_fields": "request_id, correlation_id, user_id, prompt_text, model_draft_diff, confidence_score, reviewer_id, decision, timestamp, layer='confidence_router'",
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
