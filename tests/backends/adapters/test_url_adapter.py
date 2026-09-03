import unittest
from unittest.mock import MagicMock

from clearskies.backends.adapters.url_adapter import UrlAdapter


class UrlAdapterTest(unittest.TestCase):
    def setUp(self):
        self.adapter = UrlAdapter(base_url="https://api.example.com/v1", url_suffix="")

    # ── finalize_url ────────────────────────────────────────────────────────

    def test_finalize_url_simple_no_params(self):
        url, used = self.adapter.finalize_url("users", {}, "records")
        self.assertEqual(url, "https://api.example.com/v1/users")
        self.assertEqual(used, [])

    def test_finalize_url_fills_routing_param_curly(self):
        url, used = self.adapter.finalize_url(
            "tenants/{tenant_id}/users",
            {"tenant_id": "abc", "other": "xyz"},
            "records",
        )
        self.assertEqual(url, "https://api.example.com/v1/tenants/abc/users")
        self.assertEqual(used, ["tenant_id"])

    def test_finalize_url_fills_routing_param_colon(self):
        url, used = self.adapter.finalize_url(
            "tenants/:tenant_id/users",
            {"tenant_id": "abc"},
            "records",
        )
        self.assertEqual(url, "https://api.example.com/v1/tenants/abc/users")
        self.assertEqual(used, ["tenant_id"])

    def test_finalize_url_raises_on_missing_param(self):
        with self.assertRaises(ValueError) as ctx:
            self.adapter.finalize_url("tenants/{tenant_id}/users", {}, "records")
        self.assertIn("tenant_id", str(ctx.exception))

    def test_finalize_url_raises_on_invalid_param_type(self):
        with self.assertRaises(ValueError) as ctx:
            self.adapter.finalize_url("tenants/{tenant_id}/users", {"tenant_id": ["list"]}, "records")  # type: ignore[arg-type]
        self.assertIn("tenant_id", str(ctx.exception))
        self.assertIn("list", str(ctx.exception))

    def test_finalize_url_int_param_converted_to_string(self):
        url, used = self.adapter.finalize_url("items/{item_id}", {"item_id": 42}, "records")
        self.assertIn("/42", url)

    def test_finalize_url_suffix(self):
        adapter = UrlAdapter(base_url="https://api.example.com", url_suffix=".json")
        url, used = adapter.finalize_url("users", {}, "records")
        self.assertEqual(url, "https://api.example.com/users/.json")

    def test_finalize_url_no_base_url(self):
        adapter = UrlAdapter()
        url, used = adapter.finalize_url("users", {}, "records")
        self.assertEqual(url, "users")

    # ── records_url ────────────────────────────────────────────────────────

    def test_records_url(self):
        query = MagicMock()
        query.model_class.destination_name.return_value = "users"
        query.conditions = []
        url, used = self.adapter.records_url(query)
        self.assertEqual(url, "https://api.example.com/v1/users")
        self.assertEqual(used, [])

    def test_records_url_uses_equality_conditions_for_routing(self):
        adapter = UrlAdapter(base_url="https://api.example.com/v1/{tenant_id}")
        condition = MagicMock()
        condition.operator = "="
        condition.column_name = "tenant_id"
        condition.values = ["t-123"]
        query = MagicMock()
        query.model_class.destination_name.return_value = "users"
        query.conditions = [condition]
        url, used = adapter.records_url(query)
        self.assertIn("t-123", url)
        self.assertIn("tenant_id", used)

    def test_records_url_ignores_non_equality_conditions(self):
        condition = MagicMock()
        condition.operator = ">"
        condition.column_name = "age"
        condition.values = [18]
        query = MagicMock()
        query.model_class.destination_name.return_value = "users"
        query.conditions = [condition]
        url, used = self.adapter.records_url(query)
        self.assertEqual(used, [])

    # ── create_url ────────────────────────────────────────────────────────

    def test_create_url(self):
        model = MagicMock()
        model.destination_name.return_value = "users"
        url, used = self.adapter.create_url({"name": "Jane"}, model)
        self.assertEqual(url, "https://api.example.com/v1/users")
        self.assertEqual(used, [])

    # ── update_url ────────────────────────────────────────────────────────

    def test_update_url(self):
        model = MagicMock()
        model.destination_name.return_value = "users"
        model.get_raw_data.return_value = {}
        url, used = self.adapter.update_url("u-1", {"name": "Jane"}, model)
        self.assertIn("users/u-1", url)

    def test_update_url_routing_from_data(self):
        adapter = UrlAdapter(base_url="https://api.example.com/{tenant_id}")
        model = MagicMock()
        model.destination_name.return_value = "users"
        model.get_raw_data.return_value = {}
        url, used = adapter.update_url("u-1", {"tenant_id": "t-1", "name": "Jane"}, model)
        self.assertIn("t-1", url)
        self.assertIn("tenant_id", used)

    # ── delete_url ────────────────────────────────────────────────────────

    def test_delete_url(self):
        model = MagicMock()
        model.destination_name.return_value = "users"
        model.get_raw_data.return_value = {}
        url, used = self.adapter.delete_url("u-1", model)
        self.assertIn("users/u-1", url)


if __name__ == "__main__":
    unittest.main()
