#!/usr/bin/env python3
# Copyright (c) 2014-2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from test_framework.betting_opcode import *
from test_framework.authproxy import JSONRPCException
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import wait_until, rpc_port, assert_equal, assert_raises_rpc_error, sync_blocks
from distutils.dir_util import copy_tree, remove_tree
from decimal import *
import pprint
import time
import os
import ctypes

WGR_WALLET_ORACLE = { "addr": "TXuoB9DNEuZx1RCfKw3Hsv7jNUHTt4sVG1", "key": "TBwvXbNNUiq7tDkR2EXiCbPxEJRTxA1i6euNyAE9Ag753w36c1FZ" }
WGR_WALLET_EVENT = { "addr": "TFvZVYGdrxxNunQLzSnRSC58BSRA7si6zu", "key": "TCDjD2i4e32kx2Fc87bDJKGBedEyG7oZPaZfp7E1PQG29YnvArQ8" }
WGR_WALLET_DEV = { "addr": "TLuTVND9QbZURHmtuqD5ESECrGuB9jLZTs", "key": "TFCrxaUt3EjHzMGKXeBqA7sfy3iaeihg5yZPSrf9KEyy4PHUMWVe" }
WGR_WALLET_OMNO = { "addr": "THofaueWReDjeZQZEECiySqV9GP4byP3qr", "key": "TDJnwRkSk8JiopQrB484Ny9gMcL1x7bQUUFFFNwJZmmWA7U79uRk" }

sport_names = ["Sport1", "Horse racing", "F1 racing"]
round_names = ["round0", "round1",]
tournament_names = ["Tournament1", "The BMW stakes", "F1 Cup"]
contender_names = ["cont1", "cont2",
    "horse1", "horse2", "horse3", "horse4", "horse5",
    "Alexander Albon", "Daniil Kvyat", "Pierre Gasly", "Romain Grosjean", "Antonio Maria Giovinazzi",
    "horse6", "horse7", "horse8", "horse9"
]

# Field event groups
other_group = 1
animal_racing_group = 2

# Field bet market types
market_outright = 1
market_place    = 2
market_show     = 3

# Contender result types
DNF    = 0
place1 = 1
place2 = 2
place3 = 3
DNR    = 101

ODDS_DIVISOR = 10000
BETX_PERMILLE = 60


def calculate_odds(odds_type, contenders, mrg_in_percent):
    N = len(contenders)
    if odds_type == "place":
        if N < 5:
            for contender in contenders.values():
                contender[odds_type] = 0
            return
        multiplier = 2
    elif odds_type == "show":
        if N < 8:
            for contender in contenders.values():
                contender[odds_type] = 0
            return
        multiplier = 3
    else:
        raise Exception("Wrong odds type")

    contenders_p = {}
    for k, v in contenders.items():
        contenders_p[k] = 1 / (v["outright"] / ODDS_DIVISOR)

    h = 0.000001

    real_mrg_in = (mrg_in_percent / 100) * multiplier

    # calc m
    m = 1
    md = m + h
    ms = m - h
    for i in range(1, N):
        f = 0
        for cont_k in contenders_p.keys():
            f += contenders_p[cont_k] ** (m + contenders[cont_k]["mod"])
        f -= real_mrg_in

        fd = 0
        for cont_k in contenders_p.keys():
            fd += contenders_p[cont_k] ** (md + contenders[cont_k]["mod"])
        fd -= real_mrg_in

        fs = 0
        for cont_k in contenders_p.keys():
            fs += contenders_p[cont_k] ** (ms + contenders[cont_k]["mod"])
        fs -= real_mrg_in

        der = (fd - fs) / h

        m = m - (f / der)
        md = m + h
        ms = m - h

    # calc X
    X = 1
    Xd = X + h
    Xs = X - h
    for i in range(1, N):
        f = 0
        for cont_k in contenders.keys():
            f += 1 / (1 + (X + contenders[cont_k]["mod"]) * (contenders[cont_k]["outright"] / ODDS_DIVISOR - 1))
        f -= real_mrg_in

        fd = 0
        for cont_k in contenders.keys():
            fd += 1 / (1 + (Xd + contenders[cont_k]["mod"]) * (contenders[cont_k]["outright"] / ODDS_DIVISOR - 1))
        fd -= real_mrg_in

        fs = 0
        for cont_k in contenders.keys():
            fs += 1 / (1 + (Xs + contenders[cont_k]["mod"]) * (contenders[cont_k]["outright"] / ODDS_DIVISOR - 1))
        fs -= real_mrg_in

        der = (fd - fs) / h

        X = X - (f / der)
        Xd = X + h
        Xs = X - h

    # print("odds_type = ", odds_type)
    # print("N = ", N)
    # print("real_mrg_in = ", real_mrg_in)
    # print("m = ", m)
    # print("X = ", X)

    for cont_k in contenders.keys():
        odds_x = 1 + (X + contenders[cont_k]["mod"]) * (contenders[cont_k]["outright"] / ODDS_DIVISOR - 1)
        odds_m = contenders_p[cont_k] ** (-m - contenders[cont_k]["mod"])
        contenders[cont_k][odds_type] = int(((odds_x + odds_m) / 2) * ODDS_DIVISOR)

def check_calculate_odds():
    contenders = {
        1 : { "outright" : 36699, "mod" : 0 },
        2 : { "outright" : 26152, "mod" : 0 },
        3 : { "outright" : 17617, "mod" : 0 },
        4 : { "outright" : 158265, "mod" : 0 },
        5 : { "outright" : 93296, "mod" : 0 },
        6 : { "outright" : 93296, "mod" : 0 },
        7 : { "outright" : 158265, "mod" : 0 },
        8 : { "outright" : 60873, "mod" : 0 },
        9 : { "outright" : 36699, "mod" : 0 },
    }
    mrg_in_percent = 115

    calculate_odds("place", contenders, mrg_in_percent)
    for k in contenders.keys():
        print(contenders[k])

    calculate_odds("show", contenders, mrg_in_percent)
    for k in contenders.keys():
        print(contenders[k])

    contenders = {
        1 : { "outright" : 66667, "mod" : 0 },
        2 : { "outright" : 66667, "mod" : 0 },
        3 : { "outright" : 50000, "mod" : 0 },
        4 : { "outright" : 40000, "mod" : 0 },
        5 : { "outright" : 40000, "mod" : 0 },
    }
    mrg_in_percent = 115
    calculate_odds("place", contenders, mrg_in_percent)
    for k in contenders.keys():
        print(contenders[k])

    calculate_odds("show", contenders, mrg_in_percent)
    for k in contenders.keys():
        print(contenders[k])


