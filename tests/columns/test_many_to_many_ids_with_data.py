import clearskies
from tests.test_base import TestBase


class ManyToManyIdsWithDataTest(TestBase):
    def test_default(self):
        class ThingyWidgets(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            # these could also be belongs to relationships, but the pivot model
            # is rarely used directly, so I'm being lazy to avoid having to use
            # model references.
            thingy_id = clearskies.columns.String()
            widget_id = clearskies.columns.String()
            name = clearskies.columns.String()
            kind = clearskies.columns.String()

        class Thingy(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        class Widget(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            thingy_ids = clearskies.columns.ManyToManyIdsWithData(
                related_model_class=Thingy,
                pivot_model_class=ThingyWidgets,
                readable_pivot_column_names=["id", "thingy_id", "widget_id", "name", "kind"],
            )
            thingies = clearskies.columns.ManyToManyModels("thingy_ids")
            thingy_widgets = clearskies.columns.ManyToManyPivots("thingy_ids")

        def my_application(widgets: Widget, thingies: Thingy):
            thing_1 = thingies.create({"name": "Thing 1"})
            thing_2 = thingies.create({"name": "Thing 2"})
            thing_3 = thingies.create({"name": "Thing 3"})
            widget = widgets.create(
                {
                    "name": "Widget 1",
                    "thingy_ids": [
                        {"thingy_id": thing_1.id, "name": "Widget Thing 1", "kind": "Special"},
                        {"thingy_id": thing_2.id, "name": "Widget Thing 2", "kind": "Also Special"},
                    ],
                }
            )

            return widget

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Widget,
                return_records=True,
                readable_column_names=["id", "name", "thingy_widgets"],
            ),
            classes=[Widget, Thingy, ThingyWidgets],
        )
        status_code, response_data, response_headers = context()
        assert [record["name"] for record in response_data["data"]["thingy_widgets"]] == [
            "Widget Thing 1",
            "Widget Thing 2",
        ]

    def test_integer_ids_post_save_normalises_string_ids(self):
        """ManyToManyIdsWithData.post_save doesn't spuriously delete entries when ids arrive as strings."""

        class ThingyWidgets(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            thingy_id = clearskies.columns.Integer()
            widget_id = clearskies.columns.Integer()
            kind = clearskies.columns.String()

        class Thingy(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            name = clearskies.columns.String()

        class Widget(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            name = clearskies.columns.String()
            thingy_ids = clearskies.columns.ManyToManyIdsWithData(
                related_model_class=Thingy,
                pivot_model_class=ThingyWidgets,
                readable_pivot_column_names=["id", "thingy_id", "widget_id", "kind"],
            )

        di = clearskies.di.Di(classes=[Widget, Thingy, ThingyWidgets])
        thingies = di.build(Thingy)
        widgets = di.build(Widget)
        pivots = di.build(ThingyWidgets)

        thing_1 = thingies.create({"id": 1, "name": "Thing 1"})
        thing_2 = thingies.create({"id": 2, "name": "Thing 2"})
        widget = widgets.create(
            {
                "id": 10,
                "name": "Widget 1",
                "thingy_ids": [
                    {"thingy_id": 1, "kind": "A"},
                    {"thingy_id": 2, "kind": "B"},
                ],
            }
        )

        assert len(pivots.where("widget_id=10")) == 2

        # Resave with string ids — should update, not delete+recreate
        widget.save(
            {
                "thingy_ids": [
                    {"thingy_id": "1", "kind": "A-updated"},
                    {"thingy_id": "2", "kind": "B"},
                ]
            }
        )

        assert len(pivots.where("widget_id=10")) == 2
        kinds = sorted(pivot.kind for pivot in pivots.where("widget_id=10"))
        assert kinds == ["A-updated", "B"]

    def test_removing_related_id_does_not_touch_other_records(self):
        """Removing a related id from one record must not delete other records' links to it."""

        class ThingyWidgets(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            thingy_id = clearskies.columns.String()
            widget_id = clearskies.columns.String()
            kind = clearskies.columns.String()

        class Thingy(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()

        class Widget(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            name = clearskies.columns.String()
            thingy_ids = clearskies.columns.ManyToManyIdsWithData(
                related_model_class=Thingy,
                pivot_model_class=ThingyWidgets,
                readable_pivot_column_names=["id", "thingy_id", "widget_id", "kind"],
            )

        di = clearskies.di.Di(classes=[Widget, Thingy, ThingyWidgets])
        thingies = di.build(Thingy)
        widgets = di.build(Widget)
        pivots = di.build(ThingyWidgets)

        shared = thingies.create({"name": "Shared"})
        other = thingies.create({"name": "Other"})
        widget_a = widgets.create(
            {"name": "A", "thingy_ids": [{"thingy_id": shared.id, "kind": "x"}, {"thingy_id": other.id, "kind": "y"}]}
        )
        widget_b = widgets.create({"name": "B", "thingy_ids": [{"thingy_id": shared.id, "kind": "z"}]})

        widget_a.save({"thingy_ids": [{"thingy_id": other.id, "kind": "y"}]})

        assert [pivot.thingy_id for pivot in pivots.where(f"widget_id={widget_a.id}")] == [other.id]
        assert [pivot.thingy_id for pivot in pivots.where(f"widget_id={widget_b.id}")] == [shared.id]
