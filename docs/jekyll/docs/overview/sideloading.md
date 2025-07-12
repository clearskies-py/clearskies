---
layout: default
title: Sideloading
parent: Overview
permalink: /docs/overview/sideloading.html
nav_order: 6
---

# Sideloading

Every aspect of clearskies is meant to be modified.  You can easily drop in new behavior with a single line of configuration. Take a simple example of an API endpoint that loads data from a database:

{% highlight python %}
import clearskies

my_api = clearskies.Application(
    clearskies.handlers.RestfulAPI,
    {
        'authentication': clearskies.authentication.public(),
        'model_class': models.MyModelHere,
        'readable_columns': ['name', 'description', 'price', 'created', 'updated'],
        'writeable_columns': ['name', 'description', 'price'],
        'searchable_columns': ['name', 'description', 'price'],
        'default_sort_column': 'name',
    },
    binding_modules=[models]
)
{% endhighlight %}

By default, clearskies will look for database credentials in the environment or a `.env` file and attempt to connect to the database directly.  What if you're using an RDS in AWS and want to connect using [IAM DB Auth](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html), so that you don't need a static password?  Well, you just need [a few lines of code](https://github.com/cmancone/clearskies-aws/blob/master/src/clearskies_aws/secrets/additional_configs/iam_db_auth.py) and then change a single line of your application (note the `additional_configs` kwarg at the bottom):

{% highlight python %}
import clearskies
import clearskies_aws

my_api = clearskies.Application(
    clearskies.handlers.RestfulAPI,
    {
        'authentication': clearskies.authentication.public(),
        'model_class': models.MyModelHere,
        'readable_columns': ['name', 'description', 'price', 'created', 'updated'],
        'writeable_columns': ['name', 'description', 'price'],
        'searchable_columns': ['name', 'description', 'price'],
        'default_sort_column': 'name',
    },
    binding_modules=[models],
    additional_configs=[clearskies_aws.secrets.additional_configs.iam_db_auth()]
)
{% endhighlight %}

Do you need different logic for connecting to a database when in the production environment vs running locally?  No problem.  You can combine this ease-of-configuration with the context-neutral nature of clearskies.  Take the example of the `my_api` we defined above: it uses IAM DB Auth as the default application behavior.  Therefore, for a lambda running in production you would use it like so:

{% highlight python %}
my_api_behind_an_api_gateway = clearskies_aws.contexts.lambda_api_gateway(my_api)
def lambda_handler(event, context):
    return my_api_behind_an_api_gateway(event, context)
{% endhighlight %}

and then you would just set the `lambda_handler` function as the lambda handler.  If you ran this locally behind a WSGI server and wanted to use dynamic credentials and connect to the database using SSH with certificate-based authentication, you would just:

{% highlight python %}
my_api_behind_wsgi = clearskies.contexts.wsgi(
    my_api,
    additional_configs=clearskies.secrets.additional_configs.mysql_connection_dynamic_producer_via_ssh_cert_bastion()
)
def application(env, start_response):
    return my_api_behind_wsgi(env, start_response)
{% endhighlight %}

You would set the `application` function as your WSGI handler and then, as calls came in locally, clearskies would open the SSH connection, fetch database credentials, connect through the bastion, and your application would work exactly the same.
