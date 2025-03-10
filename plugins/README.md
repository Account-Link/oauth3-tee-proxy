# OAuth3 TEE Proxy Plugin System

The OAuth3 TEE Proxy uses a plugin architecture to support multiple resource servers and authentication methods.

## Plugin Types

There are two types of plugins:

1. **Authorization Plugins**: Handle authentication and credential management for resource servers
2. **Resource Plugins**: Handle interactions with resource server APIs

## Plugin Structure

Each integration (e.g., Twitter, Telegram) should have its own directory in the `plugins` folder, with:

- `__init__.py`: Imports and registers the plugin components
- `auth.py`: Contains the AuthorizationPlugin implementation
- `resource.py`: Contains the ResourcePlugin implementation

## Creating a New Plugin

To add support for a new service:

1. Create a new directory in the `plugins` folder (e.g., `plugins/facebook/`)
2. Implement an AuthorizationPlugin in `auth.py`
3. Implement a ResourcePlugin in `resource.py`
4. Create an `__init__.py` that imports and registers the plugins

The system will automatically discover and load your plugin when the application starts.

## Example Plugin Structure

```
plugins/
├── __init__.py          # Base plugin system
├── twitter/
│   ├── __init__.py      # Registers Twitter plugins
│   ├── auth.py          # TwitterAuthorizationPlugin
│   └── resource.py      # TwitterResourcePlugin
└── telegram/
    ├── __init__.py      # Registers Telegram plugins
    ├── auth.py          # TelegramAuthorizationPlugin
    └── resource.py      # TelegramResourcePlugin
```

## Plugin Interfaces

Each plugin must implement the base interfaces defined in `plugins/__init__.py`:

- `AuthorizationPlugin`: For handling authentication and credentials
- `ResourcePlugin`: For interacting with APIs and defining available scopes

## Documentation

See the docstrings in `plugins/__init__.py` for detailed information on the methods that need to be implemented for each plugin type.