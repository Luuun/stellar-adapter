import os

# Get the Adapter Private Key
STELLAR_SEND_PRIVATE_KEY = os.environ.get('STELLAR_SEND_PRIVATE_KEY', '')

# Get the Address
STELLAR_SEND_ADDRESS = os.environ.get('STELLAR_SEND_ADDRESS', '')

STELLAR_RECEIVE_ADDRESS = os.environ.get('STELLAR_RECEIVE_ADDRESS', '')

# Get the Adapter Network
STELLAR_NETWORK = os.environ.get('STELLAR_NETWORK', '')


# Get the platform URL for the adapter (Rehive)
REHIVE_API_URL = os.environ.get('REHIVE_API_URL', '')

# Get the admin token for platform requests (Rehive)
REHIVE_API_TOKEN = os.environ.get('REHIVE_API_TOKEN', '')

# TODO: Replace this with user accounts and tokens.
ADAPTER_SECRET_KEY = os.environ.get('ADAPTER_SECRET_KEY', 'secret')
