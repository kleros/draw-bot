import json
import time
import os
import requests

from config import config

os.environ['INFURA_API_KEY'] = config["INFURA_API_KEY"]
from web3.auto.infura import w3


def get_new_period_event_logs_for_session(session):
    # new period topic
    topic0 = w3.sha3(text='NewPeriod(uint8,uint256)').hex()
    session_hex = w3.toHex(session).split('0x')[1]
    topic1 = '0x' + '0' * (64 - len(session_hex)) + session_hex

    response = requests.get('https://api.etherscan.io/api?module=logs&action=getLogs&fromBlock=379224&toBlock=latest&address=%s&topic0=%s&topic0_1_opr=and&topic1=%s&apikey=%s' % (config['KLEROS_CONTRACT_ADDRESS'], topic0, topic1, config['ETHERSCAN_API_KEY']))
    logs = response.json()

    return logs["result"]

def get_activation_period_block_range(session):
    session_logs = get_new_period_event_logs_for_session(session)
    assert(len(session_logs) >= 2)

    fromBlock = 0
    toBlock = 0
    for log in session_logs:
        if int(log["data"], 16) == 0:
            fromBlock = int(log["blockNumber"], 16)
        elif int(log["data"], 16) == 1:
            toBlock = int(log["blockNumber"], 16)

    return (fromBlock, toBlock)

def get_transactions_in_block_range(fromBlock, toBlock):
    response = requests.get('http://api.etherscan.io/api?module=account&action=txlist&address=%s&startblock=%d&endblock=%d&sort=asc&apikey=%s' % (config['KLEROS_CONTRACT_ADDRESS'], fromBlock, toBlock, config['ETHERSCAN_API_KEY']))
    logs = response.json()

    return logs["result"]

if __name__ == "__main__":
    assert(w3.isConnected())

    run = True

    # contract
    kleros_json = open(file='contracts/Kleros.json', encoding='utf-8')
    abi = json.loads(kleros_json.read())['abi']
    kleros_contract = w3.eth.contract(
        address=w3.toChecksumAddress(config['KLEROS_CONTRACT_ADDRESS']),
        abi=abi
    )

    closed_disputes = {}
    lastSessionUpdated = -1
    while run:
        try:
            session = kleros_contract.call().session()
            period = kleros_contract.call().period()

            if period == 2 and session > lastSessionUpdated:
                activated_users = []
                fromBlock, toBlock = get_activation_period_block_range(session)
                txs = get_transactions_in_block_range(fromBlock, toBlock)

                for tx in txs:
                    if (kleros_contract.decode_function_input(tx["input"])[0].__dict__["abi"]["name"] == "activateTokens"):
                        activated_users.append(tx["from"])

                # get new open disputes
                open_disputes = []
                check_disputes = True
                dispute_id = 0
                number_of_jurors_drawn = 0
                while check_disputes:
                    if closed_disputes.get(dispute_id):
                        continue
                    try:
                        dispute = kleros_contract.call().disputes(dispute_id)
                        if dispute[1] + dispute[2] == session:
                            open_disputes.append((dispute_id, dispute[2]))
                        else:
                            closed_disputes[dispute_id] = True
                    except:
                        check_disputes = False
                    dispute_id += 1

                for user in activated_users:
                    for dispute in open_disputes:
                        disputeID = dispute[0]
                        appeal = dispute[1]
                        draws = []
                        number_of_jurors = kleros_contract.functions.amountJurors(disputeID).call()
                        for draw in range(number_of_jurors):
                            is_drawn = kleros_contract.functions.isDrawn(disputeID, w3.toChecksumAddress(user), draw).call()
                            if is_drawn:
                                draws.append(draw)

                        if len(draws) > 0:
                            number_of_jurors_drawn += 1
                            r = requests.post('https://kleros.in/%s/aribtrators/%s/disputes/%d/draws' % (user, config['KLEROS_CONTRACT_ADDRESS'], disputeID), data = {"draws": draws, "appeal": appeal})
                            if r.status_code == 201:
                                requests.post('https://kleros.in/%s/session' % user, data = {"session": session})

                if number_of_jurors_drawn > 0:
                    print("processed session %d" % session)
                    lastSessionUpdated = session
                else:
                    print("unable to fetch draws for any jurors -- sleeping")
                    time.sleep(3600) # infura problems? sleep for an hour
                    continue

            time.sleep(300) # sleep for 5 minutes between iterations
        except:
            print("error -- sleeping")
            time.sleep(60) # error? restart after a minute
            continue
