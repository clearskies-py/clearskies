---
layout: default
title: State Machines
parent: Overview
permalink: /docs/overview/state-machines.html
nav_order: 4
---

# State Machines

Applications obvoiusly don't *have* to be broken down from the pespective of a state machine, but it can be a surprisingly helpful way to manage application behavior which clearskies enables.  Clearskies accomplishes this by allowing you to attach business logic to state changes.  Combined with clearskies emphasis on reusable business logic, this allows you to build applications that are easier to understand, maintain, and adapt.  In most applications business logic is defined imperatively, which typically means that business logic lives in a controller: when a client invokes a specific endpoint with some specifc data then you take some actions.  With the state machine approach in clearskies, you instead define actions to based on changes in your application state.  This can mean things like, "When the record is created send an email to the user" or "When the status changes update a related model".  This implicitly separates your business logic from the details of how your application is invoked, which makes it easier to adapt to changing needs.  We'll walk through an example to show this, starting with a user and order model:

{% highlight python %}
import clearskies

class User(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    name = clearskies.columns.String()
    email = clearskies.columns.Email()

class Order(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    total = clearskies.columns.Float()
    status = clearskies.columns.Select(["Pending", "Paid", "Shipped", "Complete"])
    user_id = clearskies.columns.BelongsToId(User)
    user = clearskies.columns.BelongsToModel("user_id")
    updated_at = clearskies.columns.Updated()
    created_at = clearskies.columns.Created()
{% endhighlight %}

We have a user model that tracks an id and email, and then an order model with total, status, user, and created/updated timestamps.  Let's say that we want to keep track of when the order status changes to some given state.  With clearskies,this logic directly to the status column:

{% highlight python %}
class Order(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    total = clearskies.columns.Float()
    status = clearskies.columns.Select(
        ["Pending", "Paid", "Shipped", "Complete"],
        on_change_pre_save=lambda data, utcnow: {data["status"].lower() + "_at": utcnow},
    )

    user_id = clearskies.columns.BelongsToId(User)
    user = clearskies.columns.BelongsToModel("user_id")

    pending_at = clearskies.columns.Datetime()
    paid_at = clearskies.columns.Datetime()
    shipped_at = clearskies.columns.Datetime()
    complete_at = clearskies.columns.Datetime()
    updated_at = clearskies.columns.Updated()
    created_at = clearskies.columns.Created()
{% endhighlight %}

We've added a timestamp column to track when the order changes to each status, and then we use the `on_change_pre_save` hook to populate these.  Note that this is a stateless hook that expects a callable.  Clearskies will pass the new data to the callable and expects it to return a dictionary of data that will be added to the record during the save.  We use this hook to populate the corresponding timestamp column for the status the order is changing to.

For the next stage in this example, we decide that we want the status to automatically change to `Shipped` anytime a tracking number is set for the order.  We therefore add a `tracking_number` column to our model and add a pre-save hook to change the status when it is set:

{% highlight python %}
class Order(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    total = clearskies.columns.Float()
    tracking_number = clearskies.columns.String(
        on_change_pre_save=lambda: {"status": "Shipped"},
    )
    status = clearskies.columns.Select(
        ["Pending", "Paid", "Shipped", "Complete"],
        on_change_pre_save=lambda data, utcnow: {data["status"].lower() + "_at": utcnow},
    )

    user_id = clearskies.columns.BelongsToId(User)
    user = clearskies.columns.BelongsToModel("user_id")

    pending_at = clearskies.columns.Datetime()
    paid_at = clearskies.columns.Datetime()
    shipped_at = clearskies.columns.Datetime()
    complete_at = clearskies.columns.Datetime()
    updated_at = clearskies.columns.Updated()
    created_at = clearskies.columns.Created()
{% endhighlight %}

Next we might decide that, instead of keeping track of separate timestamps for every order status, we want to use a separate model to track order events.  Therefore, we add a new model as well as some post-save hooks to create the events.  We use the post save hook because it is stateful, and creating records in a separate table is a stateful action.  The post save hook also expects a callable which is passed the new data, the id of the record being saved, and any other dependencies available via the dependency injection system.  The callable here doesn't return anything.

{% highlight python %}
class OrderEvent(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    order_id = clearskies.columns.String()
    event = clearskies.columns.String()
    created_at = clearskies.columns.Created()

class Order(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    total = clearskies.columns.Float()
    tracking_number = clearskies.columns.String(
        on_change_pre_save=lambda: {"status": "Shipped"},
        on_change_post_save=lambda data, order_events, id: order_events.create({
            "order_id": id, "event": f'New tracking number added: {data["tracking_number"]}'
        }),
    )
    status = clearskies.columns.Select(
        ["Pending", "Paid", "Shipped", "Complete"],
        on_change_post_save=lambda data, order_events, id: order_events.create({
            "order_id": id, "event": f'Status changed to: {data["status"]}'
        }),
    )

    user_id = clearskies.columns.BelongsToId(User)
    user = clearskies.columns.BelongsToModel("user_id")
    events = clearskies.columns.HasMany(OrderEvent, readable_child_column_names=["id", "event", "created_at"])

    updated_at = clearskies.columns.Updated()
    created_at = clearskies.columns.Created(
        on_change_post_save=lambda order_events, id: order_events.create({"order_id": id, "event": "New order received"})
    )
{% endhighlight %}

We've added the OrderEvent Model which is connected to the order model via a HasMany relationship.  We then added a post save hook to three columns in the order table: tracking_number, status, and created_at.  When any of these columns are changed we create a record in the order event table connected to our order.

Here is a complete application that demonstrates how all these pieces come together via a simple CLI command that creates an order, changes the status, and then adds a tracking number:

{% highlight python %}
import clearskies
import time

##################
### our models ###
##################
class User(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    name = clearskies.columns.String()
    email = clearskies.columns.Email()

class OrderEvent(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    order_id = clearskies.columns.String()
    event = clearskies.columns.String()
    created_at = clearskies.columns.Created()

class Order(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    total = clearskies.columns.Float()
    tracking_number = clearskies.columns.String(
        on_change_pre_save=lambda: {"status": "Shipped"},
        on_change_post_save=lambda data, order_events, id: order_events.create({
            "order_id": id, "event": f'New tracking number added: {data["tracking_number"]}'
        }),
    )
    status = clearskies.columns.Select(
        ["Pending", "Paid", "Shipped", "Complete"],
        on_change_post_save=lambda data, order_events, id: order_events.create({
            "order_id": id, "event": f'Status changed to: {data["status"]}'
        }),
    )

    user_id = clearskies.columns.BelongsToId(User)
    user = clearskies.columns.BelongsToModel("user_id")
    events = clearskies.columns.HasMany(OrderEvent, readable_child_column_names=["id", "event", "created_at"])

    updated_at = clearskies.columns.Updated()
    created_at = clearskies.columns.Created(
        on_change_post_save=lambda order_events, id: order_events.create({"order_id": id, "event": "New order received"})
    )

#####################
## our application ##
#####################
def test_callable(orders: Order):
    order = orders.create({"total": 25})
    time.sleep(1)
    order.save({"status": "Pending"})
    time.sleep(1)
    order.save({"tracking_number": "asdf-12345"})
    return order

##########################################
## and a bit of configuration to run it ##
##########################################
cli = clearskies.contexts.Cli(
    clearskies.endpoints.Callable(
        test_callable,
        model_class=Order,
        readable_column_names=["id", "user_id", "total", "status", "tracking_number", "events"],
    ),
    classes=[User, Order, OrderEvent],
)
cli()
{% endhighlight %}

You can drop the above in a python file and execute it to see output something like this:

{% highlight json %}
{
  "status": "success",
  "error": "",
  "data": {
    "id": "059e7039-89b6-489e-b2b1-a9112e1aa61f",
    "user_id": "None",
    "total": 25.0,
    "status": "Shipped",
    "tracking_number": "asdf-12345",
    "events": [
      {
        "id": "f15e02eb-2025-49e7-9fd5-278a853f6ae0",
        "event": "New order received",
        "created_at": "2025-06-23T20:06:02+00:00"
      },
      {
        "id": "dfc97f14-f938-4c73-a2a5-1b680611ecec",
        "event": "Status changed to: Pending",
        "created_at": "2025-06-23T20:06:03+00:00"
      },
      {
        "id": "f12235f4-72a5-43f0-86ba-96439f4c66c0",
        "event": "Status changed to: Shipped",
        "created_at": "2025-06-23T20:06:04+00:00"
      },
      {
        "id": "a977e1cd-ac7a-4619-9581-b4a228251d5c",
        "event": "New tracking number added: asdf-12345",
        "created_at": "2025-06-23T20:06:04+00:00"
      }
    ]
  },
  "pagination": {},
  "input_errors": {}
}
{% endhighlight %}

Finally, it's important to emphasize that defining the business logic based on state changes separates it from how the data is changed, so the above code works identically if data is modified via an API.  To demonstrate that, this last example swaps out the CLI application for a Restful API:

{% highlight python %}
wsgi = clearskies.contexts.WsgiRef(
    clearskies.endpoints.RestfulApi(
        Order,
        writeable_column_names=["total", "status", "tracking_number"],
        readable_column_names=["id", "user_id", "total", "status", "tracking_number", "events", "updated_at", "created_at"],
        searchable_column_names=["user_id", "status"],
        sortable_column_names=["total", "status", "updated_at", "created_at"],
        default_sort_column_name="created_at",
        default_sort_direction="DESC",

    ),
    classes=[User, Order, OrderEvent],
)
wsgi()
{% endhighlight %}

Which can then be invoked via curl/postman/etc:

{% highlight bash %}
export ORDER_ID=$(curl 'http://localhost:8080/' -d '{"total":25}' | jq -r '.data.id')

curl "http://localhost:8080/$ORDER_ID" -X PATCH -d '{"status": "Pending"}'

curl "http://localhost:8080/$ORDER_ID" -X PATCH -d '{"tracking_number": "asdf-12345"}'
{% endhighlight %}

The output of the final API call is effectively identical to the original CLI application.  By attaching business logic to state changes we gain substantial flexibility in how our applications are executed.
