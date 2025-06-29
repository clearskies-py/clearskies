---
layout: default
title: Infrastructure Neutral
parent: Overview
permalink: docs/overview/infrastructure-neutral.html
nav_order: 2
---

# Infrastructure Neutral

## Context

To run code in clearskies you attach your application to a context which can represent anything: a WSGI server, Lambda, Queue listener, CLI, test environment, etc... This means that the same code can run in your production environment, on a dev machine, or in your test suite without making any changes.

Consider a simple application that takes a name from a URL parameter and greets the caller:

{% highlight python %}
import clearskies

def greetings(name):
    return f'Hello {name}!'

greetings_application = clearskies.endpoints.Callable(
    greetings,
    url="/:name"
)
{% endhighlight %}

Note the Callable endpoint: applications in clearskies start with endpoints, which define common behavior.  The Callable endpoint is the most basic building block as it simply calls a developer-defined function which, in essence, turns clearskies back into a more standard development framework.  However, this still can't be called until we attach it to a context.  For development purposes clearskies comes with a built-in WSGI server which we use in the first example below.

{% highlight python %}
import clearskies

def greetings(name):
    return f'Hello {name}!'

greetings_application = clearskies.endpoints.Callable(
    greetings,
    url="/:name"
)

wsgi = clearskies.contexts.WsgiRef(greetings_application)
wsgi()
{% endhighlight %}

As a quick note, you can attach a function directly to a context without using an endpoint, but then you can't set the URL or other configuration settings.

Now, in production you'll have your own WSGI server, in which case you just need a WSGI application.  To make that happen, you just change the last few lines of code:

{% highlight python %}
wsgi = clearskies.contexts.Wsgi(greetings_application)
def wsgi_handler(env, start_response):
    return wsgi(env, start_response)
{% endhighlight %}

The `wsgi_handler` function is then what you would have your WSGi server run.  Still, what if you are running in AWS and are using a lambda behind an API gateway?  Just another tweak:

{% highlight python %}
import clearskies_aws

in_lambda = clearskies_aws.contexts.LambdaHttpGateway(greetings_application)
def lambda_handler(event, context):
    return in_lambda(event, context)
{% endhighlight %}

You can even convert application into something that runs in a command line environment:

{% highlight python %}
cli = clearskies.contexts.Cli(greetings_application)
if __name__ == "__main__":
    cli()
{% endhighlight %}

In this last example, you would invoke it like so:

{% highlight bash %}
python my_application.py 'Name Goes Here'
{% endhighlight %}

As mentioned, the context maps input and output for the application.  So, while a web context will look at a URL to fill in URL parameters, the CLI context converts command line arguments into the URL parameters.

## Backends

Another layer of abstraction for infrastructure is the backend system used by the models.  The backend provides a layer of abstraction between the models and your data source so your application can work identically regardless of where the data actually ends up.  Of course, the model system can't account for the intricacies of every kind of data source, so clearskies tries to follow the 80/20 rule and enable the most common use cases.  If needed, it's always possible to inject lower-level primatives to interact with data sources directly.  This is a common strategy in clearskies: automate common use cases and then get out of the way for the rest.  So, for example, the following model stores data in a temporary, in-memory datastore:

```
import clearskies

class User(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    name = clearskies.columns.String()
    username = clearskies.columns.String()
    age = clearskies.columns.Integer()
    created_at = clearskies.columns.Created()
    updated_at = clearskies.columns.Updated()
```

A small change in the backend property adjusts it to fetch and retrive data from MySQL/MariaDB:

```
import clearskies

class User(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.CursorBackend()

    id = clearskies.columns.Uuid()
    name = clearskies.columns.String()
    username = clearskies.columns.String()
    age = clearskies.columns.Integer()
    created_at = clearskies.columns.Created()
    updated_at = clearskies.columns.Updated()
```

Or to really mix things up you can work with a DynamoDB table:

```
import clearskies
import clearskies_aws

class User(clearskies.Model):
    id_column_name = "id"
    backend = clearskies_aws.backends.DynamoDbBackend()

    id = clearskies.columns.Uuid()
    name = clearskies.columns.String()
    username = clearskies.columns.String()
    age = clearskies.columns.Integer()
    created_at = clearskies.columns.Created()
    updated_at = clearskies.columns.Updated()
```

Here's an example application that works with all three of the above model classes to load some data into the datastore and return some records and also highlights some of the different ways of using models:

```
import clearskies

class User(clearskies.Model):
    id_column_name = "id"
    backend = clearskies.backends.MemoryBackend()

    id = clearskies.columns.Uuid()
    name = clearskies.columns.String()
    username = clearskies.columns.String()
    age = clearskies.columns.Integer()
    created_at = clearskies.columns.Created()
    updated_at = clearskies.columns.Updated()

def populate_data(users: User):
    user_1 = users.create({"name": "User 1", "username": "user_1", "age": 15})
    user_1.save({"age": 16})

    user_2 = users.empty()
    user_2.name = "User 2"
    user_2.username = "user_2"
    user_2.age = 22
    user_2.save()
    user_2.age = 25
    user_2.save()

    users.create({"name": "User 3", "username": "user_3", "age": 32})

    return users.where("age<30").sort_by("age", "desc")

cli = clearskies.contexts.Cli(
    clearskies.endpoints.Callable(
        populate_data,
        model_class=User,
        readable_column_names=["id", "name", "age"],
        return_records=True,
    ),
    classes=[User],
)
if __name__ == "__main__":
    cli()
```

The above application creates three records, updates two of them, and then returns all the users with an age less than 30, ordered by age descending.  clearskies will then extract id, name, and age for each matching user and return this in a standard JSON response.
