""" mmcc_test.py
Perform model checking for mmcc.py by running code on a small test set, and verify model correctness
by compare the program outcome with the math result computed by hand using 2-class markov chain model.
The test set contains only 2 channels, and the queue size for Q1 & Q2 are both 1.
The state diagram, global balance equation, and steady state probability is presented in: https://hackmd.io/Wen6lG5RTxmwrPxWDrCUKw
"""

import simpy
import random
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Global Parameter
RANDOM_SEED = 3                                               # for result's reproducibility
HANDOFF_TRAFFIC_RATIO = 0.5                                   # handoff_traffic / total arrival traffic
PRIORITY_1_RATIO = 0.5                                        # number of priority one handoff call / total handoff call
LAMBD = 4                                                     # input call arrival rate (call / minute)
NEW_CALL_SERVICE_RATE = 9/5                                   # mean service time for new call (call / minute)
HANDOFF_CALL_SERVICE_RATE = 9/5                               # mean service time for handoff call (call / minute)
P1CALL_DROP_RATE = 8                                          # mean drop rate for priority one call (call / minute)
P2CALL_DROP_RATE = 6                                          # mean drop rate for priority two call (call / minute)
TRANSITION_RATE = 12                                          # mean transition rate for priority two call to transit into priority one call
N_Channels = 2                                                # number of channels in the BST(cell)
Q1_SIZE = 1                                                   # number of priority one call that can be queued in Q1
Q2_SIZE = 1                                                   # number of priority two call that can be queued in Q2
N_CALLS = 10000                                               # number of calls to simulate
TRACING = False                                               # Simulation Logging

"""
Program Introduction:
Simulation runs in a environment, Callsource generates calls to the BST, 
which is handled in Call function, depends on the type of call, Call function
is will put itself into sleep(yield statement) to simulate the call being served by BST,
and will wake itself up after the service is done(call ends)

"""


def main():
    
    system_performace_data = {'N_call':0, 'H_call':0, 'BN_call': 0, 'BH_call': 0, 'P1_call': 0, 
                            'P2_call':0, 'BP1_call': 0, 'BP2_call': 0,
                            (0,0,0):0, (1,0,0):0, (2,0,0):0, (2,1,0):0, (2,0,1):0, (2,1,1):0}

    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    BST = simpy.PriorityResource(env, capacity=N_Channels)
    callSource = CallSource(env, N_CALLS, LAMBD, HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data)
    env.process(callSource)
    env.run()

    print(f"Steady state probability: ")
    print(f"(0,0,0): {system_performace_data[(0,0,0)] / N_CALLS}")
    print(f"(1,0,0): {system_performace_data[(1,0,0)] / N_CALLS}")
    print(f"(2,0,0): {system_performace_data[(2,0,0)] / N_CALLS}")
    print(f"(2,0,1): {system_performace_data[(2,0,1)] / N_CALLS}")
    print(f"(2,1,0): {system_performace_data[(2,1,0)] / N_CALLS}")
    print(f"(2,1,1): {system_performace_data[(2,1,1)] / N_CALLS}")
    print("------------------------------------\n")
    print("System average statistics: ")
    print(f"New call block rate: {system_performace_data['BN_call'] / system_performace_data['N_call']}")
    print(f"Priority 1 call block rate: {(system_performace_data['BP1_call'])/system_performace_data['H_call'] }")
    print(f"Priority 2 call block rate: {(system_performace_data['BP2_call'])/system_performace_data['H_call'] }")
    print(f"Handoff call block rate: {PRIORITY_1_RATIO * (system_performace_data['BP1_call'])/system_performace_data['H_call'] + (1 - PRIORITY_1_RATIO) * (system_performace_data['BP2_call'])/system_performace_data['H_call']}")
    print("------------------------------------\n")
    print("Statistics validation: ")