def check_bet_payouts_info(listbets, listpayoutsinfo):
    for bet in listbets:
        info_found = False
        for info in listpayoutsinfo:
            info_type = info['payoutInfo']['payoutType']
            if info_type == 'Betting Payout' or info_type == 'Betting Refund':
                if info['payoutInfo']['betBlockHeight'] == bet['betBlockHeight']:
                    if info['payoutInfo']['betTxHash'] == bet['betTxHash']:
                        if info['payoutInfo']['betTxOut'] == bet['betTxOut']:
                            info_found = True
        assert(info_found)

class BettingTest(BitcoinTestFramework):
    def get_node_setting(self, node_index, setting_name):
        with open(os.path.join(self.nodes[node_index].datadir, "wagerr.conf"), 'r', encoding='utf8') as f:
            for line in f:
                if line.startswith(setting_name + "="):
                    return line.split("=")[1].strip("\n")
        return None

    def get_local_peer(self, node_index, is_rpc=False):
        port = self.get_node_setting(node_index, "rpcport" if is_rpc else "port")
        return "127.0.0.1:" + str(rpc_port(node_index) if port is None else port)

    def set_test_params(self):
        # 0 - main node
        # 1 - oracle
        # 2 - player1
        # 3 - player2
        # 4 - revert testing
        self.num_nodes = 5
        self.extra_args = [[] for n in range(self.num_nodes)]
        self.setup_clean_chain = True
        self.players = []
        # { event_id : { contender_id : odds, ... } }
        self.odds_events = {}

    def connect_network(self):
        for i in range(len(self.nodes)):
            for j in range(len(self.nodes)):
                if i == j:
                    continue
                self.nodes[i].addnode(self.get_local_peer(j), "onetry")
                wait_until(lambda:  all(peer['version'] != 0 for peer in self.nodes[i].getpeerinfo()))
        self.sync_all()
        for n in range(self.num_nodes):
            idx_l = n
            idx_r = n + 1 if n + 1 < self.num_nodes else 0
            assert_equal(self.nodes[idx_l].getblockcount(), self.nodes[idx_r].getblockcount())

    def connect_and_sync_blocks(self):
        # for i in range(self.num_nodes):
        #     self.stop_node(i)

        # for i in range(self.num_nodes):
        #     self.nodes[i].rpchost = self.get_local_peer(i, True)
        #     self.nodes[i].start()
        #     self.nodes[i].wait_for_rpc_connection()

        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                if i == j:
                    continue
                self.nodes[i].addnode(self.get_local_peer(j), "onetry")
                wait_until(lambda:  all(peer['version'] != 0 for peer in self.nodes[i].getpeerinfo()))
        # self.sync_all()
        sync_blocks(self.nodes)

    def setup_network(self):
        self.log.info("Setup Network")
        self.setup_nodes()
        self.connect_network()

    def check_minting(self, block_count=250):
        self.log.info("Check Minting...")

        self.nodes[1].importprivkey(WGR_WALLET_ORACLE['key'])
        self.nodes[1].importprivkey(WGR_WALLET_EVENT['key'])
        self.nodes[1].importprivkey(WGR_WALLET_DEV['key'])
        self.nodes[1].importprivkey(WGR_WALLET_OMNO['key'])

        self.players.append(self.nodes[2].getnewaddress('Node2Addr'))
        self.players.append(self.nodes[3].getnewaddress('Node3Addr'))
        node4Addr = self.nodes[4].getnewaddress('Node4Addr')
        self.log.info("node4Addr = " + str(node4Addr))
        self.log.info("player1 addr = " + str(self.players[0]))
        self.log.info("player2 addr = " + str(self.players[1]))

        for i in range(block_count - 1):
            blocks = self.nodes[0].generate(1)
            blockinfo = self.nodes[0].getblock(blocks[0])
            # get coinbase tx
            rawTx = self.nodes[0].getrawtransaction(blockinfo['tx'][0])
            decodedTx = self.nodes[0].decoderawtransaction(rawTx)
            address = decodedTx['vout'][0]['scriptPubKey']['addresses'][0]
            if (i > 0):
                # minting must process to sigle address
                assert_equal(address, prevAddr)
            prevAddr = address

        for i in range(20):
            self.nodes[0].sendtoaddress(WGR_WALLET_ORACLE['addr'], 2000)
            self.nodes[0].sendtoaddress(WGR_WALLET_EVENT['addr'], 2000)
            self.nodes[0].sendtoaddress(self.players[0], 2000)
            self.nodes[0].sendtoaddress(self.players[1], 2000)

        for i in range(30):
            self.nodes[0].sendtoaddress(node4Addr, 2000)

        self.nodes[0].generate(51)
        self.sync_all()

        for n in range(self.num_nodes):
            assert_equal( self.nodes[n].getblockcount(), 300)

        assert_equal(self.nodes[1].getbalance(), 80000) # oracle
        assert_equal(self.nodes[2].getbalance(), 40000) # player1
        assert_equal(self.nodes[3].getbalance(), 40000) # player2
        assert_equal(self.nodes[4].getbalance(), 60000) # revert node

        self.log.info("Minting Success")

    def check_mapping(self):
        self.log.info("Check Mapping...")

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        assert_raises_rpc_error(-1, "No mapping exist for the mapping index you provided.", self.nodes[0].getmappingid, "", "")
        assert_raises_rpc_error(-1, "No mapping exist for the mapping index you provided.", self.nodes[0].getmappingname, "abc123", 0)

        for id in range(len(sport_names)):
            mapping_opcode = make_mapping(INDIVIDUAL_SPORT_MAPPING, id, sport_names[id])
            post_opcode(self.nodes[1], mapping_opcode, WGR_WALLET_ORACLE['addr'])
        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        for id in range(len(round_names)):
            mapping_opcode = make_mapping(ROUND_MAPPING, id, round_names[id])
            post_opcode(self.nodes[1], mapping_opcode, WGR_WALLET_ORACLE['addr'])
        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        for id in range(len(contender_names)):
            mapping_opcode = make_mapping(CONTENDER_MAPPING, id, contender_names[id])
            post_opcode(self.nodes[1], mapping_opcode, WGR_WALLET_ORACLE['addr'])
        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        for id in range(len(tournament_names)):
            mapping_opcode = make_mapping(TOURNAMENT_MAPPING, id, tournament_names[id])
            post_opcode(self.nodes[1], mapping_opcode, WGR_WALLET_ORACLE['addr'])
        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        for node in self.nodes:
            # Check sports mapping
            for id in range(len(sport_names)):
                mapping = node.getmappingname("individualSports", id)[0]
                assert_equal(mapping['exists'], True)
                assert_equal(mapping['mapping-name'], sport_names[id])
                assert_equal(mapping['mapping-type'], "individualSports")
                assert_equal(mapping['mapping-index'], id)
                mappingid = node.getmappingid("individualSports", sport_names[id])[0]
                assert_equal(mappingid['exists'], True)
                assert_equal(mappingid['mapping-index'], "individualSports")
                assert_equal(mappingid['mapping-id'], id)

            # Check rounds mapping
            for id in range(len(round_names)):
                mapping = node.getmappingname("rounds", id)[0]
                assert_equal(mapping['exists'], True)
                assert_equal(mapping['mapping-name'], round_names[id])
                assert_equal(mapping['mapping-type'], "rounds")
                assert_equal(mapping['mapping-index'], id)
                mappingid = node.getmappingid("rounds", round_names[id])[0]
                assert_equal(mappingid['exists'], True)
                assert_equal(mappingid['mapping-index'], "rounds")
                assert_equal(mappingid['mapping-id'], id)

            # Check teams mapping
            for id in range(len(contender_names)):
                mapping = node.getmappingname("contenders", id)[0]
                assert_equal(mapping['exists'], True)
                assert_equal(mapping['mapping-name'], contender_names[id])
                assert_equal(mapping['mapping-type'], "contenders")
                assert_equal(mapping['mapping-index'], id)
                mappingid = node.getmappingid("contenders", contender_names[id])[0]
                assert_equal(mappingid['exists'], True)
                assert_equal(mappingid['mapping-index'], "contenders")
                assert_equal(mappingid['mapping-id'], id)

            # Check tournaments mapping
            for id in range(len(tournament_names)):
                mapping = node.getmappingname("tournaments", id)[0]
                assert_equal(mapping['exists'], True)
                assert_equal(mapping['mapping-name'], tournament_names[id])
                assert_equal(mapping['mapping-type'], "tournaments")
                assert_equal(mapping['mapping-index'], id)
                mappingid = node.getmappingid("tournaments", tournament_names[id])[0]
                assert_equal(mappingid['exists'], True)
                assert_equal(mappingid['mapping-index'], "tournaments")
                assert_equal(mappingid['mapping-id'], id)

        self.log.info("Mapping Success")

    def check_event(self):
        self.log.info("Check Event creation...")
        start_time = int(time.time() + 60 * 60)

        # Bad case
        field_event_opcode = make_field_event(
            0,
            start_time,
            100, # bad group
            sport_names.index("Sport1"),
            tournament_names.index("Tournament1"),
            round_names.index("round0"),
            {
                contender_names.index("cont1") : 15000,
                contender_names.index("cont2") : 18000,
            }
        )
        assert_raises_rpc_error(-25, "",
            post_opcode, self.nodes[1], field_event_opcode, WGR_WALLET_ORACLE['addr'])

        # Test revert
        self.stop_node(4)

        field_event_opcode = make_field_event(
            0,
            start_time,
            other_group,
            sport_names.index("Sport1"),
            tournament_names.index("Tournament1"),
            round_names.index("round0"),
            {
                contender_names.index("cont1") : 15000,
                contender_names.index("cont2") : 18000,
            }
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        assert_raises_rpc_error(-25, "",
            post_opcode, self.nodes[1], field_event_opcode, WGR_WALLET_ORACLE['addr'])

        for node in self.nodes[0:4]:
            list_events = node.listfieldevents()
            assert_equal(len(list_events), 1)
            event_id = list_events[0]['event_id']
            assert_equal(list_events[0]['sport'], "Sport1")
            assert_equal(list_events[0]['tournament'], "Tournament1")
            assert_equal(list_events[0]['round'], "round0")
            assert_equal(len(list_events[0]['contenders']), 2)
            assert_equal(list_events[0]['contenders'][0]['name'], "cont1")
            assert_equal(list_events[0]['contenders'][0]['outright-odds'], 15000)
            assert_equal(list_events[0]['contenders'][0]['place-odds'], 15000)
            assert_equal(list_events[0]['contenders'][0]['show-odds'], 15000)
            assert_equal(list_events[0]['contenders'][1]['name'], "cont2")
            assert_equal(list_events[0]['contenders'][1]['outright-odds'], 18000)
            assert_equal(list_events[0]['contenders'][1]['place-odds'], 18000)
            assert_equal(list_events[0]['contenders'][1]['show-odds'], 18000)

        self.log.info("Revering...")
        self.nodes[4].rpchost = self.get_local_peer(4, True)
        self.nodes[4].start()
        self.nodes[4].wait_for_rpc_connection()
        self.log.info("Generate blocks...")
        for i in range(5):
            self.nodes[4].generate(1)
            time.sleep(0.5)

        assert_equal(len(self.nodes[4].listfieldevents()), 0)

        self.log.info("Connect and sync nodes...")
        self.connect_and_sync_blocks() # TODO: fix sync_mempools

        for node in self.nodes:
            assert_equal(len(node.listfieldevents()), 0)

        self.log.info("Event creation Success")

    def check_event_update_odds(self):
        self.log.info("Check Event Update Odds...")
        start_time = int(time.time() + 60 * 60)

        for node in self.nodes:
            assert_equal(len(node.listfieldevents()), 0)

        # Create event
        field_event_opcode = make_field_event(
            0,
            start_time,
            other_group,
            sport_names.index("Sport1"),
            tournament_names.index("Tournament1"),
            round_names.index("round0"),
            {
                contender_names.index("cont1") : 15000
            }
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        for node in self.nodes:
            list_events = node.listfieldevents()
            assert_equal(len(list_events), 1)

        saved_event = self.nodes[0].listfieldevents()[0]
        assert_equal(saved_event['event_id'], 0)
        assert_equal(len(saved_event['contenders']), 1)
        assert_equal(saved_event['contenders'][0]['name'], "cont1")
        assert_equal(saved_event['contenders'][0]['outright-odds'], 15000)
        assert_equal(saved_event['contenders'][0]['place-odds'], 15000)
        assert_equal(saved_event['contenders'][0]['show-odds'], 15000)

        # For revert test
        self.stop_node(4)

        field_update_odds_opcode = make_field_update_odds(
            0,
            {
                contender_names.index("cont1") : 18000,
                100 : 15000 # bad contender_id
            }
        )
        assert_raises_rpc_error(-25, "",
            post_opcode, self.nodes[1], field_update_odds_opcode, WGR_WALLET_ORACLE['addr'])

        field_update_odds_opcode = make_field_update_odds(
            100, # bad event_id
            {
                contender_names.index("cont1") : 18000
            }
        )
        assert_raises_rpc_error(-25, "",
            post_opcode, self.nodes[1], field_update_odds_opcode, WGR_WALLET_ORACLE['addr'])

        # Update odds for event
        field_update_odds_opcode = make_field_update_odds(
            0,
            {
                contender_names.index("cont1") : 18000
            }
        )
        post_opcode(self.nodes[1], field_update_odds_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        for node in self.nodes[0:4]:
            list_events = node.listfieldevents()
            assert_equal(len(list_events), 1)
            assert_equal(len(list_events[0]['contenders']), 1)
            assert_equal(list_events[0]['contenders'][0]['name'], "cont1")
            assert_equal(list_events[0]['contenders'][0]['outright-odds'], 18000)
            assert_equal(list_events[0]['contenders'][0]['place-odds'], 18000)
            assert_equal(list_events[0]['contenders'][0]['show-odds'], 18000)

        field_update_odds_opcode = make_field_update_odds(0, {
                contender_names.index("cont2") : 13000 # Add new conteder
            }
        )
        post_opcode(self.nodes[1], field_update_odds_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        for node in self.nodes[0:4]:
            list_events = node.listfieldevents()
            assert_equal(len(list_events), 1)
            assert_equal(len(list_events[0]['contenders']), 2)
            assert_equal(list_events[0]['contenders'][0]['name'], "cont1")
            assert_equal(list_events[0]['contenders'][0]['outright-odds'], 18000)
            assert_equal(list_events[0]['contenders'][0]['place-odds'], 18000)
            assert_equal(list_events[0]['contenders'][0]['show-odds'], 18000)
            assert_equal(list_events[0]['contenders'][1]['name'], "cont2")
            assert_equal(list_events[0]['contenders'][1]['outright-odds'], 13000)
            assert_equal(list_events[0]['contenders'][1]['place-odds'], 13000)
            assert_equal(list_events[0]['contenders'][1]['show-odds'], 13000)

        field_update_odds_opcode = make_field_update_odds(0, {
                contender_names.index("cont2") : 19000,
                contender_names.index("horse1") : 12000 # Add new conteder
            }
        )
        post_opcode(self.nodes[1], field_update_odds_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        for node in self.nodes[0:4]:
            list_events = node.listfieldevents()
            assert_equal(len(list_events), 1)
            assert_equal(len(list_events[0]['contenders']), 3)
            assert_equal(list_events[0]['contenders'][0]['name'], "cont1")
            assert_equal(list_events[0]['contenders'][0]['outright-odds'], 18000)
            assert_equal(list_events[0]['contenders'][0]['place-odds'], 18000)
            assert_equal(list_events[0]['contenders'][0]['show-odds'], 18000)
            assert_equal(list_events[0]['contenders'][1]['name'], "cont2")
            assert_equal(list_events[0]['contenders'][1]['outright-odds'], 19000)
            assert_equal(list_events[0]['contenders'][1]['place-odds'], 19000)
            assert_equal(list_events[0]['contenders'][1]['show-odds'], 19000)
            assert_equal(list_events[0]['contenders'][2]['name'], "horse1")
            assert_equal(list_events[0]['contenders'][2]['outright-odds'], 12000)
            assert_equal(list_events[0]['contenders'][2]['place-odds'], 12000)
            assert_equal(list_events[0]['contenders'][2]['show-odds'], 12000)

        self.log.info("Revering...")
        self.nodes[4].rpchost = self.get_local_peer(4, True)
        self.nodes[4].start()
        self.nodes[4].wait_for_rpc_connection()
        self.log.info("Generate blocks...")
        for i in range(5):
            self.nodes[4].generate(1)
            time.sleep(0.5)

        self.log.info("Connect and sync nodes...")
        self.connect_and_sync_blocks()

        # Check event not updated
        for node in self.nodes:
            list_events = node.listfieldevents()
            assert_equal(len(list_events), 1)
            assert_equal(len(list_events[0]['contenders']), 1)
            assert_equal(saved_event['contenders'][0]['name'], list_events[0]['contenders'][0]['name'])
            assert_equal(saved_event['contenders'][0]['outright-odds'], list_events[0]['contenders'][0]['outright-odds'])
            assert_equal(saved_event['contenders'][0]['place-odds'], list_events[0]['contenders'][0]['place-odds'])
            assert_equal(saved_event['contenders'][0]['show-odds'], list_events[0]['contenders'][0]['show-odds'])

        self.log.info("Field Event Odds Success")

    def check_event_zeroing_odds(self):
        self.log.info("Check Field Zeroing Odds...")
        start_time = int(time.time() + 60 * 60)

        field_event_opcode = make_field_event(
            1,
            start_time,
            animal_racing_group,
            sport_names.index("Sport1"),
            tournament_names.index("Tournament1"),
            round_names.index("round0"),
            {
                contender_names.index("cont1")  : 15000,
                contender_names.index("cont2")  : 16000,
                contender_names.index("horse1") : 17000,
                contender_names.index("horse2") : 18000,
                contender_names.index("horse3") : 19000,
            }
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        # For revert test
        self.stop_node(4)

        field_zeroing_opcode = make_field_zeroing_odds(100) # bad event_id
        assert_raises_rpc_error(-25, "",
            post_opcode, self.nodes[1], field_zeroing_opcode, WGR_WALLET_ORACLE['addr'])

        field_zeroing_opcode = make_field_zeroing_odds(1)
        post_opcode(self.nodes[1], field_zeroing_opcode, WGR_WALLET_ORACLE['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        for node in self.nodes[0:4]:
            list_events = node.listfieldevents()
            for event in list_events:
                if event['event_id'] != 1:
                    continue
                assert_equal(len(event['contenders']), 5)
                assert_equal(event['contenders'][0]['name'], "cont1")
                assert_equal(event['contenders'][0]['outright-odds'], 0)
                assert_equal(event['contenders'][0]['place-odds'], 0)
                assert_equal(event['contenders'][0]['show-odds'], 0)
                assert_equal(event['contenders'][1]['name'], "cont2")
                assert_equal(event['contenders'][1]['outright-odds'], 0)
                assert_equal(event['contenders'][1]['place-odds'], 0)
                assert_equal(event['contenders'][1]['show-odds'], 0)
                assert_equal(event['contenders'][2]['name'], "horse1")
                assert_equal(event['contenders'][2]['outright-odds'], 0)
                assert_equal(event['contenders'][2]['place-odds'], 0)
                assert_equal(event['contenders'][2]['show-odds'], 0)
                assert_equal(event['contenders'][3]['name'], "horse2")
                assert_equal(event['contenders'][3]['outright-odds'], 0)
                assert_equal(event['contenders'][3]['place-odds'], 0)
                assert_equal(event['contenders'][3]['show-odds'], 0)
                assert_equal(event['contenders'][4]['name'], "horse3")
                assert_equal(event['contenders'][4]['outright-odds'], 0)
                assert_equal(event['contenders'][4]['place-odds'], 0)
                assert_equal(event['contenders'][4]['show-odds'], 0)

        self.log.info("Revering...")
        self.nodes[4].rpchost = self.get_local_peer(4, True)
        self.nodes[4].start()
        self.nodes[4].wait_for_rpc_connection()
        self.log.info("Generate blocks...")
        for i in range(5):
            self.nodes[4].generate(1)
            time.sleep(0.5)

        self.log.info("Connect and sync nodes...")
        self.connect_and_sync_blocks()

        for node in self.nodes:
            list_events = node.listfieldevents()
            for event in list_events:
                if event['event_id'] != 1:
                    continue
                assert_equal(len(event['contenders']), 5)
                assert_equal(event['contenders'][0]['name'], "cont1")
                assert_equal(event['contenders'][0]['outright-odds'], 15000)
                assert_equal(event['contenders'][0]['place-odds'], 15000)
                assert_equal(event['contenders'][0]['show-odds'], 15000)
                assert_equal(event['contenders'][1]['name'], "cont2")
                assert_equal(event['contenders'][1]['outright-odds'], 16000)
                assert_equal(event['contenders'][1]['place-odds'], 16000)
                assert_equal(event['contenders'][1]['show-odds'], 16000)
                assert_equal(event['contenders'][2]['name'], "horse1")
                assert_equal(event['contenders'][2]['outright-odds'], 17000)
                assert_equal(event['contenders'][2]['place-odds'], 17000)
                assert_equal(event['contenders'][2]['show-odds'], 17000)
                assert_equal(event['contenders'][3]['name'], "horse2")
                assert_equal(event['contenders'][3]['outright-odds'], 18000)
                assert_equal(event['contenders'][3]['place-odds'], 18000)
                assert_equal(event['contenders'][3]['show-odds'], 18000)
                assert_equal(event['contenders'][4]['name'], "horse3")
                assert_equal(event['contenders'][4]['outright-odds'], 19000)
                assert_equal(event['contenders'][4]['place-odds'], 19000)
                assert_equal(event['contenders'][4]['show-odds'], 19000)

        self.log.info("Field Event Zeroing Odds Success")

    def check_field_bet_undo(self):
        self.log.info("Check Field Bets undo...")
        start_time = int(time.time() + 60 * 60)

        field_event_opcode = make_field_event(
            221,
            start_time,
            other_group,
            sport_names.index("F1 racing"),
            tournament_names.index("F1 Cup"),
            round_names.index("round0"),
            {
                contender_names.index("Alexander Albon") : 15000,
                contender_names.index("Pierre Gasly")    : 18000,
                contender_names.index("Romain Grosjean") : 15000,
                contender_names.index("Antonio Maria Giovinazzi")   : 19000,
                contender_names.index("cont1") : 0
            }
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        # For revert test
        self.stop_node(4)

        player1_bet = 30
        self.nodes[2].placefieldbet(221, market_outright, contender_names.index("Alexander Albon"), player1_bet)
        winnings = Decimal(player1_bet * 15000)
        player1_expected_win = (winnings - ((winnings - player1_bet * ODDS_DIVISOR) / 1000 * BETX_PERMILLE)) / ODDS_DIVISOR

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        for node in self.nodes[0:4]:
            event_stats = node.getfieldeventliability(221)
            assert_equal(event_stats["event-id"], 221)
            assert_equal(event_stats["event-status"], "running")
            assert_equal(len(event_stats["contenders"]), 5)
            for contender in event_stats["contenders"]:
                if contender["contender-id"] != contender_names.index("Alexander Albon"):
                    continue
                assert_equal(contender["outright-bets"], 1)
                assert_equal(contender["outright-liability"], int(player1_expected_win))

        field_result_opcode = make_field_result(221, STANDARD_RESULT, {
            contender_names.index("Alexander Albon") : place1,
            contender_names.index("Romain Grosjean") : place2,
            contender_names.index("Antonio Maria Giovinazzi") : place3
        })
        post_opcode(self.nodes[1], field_result_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        # Check event closed
        assert_raises_rpc_error(-4, "Error: The transaction was rejected! This might happen if some of the coins in your wallet were already spent, such as if you used a copy of wallet.dat and coins were spent in the copy but not marked as spent here.",
            self.nodes[2].placefieldbet, 221, market_outright, contender_names.index("Alexander Albon"), 30)

        for node in self.nodes[0:4]:
            event_stats = node.getfieldeventliability(221)
            assert_equal(event_stats["event-id"], 221)
            assert_equal(event_stats["event-status"], "resulted")

        self.log.info("Revering...")
        self.nodes[4].rpchost = self.get_local_peer(4, True)
        self.nodes[4].start()
        self.nodes[4].wait_for_rpc_connection()
        self.log.info("Generate blocks...")
        for i in range(5):
            self.nodes[4].generate(1)
            time.sleep(0.5)

        self.log.info("Connect and sync nodes...")
        self.connect_and_sync_blocks()

        for node in self.nodes:
            event_stats = node.getfieldeventliability(221)
            assert_equal(event_stats["event-id"], 221)
            assert_equal(event_stats["event-status"], "running")
            assert_equal(len(event_stats["contenders"]), 5)
            for contender in event_stats["contenders"]:
                assert_equal(contender["outright-bets"], 0)
                assert_equal(contender["outright-liability"], 0)

        self.log.info("Check Field Bets undo success")

    def check_field_bet_outright(self):
        self.log.info("Check Field Bets outright market...")
        start_time = int(time.time() + 60 * 60)

        global player1_total_bet
        global player2_total_bet

        player1_total_bet = 0
        player2_total_bet = 0

        # Create events for bet tests
        self.odds_events[2] = {
            contender_names.index("Alexander Albon") : 15000,
            contender_names.index("Pierre Gasly")    : 18000,
            contender_names.index("Romain Grosjean") : 15000,
            contender_names.index("Antonio Maria Giovinazzi")   : 19000,
            contender_names.index("cont1") : 0
        }
        field_event_opcode = make_field_event(
            2,
            start_time,
            other_group,
            sport_names.index("F1 racing"),
            tournament_names.index("F1 Cup"),
            round_names.index("round0"),
            self.odds_events[2]
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        self.odds_events[3] = {
            contender_names.index("horse1") : 15000,
            contender_names.index("horse2") : 18000,
            contender_names.index("horse3") : 14000,
            contender_names.index("horse4") : 13000,
            contender_names.index("horse5") : 19000
        }
        field_event_opcode = make_field_event(
            3,
            start_time,
            animal_racing_group,
            sport_names.index("Horse racing"),
            tournament_names.index("The BMW stakes"),
            round_names.index("round0"),
            self.odds_events[3]
        )

        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.odds_events[4] = {
            contender_names.index("horse1") : 15000,
            contender_names.index("horse2") : 18000,
            contender_names.index("horse3") : 14000
        }
        field_event_opcode = make_field_event(
            4,
            start_time,
            animal_racing_group,
            sport_names.index("Horse racing"),
            tournament_names.index("The BMW stakes"),
            round_names.index("round1"),
            self.odds_events[4]
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        assert_raises_rpc_error(-31, "Incorrect bet amount. Please ensure your bet is between 25 - 10000 WGR inclusive.",
            self.nodes[2].placefieldbet, 2, market_outright, contender_names.index("Alexander Albon"), 24)
        assert_raises_rpc_error(-31, "Incorrect bet amount. Please ensure your bet is between 25 - 10000 WGR inclusive.",
            self.nodes[2].placefieldbet, 2, market_outright, contender_names.index("Alexander Albon"), 10001)
        assert_raises_rpc_error(-31, "Error: there is no such FieldEvent: {}".format(202),
            self.nodes[2].placefieldbet, 202, market_outright, contender_names.index("Alexander Albon"), 30)
        assert_raises_rpc_error(-31, "Error: Incorrect bet market type for FieldEvent: {}".format(2),
            self.nodes[2].placefieldbet, 2, 100, contender_names.index("Alexander Albon"), 30)
        assert_raises_rpc_error(-31, "Error: there is no such contenderId {} in event {}".format(1050, 2),
            self.nodes[2].placefieldbet, 2, market_outright, 1050, 30)
        assert_raises_rpc_error(-31, "Error: contender odds is zero for event: {} contenderId: {}".format(2, contender_names.index("cont1")),
            self.nodes[2].placefieldbet, 2, market_outright, contender_names.index("cont1"), 30)

        # player1 makes win bet to event2
        player1_bet = 30
        player1_total_bet += player1_bet
        self.nodes[2].placefieldbet(2, market_outright, contender_names.index("Romain Grosjean"), player1_bet)
        winnings = Decimal(player1_bet * self.odds_events[2][contender_names.index("Romain Grosjean")])
        player1_expected_win = (winnings - ((winnings - player1_bet * ODDS_DIVISOR) / 1000 * BETX_PERMILLE)) / ODDS_DIVISOR

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        field_update_odds_opcode = make_field_update_odds(2, {
                contender_names.index("Romain Grosjean") : 14000,
                contender_names.index("cont2") : 11000 # Add new conteder
            }
        )
        self.odds_events[2][contender_names.index("Romain Grosjean")] = 14000
        self.odds_events[2][contender_names.index("cont2")] = 11000
        post_opcode(self.nodes[1], field_update_odds_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        # player2 makes win bet to event2 after changed odds
        player2_bet = 30
        player2_total_bet += player2_bet
        self.nodes[3].placefieldbet(2, market_outright, contender_names.index("Romain Grosjean"), player2_bet)
        winnings = Decimal(player2_bet * self.odds_events[2][contender_names.index("Romain Grosjean")])
        player2_expected_win = (winnings - ((winnings - player2_bet * ODDS_DIVISOR) / 1000 * BETX_PERMILLE)) / ODDS_DIVISOR

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        field_result_opcode = make_field_result(2, STANDARD_RESULT, {
            contender_names.index("Romain Grosjean") : place1,
            contender_names.index("Pierre Gasly") : place2,
            contender_names.index("cont2") : place3
        })
        post_opcode(self.nodes[1], field_result_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        assert_raises_rpc_error(-4, "Error: The transaction was rejected! This might happen if some of the coins in your wallet were already spent, such as if you used a copy of wallet.dat and coins were spent in the copy but not marked as spent here.",
            self.nodes[2].placefieldbet, 2, market_outright, contender_names.index("Alexander Albon"), 30)

        # TODO: for event2 calculate wins and check payouts/balances

        # player1 makes lose bet to event3
        player1_bet = 40
        player1_total_bet += player1_bet
        self.nodes[2].placefieldbet(3, market_outright, contender_names.index("horse2"), player1_bet)
        player1_expected_loss = player1_bet

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        field_update_odds_opcode = make_field_update_odds(3, {
                contender_names.index("horse1") : 14500,
                contender_names.index("horse3") : 9000,
                contender_names.index("horse6") : 17500 # Add new conteder
            }
        )
        self.odds_events[3][contender_names.index("horse1")] = 14500
        self.odds_events[3][contender_names.index("horse3")] = 9000
        self.odds_events[3][contender_names.index("horse6")] = 17500
        post_opcode(self.nodes[1], field_update_odds_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        # player2 makes win bet to event3
        player2_bet = 40
        player2_total_bet += player2_bet
        self.nodes[3].placefieldbet(3, market_outright, contender_names.index("horse6"), player2_bet)
        winnings = Decimal(player1_bet * self.odds_events[3][contender_names.index("horse6")])
        player2_expected_win = (winnings - ((winnings - player2_bet * ODDS_DIVISOR) / 1000 * BETX_PERMILLE)) / ODDS_DIVISOR

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        # make result for event3 and check payouts and players balances
        field_result_opcode = make_field_result(3, STANDARD_RESULT, {
            contender_names.index("horse6") : place1,
            contender_names.index("horse3") : place2,
            contender_names.index("horse5") : place3,
        })
        post_opcode(self.nodes[1], field_result_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        # TODO: for event3 calculate wins and check payouts/balances

        self.log.info("Field Bets outright market Success")

    def check_field_bet_place(self):
        # TODO: create outright event
        # TODO: check place market closed (contenders size)
        # update event to place market
        # placefield bet
        # event result
        # calculate
        pass

    def check_field_bet_show(self):
        # TODO: create outright event
        # TODO: check show market closed (contenders size)
        # update event to show market
        # placefield bet
        # event result
        # calculate
        pass

    def check_parlays_field_bet_undo(self):
        self.log.info("Check Parlay Field Bets Undo...")
        start_time = int(time.time() + 60 * 60)

        field_event_opcode = make_field_event(
            231,
            start_time,
            animal_racing_group,
            sport_names.index("Horse racing"),
            tournament_names.index("The BMW stakes"),
            round_names.index("round0"),
            {
                contender_names.index("horse1") : 15000,
                contender_names.index("horse2") : 18000,
                contender_names.index("horse3") : 14000,
                contender_names.index("horse4") : 13000,
                contender_names.index("horse5") : 19000
            }
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        field_event_opcode = make_field_event(
            232,
            start_time,
            animal_racing_group,
            sport_names.index("Horse racing"),
            tournament_names.index("The BMW stakes"),
            round_names.index("round0"),
            {
                contender_names.index("horse1") : 15000,
                contender_names.index("horse2") : 18000,
                contender_names.index("horse3") : 14000,
                contender_names.index("horse4") : 19000,
            }
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        # For revert test
        self.stop_node(4)

        player1_bet = 30
        self.nodes[2].placefieldparlaybet(
            [
                {"eventId": 231, "marketType": market_outright, "contenderId": contender_names.index("horse1")},
                {"eventId": 232, "marketType": market_outright, "contenderId": contender_names.index("horse4")},
            ],
            player1_bet
        )

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        for node in self.nodes[0:4]:
            event_stats = node.getfieldeventliability(231)
            assert_equal(event_stats["event-status"], "running")
            for contender in event_stats["contenders"]:
                if contender["contender-id"] == contender_names.index("horse1"):
                    assert_equal(contender["outright-bets"], 1)
                else:
                    assert_equal(contender["outright-bets"], 0)

        for node in self.nodes[0:4]:
            event_stats = node.getfieldeventliability(232)
            assert_equal(event_stats["event-status"], "running")
            for contender in event_stats["contenders"]:
                if contender["contender-id"] == contender_names.index("horse4"):
                    assert_equal(contender["outright-bets"], 1)
                else:
                    assert_equal(contender["outright-bets"], 0)

        field_result_opcode = make_field_result(231, STANDARD_RESULT, {
            contender_names.index("horse1") : place1,
            contender_names.index("horse2") : place2,
            contender_names.index("horse3") : place3
        })
        post_opcode(self.nodes[1], field_result_opcode, WGR_WALLET_EVENT['addr'])

        field_result_opcode = make_field_result(232, STANDARD_RESULT, {
            contender_names.index("horse1") : place1,
            contender_names.index("horse2") : place2,
            contender_names.index("horse3") : place3
        })
        post_opcode(self.nodes[1], field_result_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes[0:4])

        for node in self.nodes[0:4]:
            event_stats = node.getfieldeventliability(231)
            assert_equal(event_stats["event-status"], "resulted")

        for node in self.nodes[0:4]:
            event_stats = node.getfieldeventliability(232)
            assert_equal(event_stats["event-status"], "resulted")

        self.log.info("Revering...")
        self.nodes[4].rpchost = self.get_local_peer(4, True)
        self.nodes[4].start()
        self.nodes[4].wait_for_rpc_connection()
        self.log.info("Generate blocks...")
        for i in range(5):
            self.nodes[4].generate(1)
            time.sleep(0.5)

        self.log.info("Connect and sync nodes...")
        self.connect_and_sync_blocks()

        for node in self.nodes:
            event_stats = node.getfieldeventliability(231)
            assert_equal(event_stats["event-status"], "running")
            for contender in event_stats["contenders"]:
                assert_equal(contender["outright-bets"], 0)
                assert_equal(contender["outright-liability"], 0)

        for node in self.nodes:
            event_stats = node.getfieldeventliability(232)
            assert_equal(event_stats["event-status"], "running")
            for contender in event_stats["contenders"]:
                assert_equal(contender["outright-bets"], 0)
                assert_equal(contender["outright-liability"], 0)

        self.log.info("Check Parlay Field Bets Undo Success")

    def check_parlays_field_bet(self):
        self.log.info("Check Parlay Field Bets...")
        start_time = int(time.time() + 60 * 60)

        global player1_total_bet

        # For round1 tests
        field_event_opcode = make_field_event(
            5,
            start_time,
            animal_racing_group,
            sport_names.index("Horse racing"),
            tournament_names.index("The BMW stakes"),
            round_names.index("round1"),
            {
                contender_names.index("horse1") : 11000,
                contender_names.index("horse2") : 12000,
                contender_names.index("horse3") : 13000,
            }
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        show_market_event_id = 6
        self.odds_events[show_market_event_id] = {
            contender_names.index("horse1") : 11000,
            contender_names.index("horse2") : 12000,
            contender_names.index("horse3") : 13000,
            contender_names.index("horse4") : 14000,
            contender_names.index("horse5") : 15000,
            contender_names.index("horse6") : 16000,
            contender_names.index("horse7") : 17000,
            contender_names.index("horse8") : 0 # for zero odds test
        }
        field_event_opcode = make_field_event(
            show_market_event_id,
            start_time,
            animal_racing_group,
            sport_names.index("Horse racing"),
            tournament_names.index("The BMW stakes"),
            round_names.index("round0"),
            self.odds_events[show_market_event_id]
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        place_market_event_id = 7
        self.odds_events[place_market_event_id] = {
            contender_names.index("horse1") : 11000,
            contender_names.index("horse2") : 12000,
            contender_names.index("horse3") : 13000,
            contender_names.index("horse4") : 14000,
            contender_names.index("horse5") : 15000,
            contender_names.index("horse6") : 16000
        }
        field_event_opcode = make_field_event(
            place_market_event_id,
            start_time,
            animal_racing_group,
            sport_names.index("Horse racing"),
            tournament_names.index("The BMW stakes"),
            round_names.index("round0"),
            self.odds_events[place_market_event_id]
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        outright_market_event_id = 8
        self.odds_events[outright_market_event_id] = {
            contender_names.index("horse1") : 11000,
            contender_names.index("horse2") : 12000,
            contender_names.index("horse3") : 13000,
            contender_names.index("horse4") : 14000
        }
        field_event_opcode = make_field_event(
            outright_market_event_id,
            start_time,
            animal_racing_group,
            sport_names.index("Horse racing"),
            tournament_names.index("The BMW stakes"),
            round_names.index("round0"),
            self.odds_events[outright_market_event_id]
        )
        post_opcode(self.nodes[1], field_event_opcode, WGR_WALLET_EVENT['addr'])

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        assert_raises_rpc_error(-31, "Incorrect bet amount. Please ensure your bet is between 25 - 10000 WGR inclusive.",
            self.nodes[2].placefieldparlaybet, [
                {"eventId": show_market_event_id, "marketType": market_show, "contenderId": contender_names.index("horse1")},
                {"eventId": place_market_event_id, "marketType": market_place, "contenderId": contender_names.index("horse4")},
            ], 24)
        assert_raises_rpc_error(-31, "Incorrect bet amount. Please ensure your bet is between 25 - 10000 WGR inclusive.",
            self.nodes[2].placefieldparlaybet, [
                {"eventId": show_market_event_id, "marketType": market_show, "contenderId": contender_names.index("horse1")},
                {"eventId": place_market_event_id, "marketType": market_place, "contenderId": contender_names.index("horse4")},
            ], 10001)
        assert_raises_rpc_error(-31, "Error: there is no such FieldEvent: {}".format(202),
            self.nodes[2].placefieldparlaybet, [
                {"eventId": show_market_event_id, "marketType": market_show, "contenderId": contender_names.index("horse1")},
                {"eventId": 202,                  "marketType": market_place, "contenderId": contender_names.index("horse4")},
            ], 30)
        assert_raises_rpc_error(-31, "Error: Incorrect bet market type for FieldEvent: {}".format(show_market_event_id),
            self.nodes[2].placefieldparlaybet, [
                {"eventId": show_market_event_id, "marketType": 100, "contenderId": contender_names.index("horse1")},
                {"eventId": place_market_event_id, "marketType": market_place, "contenderId": contender_names.index("horse4")},
            ], 30)
        assert_raises_rpc_error(-31, "Error: there is no such contenderId {} in event {}".format(1050, show_market_event_id),
            self.nodes[2].placefieldparlaybet, [
                {"eventId": show_market_event_id, "marketType": market_show, "contenderId": 1050},
                {"eventId": place_market_event_id, "marketType": market_place, "contenderId": contender_names.index("horse4")},
            ], 30)
        assert_raises_rpc_error(-31, "Error: contender odds is zero for event: {} contenderId: {}".format(show_market_event_id, contender_names.index("horse8")),
            self.nodes[2].placefieldparlaybet, [
                {"eventId": show_market_event_id, "marketType": market_show, "contenderId": contender_names.index("horse8")},
                {"eventId": place_market_event_id, "marketType": market_place, "contenderId": contender_names.index("horse4")},
            ], 30)
        assert_raises_rpc_error(-31, "Error: event {} cannot be part of parlay bet".format(5),
            self.nodes[2].placefieldparlaybet, [
                {"eventId": 5, "marketType": market_outright, "contenderId": contender_names.index("horse1")},
                {"eventId": place_market_event_id, "marketType": market_place, "contenderId": contender_names.index("horse4")},
            ], 30)
        assert_raises_rpc_error(-31, "Error: market {} is closed for event {}".format(market_show, place_market_event_id),
            self.nodes[2].placefieldparlaybet, [
                {"eventId": show_market_event_id, "marketType": market_show,  "contenderId": contender_names.index("horse1")},
                {"eventId": place_market_event_id, "marketType": market_show, "contenderId": contender_names.index("horse4")},
            ], 30)
        assert_raises_rpc_error(-31, "Error: market {} is closed for event {}".format(market_place, outright_market_event_id),
            self.nodes[2].placefieldparlaybet, [
                {"eventId": outright_market_event_id, "marketType": market_place,  "contenderId": contender_names.index("horse1")},
                {"eventId": place_market_event_id, "marketType": market_place, "contenderId": contender_names.index("horse4")},
            ], 30)

        # Player1 place win parlay bet
        player1_bet = 40
        self.nodes[2].placefieldparlaybet(
            [
                {"eventId": outright_market_event_id, "marketType": market_outright,  "contenderId": contender_names.index("horse1")},
                {"eventId": place_market_event_id, "marketType": market_place, "contenderId": contender_names.index("horse5")},
                {"eventId": show_market_event_id, "marketType": market_show, "contenderId": contender_names.index("horse7")},
            ], player1_bet
        )
        # TODO: player_1 expected win calculate
        player1_expected_win = 0

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        for event_id in [outright_market_event_id, place_market_event_id, show_market_event_id]:
            for node in self.nodes:
                event_stats = node.getfieldeventliability(event_id)
                assert_equal(event_stats["event-status"], "running")
                for contender in event_stats["contenders"]:
                    if event_id == outright_market_event_id and contender["contender-id"] == contender_names.index("horse1"):
                        assert_equal(contender["outright-bets"], 1)
                        assert_equal(contender["place-bets"], 0)
                        assert_equal(contender["show-bets"], 0)
                    if event_id == place_market_event_id and contender["contender-id"] == contender_names.index("horse5"):
                        assert_equal(contender["outright-bets"], 0)
                        assert_equal(contender["place-bets"], 1)
                        assert_equal(contender["show-bets"], 0)
                    if event_id == show_market_event_id and contender["contender-id"] == contender_names.index("horse7"):
                        assert_equal(contender["outright-bets"], 0)
                        assert_equal(contender["place-bets"], 0)
                        assert_equal(contender["show-bets"], 1)

        # TODO: player1 place lose bet, calculate

        self.log.info("Parlay Field Bets Success")

    def check_timecut_refund(self):
        self.log.info("Check Timecut Refund...")

        # TODO: check

        self.log.info("Timecut Refund Success")

    def run_test(self):
        self.check_minting()
        # Chain height = 300 after minting -> v4 protocol active
        self.check_mapping()
        self.check_event()
        self.check_event_update_odds()
        self.check_event_zeroing_odds()
        # TODO: check big size transactions (lots of contenders)
        self.check_field_bet_undo()
        self.check_field_bet_outright()
        # self.check_field_bet_place() # TODO
        # self.check_field_bet_show() # TODO
        self.check_parlays_field_bet_undo()
        self.check_parlays_field_bet()
        # self.check_timecut_refund() # TODO

if __name__ == '__main__':
    BettingTest().main()
    # check_calculate_odds()
