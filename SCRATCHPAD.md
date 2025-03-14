# Scratchpad

This is intended as an ultralight PM tool to coordinate the current context and todos.

## Issues I found

* Policy seems to have some issue. Adding `twitter.graphql.read` will not allow me to use read only endpoint like HomeTimeline. I need `twitter.graphql` `twitter.graphql.read` both present to allow myself to access the endpoint.
* twitter API is incorrectly initializing cookie client, which should only be used with GraphQL.
