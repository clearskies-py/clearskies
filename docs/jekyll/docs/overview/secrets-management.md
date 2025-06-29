---
layout: default
title: Secrets Management
parent: Overview
permalink: /docs/overview/secrets-management.html
nav_order: 5
---

# Secrets Management

clearskies integrates tightly with your secret management system to bring secrets back _into_ the application. Most applications work by pulling secrets from the environment when they launch.  You can do that with clearskies if you want, but clearskies is designed to fetch secrets directly from your secret manager as needed.  This allows it to automatically detect when credentials are rotated and so refresh credentials without interruption.  It also allows it to work easily with dynamic/short lived credentials.  Other than the direct benefits of simplifying credential management, this also dramatically simplifies the process of application bootstrapping.  Often, running an application locally for the first time starts with the process of collecting the necessary credentials and configuring the application environment.  This inevitably leads to secret sprawl, which remains a leading cause of data breaches.  With clearskies, you just need to ensure that the application has permission to access your secret manager, and then it will bootstrap itself.
