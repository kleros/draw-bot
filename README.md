# Kleros Draw Bot

Service to find all jurors who deposited tokens in a session and preload their draws into the kleros store cache.

### Usage

For `Python 3.x`

It is recommended that you use a `virtualenv`.

Create a config.py in the format:
```
config = {
    "ETH_PROVIDER": "https://mainnet.infura.io/<api key>",
    "INFURA_API_KEY": "",
    "KLEROS_CONTRACT_ADDRESS": "",
    "ETHERSCAN_API_KEY": ""
}
```

```
pip install requirements.txt
python3 run.py
```

### Notes

- Uses etherscan API to fetch transactions and events
- This daemon will be deprecated with the release of Kleros Athena
