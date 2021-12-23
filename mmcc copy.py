""" mmcc_test.py
Perform model checking for mmcc.py by running code on a small test set, and verify model correctness
by compare the program outcome with the math result computed by hand using 2-class markov chain model.

The test set contains only 2 channels, and the queue size for Q1 & Q2 are both 1.
"""

import simpy
import random
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Global Parameter

MEAN_MESSAGE_DURATION = 180                                 # unit: second    
LAMBD = 4
RANDOM_SEED = 2                                             # For result's reproducibility
HANDOFF_TRAFFIC_RATIO = 0.5                                 # handoff_traffic / total arrival traffic
PRIORITY_1_RATIO = 0.5
N_CALLS = 100                                             # number of new calls to simulate, simulation will stop either there's no more calls or simulation time ends.
N_Channels = 2                                             # number of channels in the BST(cell)
Q1_SIZE = 1                                                 # number of calls that can be queued in Q1
Q2_SIZE = 1                                                 # number of calls that can be queued in Q2
TRACING = True                                              # Logging


def main():
    
    system_performace_data = {'N_call':0, 'H_call':0, 'BN_call': 0, 'BH_call': 0,
                                'P1_call': 0, 'P2_call':0, 'DP1_call':0, 'DP2_call':0, 'BP1_call':0, 'BP2_call':0}

    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    BST = simpy.PriorityResource(env, capacity=N_Channels)
    callSource = CallSource(env, N_CALLS, LAMBD, 
                            HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data)
    
    env.process(callSource)
    env.run()

    print(f"New call block rate: {system_performace_data['BN_call'] / system_performace_data['N_call']}")
    print(f"Handoff call block rate: {system_performace_data['BH_call'] / system_performace_data['H_call']}")
    print(f"Priority 1 call block rate: {system_performace_data['BP1_call'] / system_performace_data['P1_call']}")
    print(f"Priority 2 call block rate: {system_performace_data['BP2_call'] / system_performace_data['P2_call']}")
    print(f"Priority 1 call drop rate: {system_performace_data['DP1_call'] / system_performace_data['P1_call']}")
    print(f"Priority 2 call drop rate: {system_performace_data['DP2_call'] / system_performace_data['P2_call']}")

# Model components 
def CallSource(env, N_CALLS, LAMBD, HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data):
    """ 
    Generates a sequence of new calls depends on probability: HANDOFF_TRAFFIC_RATIO & PRIORITY_1_RATIO,
    In this case, HANDOFF_TRAFFIC_RATIO = 1/2, and PRIORITY_1_RATIO = 1/2, which means the handoff traffic is roughly  
    50% of the total incomming call traffic, and among the total handoff traffic, calls that have priority 1 is roughly 50%. 
    """
    for i in range(N_CALLS):
        p1 = random.random()
        if p1 > HANDOFF_TRAFFIC_RATIO:
            call = Call(env, BST, 0, f"new call       , ID = {i}", system_performace_data)
            env.process(call)
        else:
            p2 = random.random()
            if p2 > PRIORITY_1_RATIO:
                call = Call(env, BST, 1, f"Priority 1 call, ID = {i}", system_performace_data)
                env.process(call)
            else:
                call = Call(env, BST, 2, f"Priority 2 call, ID = {i}", system_performace_data)
                env.process(call)

        yield env.timeout(1/2)

def print_stats(res):
    print(f'{res.count} of {res.capacity} slots are allocated.')
    print(f'  Users: {res.users}')
    print(f'  Queued events: {res.queue}')

