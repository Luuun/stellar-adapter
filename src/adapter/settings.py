import os

STELLAR_SEND_PRIVATE_KEY = os.environ.get('STELLAR_SEND_PRIVATE_KEY', '')
STELLAR_SEND_ADDRESS = os.environ.get('STELLAR_SEND_ADDRESS', '')
STELLAR_RECEIVE_ADDRESS = os.environ.get('STELLAR_RECEIVE_ADDRESS', '')

STELLAR_NETWORK = os.environ.get('STELLAR_NETWORK', '')

# Get the platform URL for the adapter (Rehive)
REHIVE_API_URL = os.environ.get('REHIVE_API_URL', '')

# Get the admin token for platform requests (Rehive)
REHIVE_API_TOKEN = os.environ.get('REHIVE_API_TOKEN', '')

# Purchase webhook secret key
STELLAR_PURCHASE_SECRET_KEY = os.environ.get('STELLAR_PURCHASE_SECRET_KEY', 'secret')

# Withdraw webhook secret key
STELLAR_WITHDRAW_SECRET_KEY = os.environ.get('STELLAR_WITHDRAW_SECRET_KEY', 'secret')

# Deposit webhook secret key
STELLAR_DEPOSIT_SECRET_KEY = os.environ.get('STELLAR_DEPOSIT_SECRET_KEY', 'secret')

# Send webhook secret key
STELLAR_SEND_SECRET_KEY = os.environ.get('STELLAR_SEND_SECRET_KEY', 'secret')

# Adapter secret key
STELLAR_ADAPTER_SECRET_KEY = os.environ.get('STELLAR_ADAPTER_SECRET_KEY', 'secret')
