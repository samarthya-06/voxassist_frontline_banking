import unittest

from backend.app.services.rag_service import rag_service
from backend.app.services.ai_orchestrator import AIOrchestrator
from backend.app.services.vector_store import sop_store


class RagRetrievalTests(unittest.IsolatedAsyncioTestCase):
    async def test_fd_rates_retrieve_rate_card(self):
        result = await rag_service.answer("What are current FD rates for senior citizens?", branch_id="default")

        self.assertTrue("Fixed Deposit" in result.title or "Term Deposit" in result.title)
        self.assertGreaterEqual(result.confidence, 0.18)
        self.assertTrue(any("Retail Deposit Rate Card" in citation.source for citation in result.citations))
        self.assertTrue("7.05" in result.answer or "7.60" in result.answer)

    async def test_branch_policy_overrides_default_context(self):
        matches = await sop_store.retrieve("FD closure above INR 10 lakh branch approval", branch_id="Central District")

        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0].chunk.document_id, "branch-policy-demo-central-2026-04")

    async def test_unknown_policy_requires_staff_verification(self):
        result = await rag_service.answer("Does the branch provide cryptocurrency custody for minors?", branch_id="default")

        self.assertTrue(result.requiresStaffVerification)

    async def test_kyc_documents_retrieve_document_checklist(self):
        result = await rag_service.answer("What KYC documents are required for account opening?", branch_id="default")

        self.assertGreaterEqual(result.confidence, 0.18)
        self.assertTrue(result.citations)
        self.assertIn("PAN", result.answer)
        self.assertTrue("Aadhaar" in result.answer or "officially valid document" in result.answer)

    async def test_lost_card_blocking_retrieves_card_protocol(self):
        result = await rag_service.answer("Customer lost card, block it and check unauthorized transactions", branch_id="default")

        self.assertGreaterEqual(result.confidence, 0.18)
        self.assertTrue(any("Card" in citation.title for citation in result.citations))
        self.assertIn("block", result.answer.lower())

    async def test_service_fee_query_includes_source_and_amount(self):
        result = await rag_service.answer("How much is a Visa Platinum card replacement fee?", branch_id="default")

        self.assertGreaterEqual(result.confidence, 0.18)
        self.assertTrue(result.source)
        self.assertTrue(result.branchId)
        self.assertTrue(result.effectiveFrom)
        self.assertTrue("500" in result.answer or "INR 500" in result.answer)

    async def test_bounce_check_retrieves_cheque_return_policy(self):
        result = await rag_service.answer("What are the charges if my bounce check happens?", branch_id="default")

        self.assertGreaterEqual(result.confidence, 0.18)
        self.assertIn("Cheque", result.title)
        self.assertTrue("150" in result.answer and "750" in result.answer)

    async def test_marathi_cheque_question_does_not_use_pending_form(self):
        orchestrator = AIOrchestrator()

        async def no_provider_translate(text: str, source_code: str, target_code: str = "en-IN") -> str:
            return text

        orchestrator._call_sarvam_translate = no_provider_translate  # type: ignore[method-assign]
        orchestrator.set_language("mr-IN")
        orchestrator.awaiting_form_confirmation = True
        orchestrator.pending_form_type = "account_opening"

        try:
            result = await orchestrator.process_text_turn(
                "चेक बाउन्स झाला तर चार्ज काय आहे?",
                "customer",
                "mr-IN",
            )
        finally:
            await orchestrator.close()

        self.assertFalse(orchestrator.awaiting_form_confirmation)
        self.assertIsNone(orchestrator.pending_form_type)
        self.assertNotIn("autoStartForm", result)
        self.assertIn("assistantResponse", result)
        self.assertIn("INR 150", result["assistantResponse"])
        self.assertIn("चेक", result["assistantResponse"])


if __name__ == "__main__":
    unittest.main()
