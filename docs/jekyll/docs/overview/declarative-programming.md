---
layout: default
title: Declarative Programmings
parent: Overview
permalink: /docs/overview/declarative-apis.html
nav_order: 1
---

# Declarative Programming

Building applications via [declarative programming principles](https://en.wikipedia.org/wiki/Declarative_programming) means that you tell clearskies what you want done instead of how to do it.  Instead of building controllers and explicitly writing all the necessary logic for input validation, building queries, pagination, searching, etc, clearskies has the concept of "endpoints" which encapsulate common, standard behavior.  Consider a simple endpoint to return a set of records from a database table while allowing the user to specify simple search conditions as well as pagination and sorting.  Proper input validation, query building, etc, can easily result in hundreds of lines of code.  Clearskies, by contrast, has an endpoint built in for this functionality and so accomplishes the same with 10 or 20 lines of configuration.  It does this by relying heavily on model classes you declare which defines your data schema, and then you simply tell clearskies what columns to return or what the client is allowed to set.  Here's an example of how to define a model and build a fully functional REST API with full CRUD capabilities using minimal code:

{% highlight python %}
import clearskies
from clearskies.validators import Required, Unique
from clearskies import columns

class User(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = columns.Uuid()
    name = columns.String(validators=[Required()])
    username = columns.String(
        validators=[
            Required(),
            Unique(),
        ]
    )
    age = columns.Integer(validators=[Required()])
    created_at = columns.Created()
    updated_at = columns.Updated()

wsgi = clearskies.contexts.WsgiRef(
    clearskies.endpoints.RestfulApi(
        url="users",
        model_class=User,
        readable_column_names=["id", "name", "username", "age", "created_at", "updated_at"],
        writeable_column_names=["name", "username", "age"],
        sortable_column_names=["id", "name", "username", "age", "created_at", "updated_at"],
        searchable_column_names=["id", "name", "username", "age", "created_at", "updated_at"],
        default_sort_column_name="name",
    )
)
wsgi()
{% endhighlight %}

## Model

The first thing we do (after some imports) is to declare a model.  This tells clearskies everthing it needs to know about the data.  In this case the model says:

  1. clearskies can use the "id" column to uniquely identify every record.
  2. We want to use the memory backend, which means all data is stored in-memory instead of looking for a database.
  3. We have an id column which is a uuid, meaning that it will be automatically populated when the record is created.
  4. We have a username column which is required and must be unique.
  5. We have an age column which is required and is an integer.
  6. We want to record a timestamp when the record is created and store it in a column namd `created_at`
  7. We want to record a timestamp when the record is updated and store it in a column named `updated_at`.

## Context

Next, we create a WsgiRef object.  This is our "context", which tells clearskies how the application is running.  This fulfills promises of infrastructure neutrality: the context acts as an abstraction layer between clearskies and your hosting setup so that the application can understand how to receive input and send a response without having to modify any code.  The WsgiRef context is designed for testing purposes: it uses the WSGI server built into python so you can easily launch a demo/development application without having to actually install a WSGi server.

## Endpoint

The endpoint is where declarative programming really shines.  In this case, we use the RestfulApi endpoint that comes with clearskies.  This is intended to build a fully functional REST API with just a bit of configuration.  In this case, we highlight basic usage to demonstrate how it works, but there are a variety of additional hooks and knobs to enable more complicated behavior.  So, for the purposes of a simple example, we configure our Restful API endpoint as so:

 1. We tell it to use `/users` as the base URL for the API
 2. We pass along the `User` model. clearskies uses the schema information it contains and also uses it to fetch and store records.
 3. We tell it what columns to return to the client (e.g. the `readable_column_names`)
 4. We tell it what columns the client is allowed to set during create and update operations (`writeable_column_names`)
 5. We tell it what columns the client is allowed to sort by (`sortable_column_names`)
 6. We tell it what columns the client is allowed to search by (`searchable_column_names`)
 7. We tell it the default column to sort by.

If you do drop this in a python file, you can then query the server via Postman/Curl:

{% highlight bash %}
curl 'http://localhost:8080/users' -d '{"name": "Jane Doe", "username": "anonymous_bird", "age": 27}'

curl 'http://localhost:8080/users' -d '{"name": "John Brown", "username": "patient_dove", "age": 32}'
{% endhighlight %}

Which responds with something like:

{% highlight json %}
{
  "status": "success",
  "error": "",
  "data": {
    "id": "3617ed9e-5f2b-4a77-b849-6289dedcf6dd",
    "name": "Jane Doe",
    "username": "anonymous_bird",
    "age": 27,
    "created_at": "2025-06-22T02:50:53+00:00",
    "updated_at": "2025-06-22T02:50:53+00:00"
  },
  "pagination": {},
  "input_errors": {}
}

{
  "status": "success",
  "error": "",
  "data": {
    "id": "94a7cc7d-ab08-498b-9db5-a9e5404b11a9",
    "name": "John Brown",
    "username": "patient_dove",
    "age": 32,
    "created_at": "2025-06-22T02:52:28+00:00",
    "updated_at": "2025-06-22T02:52:28+00:00"
  },
  "pagination": {},
  "input_errors": {}
}
{% endhighlight %}

We can fetch these back out, search records, or fetch individual records by id:

{% highlight bash %}
curl 'http://localhost:8080/users'

curl 'http://localhost:8080/users?username=anonymous_bird'

curl 'http://localhost:8080/users/94a7cc7d-ab08-498b-9db5-a9e5404b11a9'
{% endhighlight %}

All of which return exactly what you would expect:

{% highlight json %}
{
  "status": "success",
  "error": "",
  "data": [
    {
      "id": "3617ed9e-5f2b-4a77-b849-6289dedcf6dd",
      "name": "Jane Doe",
      "username": "anonymous_bird",
      "age": 27,
      "created_at": "2025-06-22T02:50:53+00:00",
      "updated_at": "2025-06-22T02:50:53+00:00"
    },
    {
      "id": "94a7cc7d-ab08-498b-9db5-a9e5404b11a9",
      "name": "John Brown",
      "username": "patient_dove",
      "age": 32,
      "created_at": "2025-06-22T02:52:28+00:00",
      "updated_at": "2025-06-22T02:52:28+00:00"
    }
  ],
  "pagination": {
    "number_results": 2,
    "limit": 50,
    "next_page": {}
  },
  "input_errors": {}
}

{
  "status": "success",
  "error": "",
  "data": [
    {
      "id": "3617ed9e-5f2b-4a77-b849-6289dedcf6dd",
      "name": "Jane Doe",
      "username": "anonymous_bird",
      "age": 27,
      "created_at": "2025-06-22T02:50:53+00:00",
      "updated_at": "2025-06-22T02:50:53+00:00"
    }
  ],
  "pagination": {
    "number_results": 1,
    "limit": 50,
    "next_page": {}
  },
  "input_errors": {}
}

{
  "status": "success",
  "error": "",
  "data": {
    "id": "94a7cc7d-ab08-498b-9db5-a9e5404b11a9",
    "name": "John Brown",
    "username": "patient_dove",
    "age": 32,
    "created_at": "2025-06-22T02:52:28+00:00",
    "updated_at": "2025-06-22T02:52:28+00:00"
  },
  "pagination": {},
  "input_errors": {}
}
{% endhighlight %}

Finally, input validation is strictly enforced:

{% highlight bash %}
curl 'http://localhost:8080/users' -d '{"username": "anonymous_bird", "age": "Very Old", "not a column": "nope"}'
{% endhighlight %}

Which will return some errors:

{% highlight json %}
{
  "status": "input_errors",
  "error": "",
  "data": [],
  "pagination": {},
  "input_errors": {
    "name": "'name' is required.",
    "username": "Invalid value for 'username': the given value already exists, and must be unique.",
    "age": "value should be an integer",
    "not a column": "Input column not a column is not an allowed input column."
  }
}
{% endhighlight %}
