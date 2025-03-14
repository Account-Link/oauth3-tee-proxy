# Scratchpad

This is intended as an ultralight PM tool to coordinate the current context and todos.

## Issues I found

- [X] Policy seems to have some issue. Adding `twitter.graphql.read` will not allow me to use read only endpoint like HomeTimeline. I need `twitter.graphql` `twitter.graphql.read` both present to allow myself to access the endpoint. (Note from Dan: I'm reworking this to not use scopes and rely on policies instead.)
- [-] twitter API is incorrectly initializing cookie client, which should only be used with GraphQL. (Note from Dan: I'm reworking this to not use cookies and rely on the JWT token instead.)

## TODO:

- [ ] The twitter cookie saving isn't working. It's not successfully validating the cookie.
- [ ] Remove all knowledge of the twitter and telegram plugins from the codebase. The plugins should be registering themselves, their routes, and their UI. If there are any authorization requirements for routes provided by the plugins, they should be handled by the plugin.
- [ ] The email, phone number and base wallet fields aren't working on the profile page.
