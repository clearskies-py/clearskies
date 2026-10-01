import clearskies
from tests.test_base import TestBase


class ManyToManyIdsTest(TestBase):
    def test_default(self):
        class ThingyToWidget(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            # these could also be belongs to relationships, but the pivot model
            # is rarely used directly, so I'm being lazy to avoid having to use
            # model references.
            thingy_id = clearskies.columns.String()
            widget_id = clearskies.columns.String()

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
            thingy_ids = clearskies.columns.ManyToManyIds(
                related_model_class=Thingy,
                pivot_model_class=ThingyToWidget,
            )
            thingies = clearskies.columns.ManyToManyModels("thingy_ids")

        def my_application(widgets: Widget, thingies: Thingy):
            thing_1 = thingies.create({"name": "Thing 1"})
            thing_2 = thingies.create({"name": "Thing 2"})
            thing_3 = thingies.create({"name": "Thing 3"})
            widget = widgets.create(
                {
                    "name": "Widget 1",
                    "thingy_ids": [thing_1.id, thing_2.id],
                }
            )

            # remove an item by saving without it's id in place
            widget.save({"thingy_ids": [thing.id for thing in widget.thingies if thing.id != thing_1.id]})

            # add an item by saving and adding the new id
            widget.save({"thingy_ids": [*widget.thingy_ids, thing_3.id]})

            return widget.thingies

        context = clearskies.contexts.Context(
            clearskies.endpoints.Callable(
                my_application,
                model_class=Thingy,
                return_records=True,
                readable_column_names=["id", "name"],
            ),
            classes=[Widget, Thingy, ThingyToWidget],
        )
        status_code, response_data, response_headers = context()

        assert [record["name"] for record in response_data["data"]] == ["Thing 2", "Thing 3"]

    def test_integer_related_ids_typed_in_to_json_and_docs(self):
        """ManyToManyIds returns int ids and documents them as Integer for an Integer-id related model."""

        class ThingyToWidget(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            thingy_id = clearskies.columns.Integer()
            widget_id = clearskies.columns.Integer()

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
            thingy_ids = clearskies.columns.ManyToManyIds(
                related_model_class=Thingy,
                pivot_model_class=ThingyToWidget,
            )

        di = clearskies.di.Di(classes=[Widget, Thingy, ThingyToWidget])
        thingies = di.build(Thingy)
        widgets = di.build(Widget)

        thing_1 = thingies.create({"id": 1, "name": "Thing 1"})
        thing_2 = thingies.create({"id": 2, "name": "Thing 2"})
        widget = widgets.create({"id": 10, "name": "Widget 1", "thingy_ids": [1, 2]})

        column = Widget.thingy_ids
        result = column.to_json(widget)
        ids = result["thingy_ids"]

        assert sorted(ids) == [1, 2]
        assert all(isinstance(thingy_id, int) for thingy_id in ids)

        # documentation should reflect integer type
        Widget().get_columns()
        docs = Widget.thingy_ids.documentation()
        assert len(docs) == 1
        assert isinstance(docs[0], clearskies.autodoc.schema.Array)
        assert isinstance(docs[0].item_definition, clearskies.autodoc.schema.Integer)

    def test_integer_ids_post_save_normalises_string_ids(self):
        """ManyToManyIds.post_save doesn't duplicate entries when ids arrive as strings."""

        class ThingyToWidget(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Integer()
            thingy_id = clearskies.columns.Integer()
            widget_id = clearskies.columns.Integer()

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
            thingy_ids = clearskies.columns.ManyToManyIds(
                related_model_class=Thingy,
                pivot_model_class=ThingyToWidget,
            )

        di = clearskies.di.Di(classes=[Widget, Thingy, ThingyToWidget])
        thingies = di.build(Thingy)
        widgets = di.build(Widget)
        pivots = di.build(ThingyToWidget)

        thing_1 = thingies.create({"id": 1, "name": "Thing 1"})
        thing_2 = thingies.create({"id": 2, "name": "Thing 2"})
        widget = widgets.create({"id": 10, "name": "Widget 1", "thingy_ids": [1, 2]})

        # Save with string ids — should not create duplicates
        widget.save({"thingy_ids": ["1", "2"]})

        assert sorted(widget.thingy_ids) == [1, 2]
        # pivot table should still have exactly 2 rows
        assert len(pivots.where("widget_id=10")) == 2

    def test_removing_related_id_does_not_touch_other_records(self):
        """Removing a related id from one record must not delete other records' links to it."""

        class ThingyToWidget(clearskies.Model):
            id_column_name = "id"
            backend = clearskies.backends.MemoryBackend()

            id = clearskies.columns.Uuid()
            thingy_id = clearskies.columns.String()
            widget_id = clearskies.columns.String()

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
            thingy_ids = clearskies.columns.ManyToManyIds(
                related_model_class=Thingy,
                pivot_model_class=ThingyToWidget,
            )

        di = clearskies.di.Di(classes=[Widget, Thingy, ThingyToWidget])
        thingies = di.build(Thingy)
        widgets = di.build(Widget)

        shared = thingies.create({"name": "Shared"})
        other = thingies.create({"name": "Other"})
        widget_a = widgets.create({"name": "A", "thingy_ids": [shared.id, other.id]})
        widget_b = widgets.create({"name": "B", "thingy_ids": [shared.id]})

        widget_a.save({"thingy_ids": [other.id]})

        assert widget_a.thingy_ids == [other.id]
        assert widget_b.thingy_ids == [shared.id]
