import unittest

from backend.app.services.rag_service import rag_service
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


if __name__ == "__main__":
    unittest.main()
