
import unittest
from unittest.mock import patch

from verification.verifier import verify_task


class TestIndependentVerifier(unittest.TestCase):

    # Test 1: Task successfully completed
    @patch("verification.verifier.get_all_tasks")
    def test_successful_task(self, mock_tasks):

        mock_tasks.return_value = [
            (1, "Python Assignment", "Completed")
        ]

        result = verify_task("Python Assignment")

        self.assertEqual(
            result["verification_status"], "PASSED"
        )

    # Test 2: Task does not exist
    @patch("verification.verifier.get_all_tasks")
    def test_missing_task(self, mock_tasks):

        mock_tasks.return_value = []

        result = verify_task("Missing Task")

        self.assertEqual(
            result["verification_status"], "FAILED"
        )

    # Test 3: Task has incorrect status
    @patch("verification.verifier.get_all_tasks")
    def test_incorrect_status(self, mock_tasks):

        mock_tasks.return_value = [
            (2, "ML Assignment", "In Progress")
        ]

        result = verify_task("ML Assignment")

        self.assertEqual(
            result["verification_status"], "FAILED"
        )


if __name__ == "__main__":
    unittest.main()
