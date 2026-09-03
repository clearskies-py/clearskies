import unittest
from typing import cast
from unittest.mock import MagicMock

import clearskies
from clearskies.backends import ApiBackend
from clearskies.backends.adapters import (
    BodyCountAdapter,
    ParameterPaginationAdapter,
    ResponseAdapter,
    UrlAdapter,
)
from clearskies.contexts import Context


class Envelope(ResponseAdapter):
    def extract_records(self, response_data):
        if isinstance(response_data, dict):
            return response_data.get("data")
        return None


class ApiBackendAdapterIntegrationTest(unittest.TestCase):
    """End-to-end tests for the pluggable adapters on ApiBackend."""

    def _requests_returning(self, json_body, headers=None):
        requests = MagicMock()
        response = MagicMock()
        response.ok = True
        response.content = True
        response.headers = headers or {}
        response.json = MagicMock(return_value=json_body)
        requests.request = MagicMock(return_value=response)
        return requests

    def _run(self, model_class, app, requests):
        context = Context(
            clearskies.endpoints.Callable(app),
            classes=[model_class],
            bindings={"requests": requests},
        )
        (status_code, response, response_headers) = context()
        self.assertEqual(status_code, 200, response)
        return response["data"]

    # ── default adapters resolve to the right concrete types ────────────────

    def test_default_adapters_are_resolved(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.ApiBackend(base_url="https://api.example.com")
            id = clearskies.columns.String()
            name = clearskies.columns.String()

        def app(users: User):
            backend = cast(ApiBackend, users.backend)
            return {
                "url": type(backend.url_adapter_instance).__name__,
                "pagination": type(backend.pagination_adapter_instance).__name__,
                "count": type(backend.count_adapter_instance).__name__,
            }

        data = self._run(User, app, self._requests_returning([]))
        self.assertEqual(data["url"], "UrlAdapter")
        self.assertEqual(data["pagination"], "LinkHeaderPaginationAdapter")
        self.assertEqual(data["count"], "HeaderCountAdapter")

    def test_default_url_adapter_inherits_base_url(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.ApiBackend(base_url="https://api.example.com/v1", url_suffix=".json")
            id = clearskies.columns.String()

        def app(users: User):
            adapter = cast(UrlAdapter, cast(ApiBackend, users.backend).url_adapter_instance)
            return {"base_url": adapter.base_url, "url_suffix": adapter.url_suffix}

        data = self._run(User, app, self._requests_returning([]))
        self.assertEqual(data["base_url"], "https://api.example.com/v1")
        self.assertEqual(data["url_suffix"], ".json")

    # ── adapter instances are accepted by the config descriptor ────────────
    # Regression: AdapterOrCallable.__set__ used to only accept callables,
    # which rejected every (non-callable) adapter instance.

    def test_adapter_instances_are_accepted_by_config(self):
        count_adapter = BodyCountAdapter(count_path="meta.total")
        pagination_adapter = ParameterPaginationAdapter(pagination_parameter_name="page")
        url_adapter = UrlAdapter(base_url="https://api.example.com")

        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            count_adapter=count_adapter,
            pagination_adapter=pagination_adapter,
            url_adapter=url_adapter,
        )

        self.assertIs(backend.count_adapter, count_adapter)
        self.assertIs(backend.pagination_adapter, pagination_adapter)
        self.assertIs(backend.url_adapter, url_adapter)

    def test_callables_are_still_accepted_by_config(self):
        backend = clearskies.backends.ApiBackend(
            base_url="https://api.example.com",
            count_adapter=lambda headers, data: (5, None),
        )
        self.assertTrue(callable(backend.count_adapter))

    def test_invalid_value_is_rejected_by_config(self):
        with self.assertRaises(TypeError) as ctx:
            clearskies.backends.ApiBackend(
                base_url="https://api.example.com",
                count_adapter="not-an-adapter",  # type: ignore[arg-type]
            )
        self.assertIn("CountAdapter", str(ctx.exception))

    # ── header-based counting ──────────────────────────────────────────────

    def test_len_from_header_count_adapter(self):
        class User(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.ApiBackend(base_url="https://api.example.com")
            id = clearskies.columns.String()
            name = clearskies.columns.String()

        def app(users: User):
            query = users.limit(2)
            records = [u.name for u in query]
            return {"records": records, "count": len(query)}

        requests = self._requests_returning(
            [{"id": "1", "name": "alice"}, {"id": "2", "name": "bob"}],
            headers={"x-total-count": "3"},
        )
        data = self._run(User, app, requests)
        self.assertEqual(data["records"], ["alice", "bob"])
        self.assertEqual(data["count"], 3)

    # ── body-based counting ────────────────────────────────────────────────
    # Regression: records() used to pass None as the response body to
    # extract_count_from_response, so body-based count adapters never worked.

    def test_len_from_body_count_adapter(self):
        class Item(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.ApiBackend(
                base_url="https://api.example.com",
                response_adapter=Envelope(),
                count_adapter=BodyCountAdapter(
                    count_path="meta.pagination.total",
                    pages_path="meta.pagination.pages",
                ),
            )
            id = clearskies.columns.String()
            name = clearskies.columns.String()

        def app(items: Item):
            query = items.limit(2)
            records = [i.name for i in query]
            return {"records": records, "count": len(query)}

        requests = self._requests_returning(
            {
                "data": [{"id": "0", "name": "item0"}, {"id": "1", "name": "item1"}],
                "meta": {"pagination": {"total": 150, "pages": 75}},
            }
        )
        data = self._run(Item, app, requests)
        self.assertEqual(data["records"], ["item0", "item1"])
        self.assertEqual(data["count"], 150)

    # ── parameter-based pagination ─────────────────────────────────────────

    def test_next_page_from_parameter_pagination_adapter(self):
        class Item(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.ApiBackend(
                base_url="https://api.example.com",
                response_adapter=Envelope(),
                pagination_adapter=ParameterPaginationAdapter(
                    pagination_parameter_name="offset",
                    start_value=0,
                    use_limit_as_step=True,
                ),
                pagination_parameter_name="offset",
            )
            id = clearskies.columns.String()
            name = clearskies.columns.String()

        def app(items: Item):
            query = items.limit(2)
            records = [i.name for i in query]
            return {"records": records, "next_page": query.next_page_data()}

        requests = self._requests_returning({"data": [{"id": "0", "name": "item0"}, {"id": "1", "name": "item1"}]})
        data = self._run(Item, app, requests)
        self.assertEqual(data["records"], ["item0", "item1"])
        self.assertEqual(data["next_page"], {"offset": "2"})

    # ── can_count ──────────────────────────────────────────────────────────

    def test_can_count_defaults_to_false_and_is_configurable(self):
        default_backend = clearskies.backends.ApiBackend(base_url="https://api.example.com")
        counting_backend = clearskies.backends.ApiBackend(base_url="https://api.example.com", can_count=True)
        self.assertFalse(default_backend.can_count)
        self.assertTrue(counting_backend.can_count)
        # no config leakage between instances
        self.assertFalse(default_backend.can_count)

    def test_count_raises_when_can_count_is_false(self):
        backend = clearskies.backends.ApiBackend(base_url="https://api.example.com")
        with self.assertRaises(NotImplementedError) as ctx:
            backend.count(MagicMock())
        self.assertIn("can_count=True", str(ctx.exception))

    def test_count_method_defaults_to_head(self):
        backend = clearskies.backends.ApiBackend(base_url="https://api.example.com")
        self.assertEqual(backend.count_method(MagicMock()), "HEAD")
        self.assertEqual(backend.records_method(MagicMock()), "GET")

    # ── backward-compatible url helpers ────────────────────────────────────

    def test_finalize_url_shims_still_exist(self):
        backend = clearskies.backends.ApiBackend(base_url="https://api.example.com")
        url, used = backend.finalize_url_from_data("users", {}, "records")
        self.assertEqual(url, "https://api.example.com/users")
        self.assertEqual(used, [])


if __name__ == "__main__":
    unittest.main()