def Call(env, BST, callType, name, system_performace_data):
    """
    Calls arrive at random at the BST(base station transmitter)
    , callType: 0 means new call, 1 means handoff call with priority 1, 2 means handoff call with priority 2.
    queue_type = 0 => dynamic queue(Q1, Q2).
    queue_type = 1 => FCFS queue(Q1, Q2), which means there is no dynamic flow from Q2 to Q1.
    """

    def LOG(message):
        if TRACING:
            time = env.now
            print(f"{time: 2f}: {message}")

    # print_stats(BST)
    if callType == 0:  

        # A new call has arrived 
        system_performace_data['N_call'] += 1

        # Request a channel with the lowest priority(compare to handoff calls)
        req = BST.request(priority=3)
        
        # timeout immediately, no patience
        yield req | env.timeout(0) 
        if req.triggered:
            LOG(f"{name} start: get a channel")
            yield env.timeout(5)
            BST.release(req)
            LOG(f"{name} finish: leaving system...")
        else:
            # New call does not have waiting queue, simply being dropped.
            req.cancel()
            system_performace_data['BN_call'] += 1
            LOG(f"{name} get blocked, leaving system...")

    elif callType == 1:  

        # priority 1 handoff call
        system_performace_data['H_call'] += 1
        system_performace_data['P1_call'] += 1
        # Request a channel with the highest priority
        req = BST.request(priority=0)
        # timeout immediately, no patience
        yield req | env.timeout(0)
        if req.triggered:
            
            LOG(f"{name} start: get a channel, being served...")
            # Suspend this process for time period of length = mean service time for handoff calls
            yield env.timeout(2)
            BST.release(req)
            LOG(f"{name} finish: leaving system...")
        else:
            
            Q1Full = CountQueueLength(BST.queue, request_type = 1)
            if Q1Full:
                req.cancel()
                system_performace_data['BH_call'] += 1
                system_performace_data['BP1_call'] += 1
                LOG(f"{name} Q1 full, blocked")
            else:
                yield req | env.timeout(1)
                if req.triggered:
                    LOG(f"{name} start: get a channel(from Q1), being served...")
                    yield env.timeout(1)
                    LOG(f"{name} finish: leaving system...")
                    BST.release(req)

                else:
                    # Pass Dwell time, call dropped
                    system_performace_data['DP1_call'] += 1
                    system_performace_data['BH_call'] += 1
                    req.cancel()
                    LOG(f"{name} Q1 get dropped, leaving system...")

    elif callType == 2:  
        # priority 2 handoff call, 
        system_performace_data['H_call'] += 1
        system_performace_data['P2_call'] += 1

        # Request a channel
        req = BST.request(priority=1)
        # timeout immediately, no patience
        yield req | env.timeout(0)
        if req.triggered:
            
            LOG(f"{name} start: get a channel, being served...")

            yield env.timeout(2)
            BST.release(req)
            LOG(f"{name} finish: leaving system...")
        else:
            Q2Full = CountQueueLength(BST.queue, request_type = 2)
            if Q2Full:
                
                system_performace_data['BH_call'] += 1
                system_performace_data['BP2_call'] += 1
                req.cancel()
                LOG(f"{name} Q2 full, blocked")
            else:
                
                yield req | env.timeout(0.5)
                if req.triggered:
                    LOG(f"{name} start: get a channel(from Q2), being served...")
     
                    yield env.timeout(1.5)
                    LOG(f"{name} finish: leaving system...")
                    BST.release(req)
                else:
                    p1Count = 0
                    for request in BST.queue:
                        if request.priority == 0:
                            p1Count += 1
                    if p1Count < Q1_SIZE:
                        req.cancel()
                        new_req = BST.request(priority=1)
                    
                        yield new_req | env.timeout(1)
                        if new_req.triggered:
                            LOG(f"{name} start: get a channel(from Q1 Q2), being served...")
                            yield env.timeout(1)
                            LOG(f"{name} finish: leaving system...")
                            BST.release(new_req)
                        else:
                            # Pass Dwell time, call dropped
                            system_performace_data['DP1_call'] += 1
                            system_performace_data['BH_call'] += 1
                            new_req.cancel()
                            LOG(f"{name} Q1 get dropped, leaving system...")
                            

                    else:

                        yield req | env.timeout(1)
                        if req.triggered:
                            LOG(f"{name} start: get a channel(from Q2), being served...")
                           
                            yield env.timeout(1)
                            LOG(f"{name} finish: leaving system...")
                           
                            BST.release(req)
                        else:
                            system_performace_data['DP2_call'] += 1
                            system_performace_data['BH_call'] += 1
                            req.cancel()
                            LOG(f"{name}: Q2 get dropped")
                
    else:
        LOG("Something went wrong, unknown type of call.")


# This util function counts how many reqeust currently holding onto resourse(BST channels), and return whether the desire queue is full.
# Ex: currently all K channels are full, then a priority 1 handoff call arrived, then p1Count will equal 1, return False.
# If currently all K channels are full, and the sixth priority 1 handoff call arrived, then p1Count will equal 5, return False.
def CountQueueLength(resourceQueue, request_type):
     
    p1Count = p2Count = 0

    for request in resourceQueue:
        if request.priority == 0:
            p1Count += 1
        if request.priority == 1:
            p2Count += 1

    if request_type == 1:
        return p1Count > Q1_SIZE
    elif request_type == 2:
        return p2Count > Q2_SIZE
    else:
        pass

if __name__ == '__main__':
    main()