# Model components 
def CallSource(env, N_CALLS, LAMBD, HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data):
    """ 
    Generates a sequence of new calls depends on HANDOFF_TRAFFIC_RATIO & PRIORITY_1_RATIO,
    In this case, HANDOFF_TRAFFIC_RATIO = 1/2, and PRIORITY_1_RATIO = 1/2, which means the handoff traffic is roughly  
    50% of the total in-comming call traffic, and among the total handoff traffic, calls that have priority 1 is roughly 50%. 
    """

    for i in range(N_CALLS):
        p1 = random.random()
        if p1 > HANDOFF_TRAFFIC_RATIO:
            call = Call(env, BST, 0, f"new call       , ID = {i}", system_performace_data)
            env.process(call)
        else:
            p2 = random.random()
            if p2 > PRIORITY_1_RATIO:
                call = Call(env, BST, 2, f"Priority 2 call, ID = {i}", system_performace_data)
                env.process(call)
            else:
                call = Call(env, BST, 1, f"Priority 1 call, ID = {i}", system_performace_data)
                env.process(call)
        # t is the interarrival time, given the arrival rate is LAMBD
        t = random.expovariate(LAMBD)
        yield env.timeout(t)

def Call(env, BST, callType, name, system_performace_data):
    """
    Calls arrive at random at the BST(base station transmitter)
    , callType: 0 means new call, 1 means handoff call with priority 1, 2 means handoff call with priority 2.
    queue_type = 0 => dynamic queue(Q1, Q2).
    queue_type = 1 => FCFS queue(Q1, Q2), which means there is no dynamic flow from Q2 to Q1.
    """

    k = BST.count
    m1 = 0
    m2 = 0

    users_delay = []
    for user in BST.users:
        users_delay.append(user.proc.target._delay)

    for request in BST.queue:

        timeout = request.proc.target._events[1]._delay
        flag = False
        for d in users_delay:
            if d < timeout:
                flag = True
                break
        
        if request.priority == 0:
            m1 += 1
            if not flag:
                system_performace_data['P1_failed'] += 1
        if request.priority == 1:
            m2 += 1
            if not flag:
                system_performace_data['P2_failed'] += 1

    system_performace_data[(k , m1, m2)] += 1

    def LOG(message):
        if TRACING:
            time = env.now
            print(f"{time: 2f}: {message}")

    if callType == 0:  
        LOG(f"{name} Incoming")
        system_performace_data['N_call'] += 1

        req = BST.request(priority=3)
        yield req | env.timeout(0) 
        if req.triggered:
            LOG(f"{name} start: get a channel")
            
            t = random.expovariate(NEWCALL_HOLDING_T)
            yield env.timeout(t)
            BST.release(req)
            LOG(f"{name} finish: leaving system...")
        else:
            # New call does not have waiting queue, simply being dropped.
            req.cancel()
            system_performace_data['BN_call'] += 1
            LOG(f"{name} get blocked, leaving system...")

    elif callType == 1:  
        LOG(f"{name} Incoming")
        # priority 1 handoff call
        system_performace_data['H_call'] += 1
        system_performace_data['P1_call'] += 1
        total_service_time = random.expovariate(HANDOFF_HOLDING_T)
        wait_time = random.expovariate(DWELL_TIME_1)
        # Request a channel with the highest priority
        req = BST.request(priority=0)
        # timeout immediately, no patience
        yield req | env.timeout(0)
        if req.triggered:
            
            LOG(f"{name} start: get a channel, being served...")
            
            # Suspend this process for time period of length = mean service time for handoff calls
            yield env.timeout(total_service_time)
            BST.release(req)
            LOG(f"{name} finish: leaving system...")
        else:
            
            Q1Full = CountQueueLength(BST.queue, request_type = 1)
            if Q1Full:
                system_performace_data['BH_call'] += 1
                system_performace_data['BP1_call'] += 1
                req.cancel()
                LOG(f"{name} Q1 full, blocked")
            else:
                # priority 1 call waits in Q1 for DWELL_TIME_1
                # If still not get served, leaves Q1(dropped)
                
                yield req | env.timeout(wait_time)
                if req.triggered:
                    LOG(f"{name} start: get a channel(from Q1), being served...")
                    system_performace_data['P1_served'] += 1
                    yield env.timeout(total_service_time)
                    LOG(f"{name} finish: leaving system...")
                    BST.release(req)
                else:
                    # Pass Dwell time, call dropped
                    system_performace_data['DP1_call'] += 1
                    system_performace_data['BH_call'] += 1
                    req.cancel()
                    LOG(f"{name} Q1 get dropped, leaving system...")

    elif callType == 2:  
        LOG(f"{name} Incoming")
        wait_time = random.expovariate(DWELL_TIME_2)
        transition_time = random.expovariate(TRANSITION_TIME)
        service_time = random.expovariate(HANDOFF_HOLDING_T)

        # priority 2 handoff call, 
        system_performace_data['H_call'] += 1
        system_performace_data['P2_call'] += 1

        # Request a channel
        req = BST.request(priority=1)
        # timeout immediately, no patience
        yield req | env.timeout(0)
        if req.triggered:
            
            LOG(f"{name} start: get a channel, being served...")
            # Suspend this process for time period of length = mean service time for handoff calls
            yield env.timeout(service_time)
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
                
                t0 = env.now
                yield req | env.timeout(transition_time)
                if req.triggered:
                    LOG(f"{name} start: get a channel(from Q2), being served...")
                    t1 = env.now
                    time_spent_in_queue = t1 - t0
                    service_time_left = max(service_time - time_spent_in_queue, 0)
                    yield env.timeout(service_time_left)
                    BST.release(req)
                    LOG(f"{name} finish: leaving system...")
                else:
                    p1Count = 0
                    for request in BST.queue:
                        if request.priority == 0:
                            p1Count += 1
                    if p1Count < Q1_SIZE:
                        req.cancel()

                        new_req = BST.request(priority=0)
                        t = random.expovariate(DWELL_TIME_1)
                        t_before = env.now
                        yield new_req | env.timeout(t)
                        if new_req.triggered:
                            LOG(f"{name} start: get a channel(from Q1), being served...")
                            system_performace_data['P1_served'] += 1
                            t_after = env.now                  
                            time_spent_in_queue = t_after - t0
                            service_time_left = max(service_time - time_spent_in_queue, 0)
                            yield env.timeout(service_time_left)
                            LOG(f"{name} finish: leaving system...")
                            BST.release(new_req)
                        else:
                            # Pass Dwell time, call dropped
                            system_performace_data['DP1_call'] += 1
                            system_performace_data['BH_call'] += 1
                            new_req.cancel()
                            LOG(f"{name} Q1 get dropped, leaving system...")
                            

                    else:
                        wait_time_left = max(wait_time - transition_time, 0)
                        yield req | env.timeout(wait_time_left)
                        if req.triggered:
                            LOG(f"{name} start: get a channel(from Q2), being served...")
                            t2 = env.now
                            time_spent_in_queue = t2 - t0
                            service_time_left = max(service_time - time_spent_in_queue, 0)    
                            yield env.timeout(service_time_left)
                            LOG(f"{name} finish: leaving system...")
                            BST.release(req)
                        else:
                            system_performace_data['DP2_call'] += 1
                            system_performace_data['BH_call'] += 1
                            req.cancel()
                            LOG(f"{name}: Q2 get dropped")
                
    else:
        LOG("Something went wrong, unknown type of call.")


# Utils
def print_stats(resource):
    print(f'{resource.count} of {resource.capacity} channels are allocated.')
    print(f'  Users: {resource.users}')
    print(f'  Queued events: {resource.queue}')

"""
This util function counts how many request currently holding onto resource(BST channels), 
and return whether the desire queue is full. Ex: currently all K channels are full, then a priority 1 
handoff call arrived, made a request to claim resource, then p1Count will equal 2(include himself), return False.
"""
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
