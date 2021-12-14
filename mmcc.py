""" mmcc_FCFS.py

Simulate the result proposed in "Dynamic priority queueing of handoff requests in PCS".
Paper link: https://ieeexplore.ieee.org/document/936959 
Q1 and Q2 are FCFS, no dynamic flow in between.
"""

import simpy
import random
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Global Parameter
"""
Total offered load is measured in Erlangs(E), E = lambda * h,
where lambda is the arrival rate, and h is mean call duration.
Ex: arrival rate(lambda) = 1/6 (call/sec), mean call duration = 180(sec)
then the offered load is 1/6 * 180 = 30(Erlangs), the equation is basically Little's Formula.
"""
MEAN_MESSAGE_DURATION = 180                                 # unit: second    
RANDOM_SEED = 1                                             # For result's reproducibility
HANDOFF_TRAFFIC_RATIO = 0.5                                 # handoff_traffic / total arrival traffic
PRIORITY_1_RATIO = 0.5                                      # number of priority one handoff call / total handoff call
CHANNEL_HOLDING_T = 60                                      # mean service time(time unit = second) for call in BST
HANDOFF_HOLDING_T = 30                                      # mean service time(time unit = second) for call queued in Q1, Q2
DWELL_TIME_1 = 12.5                                       # mean waiting time(time unit = second) before call in Q1 to be dropped
DWELL_TIME_2 = 17.5                                         # mean waiting time(time unit = second) before call in Q2 to be dropped
TRANSITION_TIME = 6                                         # mean waiting time(time unit = second) before call in Q2 to be transit from Q2 to Q1
N_CALLS = 10000                                             # number of new calls to simulate, simulation will stop either there's no more calls or simulation time ends.
N_Channels = 30                                             # number of channels in the BST(cell)
Q1_SIZE = 5                                                 # number of calls that can be queued in Q1
Q2_SIZE = 5                                                 # number of calls that can be queued in Q2
TRACING = False                                              # Logging
SIMULATION_TIME = 30000                                     # time unit(sec)

def main():

    lambda_range = np.array(np.arange(0.01, 1, 0.01)) # input call arrival rate (calls/second)

    plot_data = {'Pb_d': [], 'Ph_d': [], 'Pb_f': [], 'Ph_f': [], 'Lambda_0': [], 'Lambda_1': []}
    for i in lambda_range:
        Simulation(i, 0, plot_data) # queue_type = 0 => dynamic queue
        Simulation(i, 1, plot_data) # queue_type = 1 => FCFS queue
    
    # simulation result data
    df = pd.DataFrame({
        'Offered_load': plot_data['Lambda_0'],
        'Block probability for new call(dynamic queue)': plot_data['Pb_d'],
        'Block probability for handoff call(dynamic queue)':plot_data['Ph_d'],
        'Block probability for new call(FCFS queue)': plot_data['Pb_f'],
        'Block probability for handoff call(FCFS queue)':plot_data['Ph_f']
    })

    # plot
    # multiple line plots
    plt.plot( 'Offered_load', 'Block probability for new call(dynamic queue)', data=df, marker='.', color='skyblue', linewidth=2)
    plt.plot( 'Offered_load', 'Block probability for handoff call(dynamic queue)', data=df, marker='.', color='olive', linewidth=2)
    plt.plot( 'Offered_load', 'Block probability for new call(FCFS queue)', data=df, marker='', color='red', linewidth=2)
    plt.plot( 'Offered_load', 'Block probability for handoff call(FCFS queue)', data=df, marker='', color='green', linewidth=2)

    # show legend
    plt.legend()
    plt.show()


def Simulation(Lambda, queue_type, plot_data):

    # plot_data["Lambda"].append(Lambda * MEAN_MESSAGE_DURATION) # Lambda * MEAN_MESSAGE_DURATION = Offered Load(Erlang)
    system_performace_data = {'N_call':0, 'H_call':0, 'BN_call': 0, 'BH_call': 0,
                                'P1_call': 0, 'P2_call':0, 'BP1_call':0, 'BP2_call':0, 
                                'P2_P1_call':0, 'P2_P1_drop_call':0, 'DP1_call':0, 'DP2_call':0}

    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    BST = simpy.PriorityResource(env, capacity=N_Channels)
    callSource = CallSource(env, N_CALLS, Lambda, 
                            HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data, queue_type)
    
    env.process(callSource)
    env.run()
    # env.run(until=SIMULATION_TIME)

    if queue_type == 0:
        plot_data["Lambda_0"].append(Lambda * MEAN_MESSAGE_DURATION)
        plot_data['Pb_d'].append(system_performace_data['BN_call'] / system_performace_data['N_call'])
        plot_data['Ph_d'].append(system_performace_data['BH_call'] / system_performace_data['H_call'])
    elif queue_type == 1:
        plot_data["Lambda_1"].append(Lambda * MEAN_MESSAGE_DURATION)
        plot_data['Pb_f'].append(system_performace_data['BN_call'] / system_performace_data['N_call'])
        plot_data['Ph_f'].append(system_performace_data['BH_call'] / system_performace_data['H_call'])

    # print(f"New call block rate: {system_performace_data['BN_call'] / system_performace_data['N_call']}")
    # print(f"Handoff call block rate: {system_performace_data['BH_call'] / system_performace_data['H_call']}")
    # print(f"Priority 1 call block rate: {system_performace_data['BP1_call'] / system_performace_data['P1_call']}")
    # print(f"Priority 2 call block rate: {system_performace_data['BP2_call'] / system_performace_data['P2_call']}")
    # print(f"Priority 1 call to Priority 2 call, transition rate: {system_performace_data['P2_P1_call'] / system_performace_data['P2_call']}")
    # print(f"Priority 1 call to Priority 2 call, dropped: {system_performace_data['P2_P1_drop_call'] / system_performace_data['P2_P1_call']}")
    

# Model components 
def CallSource(env, N_CALLS, Lambda, HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data, queue_type):
    """ 
    Generates a sequence of new calls depends on probability: HANDOFF_TRAFFIC_RATIO & PRIORITY_1_RATIO,
    In this case, HANDOFF_TRAFFIC_RATIO = 1/2, and PRIORITY_1_RATIO = 1/2, which means the handoff traffic is roughly  
    50% of the total incomming call traffic, and among the total handoff traffic, calls that have priority 1 is roughly 50%. 
    """
    for i in range(N_CALLS):
        p1 = random.random()
        if p1 > HANDOFF_TRAFFIC_RATIO:
            call = Call(env, BST, 0, f"new call       , ID = {i}", system_performace_data, queue_type)
            env.process(call)
        else:
            p2 = random.random()
            if p2 > PRIORITY_1_RATIO:
                call = Call(env, BST, 1, f"Priority 1 call, ID = {i}", system_performace_data, queue_type)
                env.process(call)
            else:
                call = Call(env, BST, 2, f"Priority 2 call, ID = {i}", system_performace_data, queue_type)
                env.process(call)

        # t is the inter-arrival time for arrival rate = Lambda
        # We suspend the Call process, resume it after time period of length t to mimic incomming Poisson arrival calls.
        t = random.expovariate(Lambda)
        yield env.timeout(t)




def Call(env, BST, callType, name, system_performace_data, queue_type):
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

    if callType == 0:  

        # A new call has arrived 
        system_performace_data['N_call'] += 1

        # Request a channel with the lowest priority(compare to handoff calls)
        with BST.request(priority=3) as req:
            # timeout immediately, no patience
            result = yield req | env.timeout(0) 
            if req in result:
                LOG(f"{name} start: get a channel")
                # Suspend this process for time period of length = mean service time for new calls
                t = CHANNEL_HOLDING_T
                yield env.timeout(t)
                LOG(f"{name} finish: leave system")
            else:
                # New call does not have waiting queue, simply being dropped.
                system_performace_data['BN_call'] += 1
                LOG(f"{name} get blocked, leaving system...")

    elif callType == 1:  

        # priority 1 handoff call
        system_performace_data['H_call'] += 1
        system_performace_data['P1_call'] += 1

        # Request a channel with the highest priority
        with BST.request(priority=0) as req:
            # timeout immediately, no patience
            result = yield req | env.timeout(0)
            if req in result:
                LOG(f"{name} start: get a channel, being served...")
                # Suspend this process for time period of length = mean service time for handoff calls
                t = HANDOFF_HOLDING_T
                yield env.timeout(t)
                LOG(f"{name} finish: leaving system...")
            else:
                # Server(BST) is full, currently all K channels are being used, request failed.
                # Attempt to join Q1, but first we have to check if Q1 is full or not(size = H1)
                # If Q1 is full, this call get dropped, else, join the queue.
                # After Joining Q1, if this call does not get served after time period = DWELL_TIME_1, if gets dropped.
                Q1Full = CountQueueLength(BST.queue, request_type = 1)
                if Q1Full:
                    system_performace_data['BH_call'] += 1
                    system_performace_data['BP1_call'] += 1
                    LOG(f"{name} Q1 full, blocked")
                else:
                    with BST.request(priority=0) as req:
                        # priority 1 call waits in Q1 for DWELL_TIME_1
                        # If still not get served, leaves Q1(dropped)
                        result = yield req | env.timeout(DWELL_TIME_1)
                        if req in result:
                            LOG(f"{name}: Q1 get served")
                            t = HANDOFF_HOLDING_T
                            yield env.timeout(t)
                        else:
                            system_performace_data['DP1_call'] += 1
                            system_performace_data['BH_call'] += 1
                            LOG(f"{name} Q1 get dropped, leaving system...")

    elif callType == 2:  
        # priority 2 handoff call, 
        system_performace_data['H_call'] += 1
        system_performace_data['P2_call'] += 1

        # Request a channel
        with BST.request(priority=1) as req:
            # timeout immediately, no patience
            result = yield req | env.timeout(0)
            if req in result:
                LOG(f"{name} start: get a channel")
                t = HANDOFF_HOLDING_T
                yield env.timeout(t)
                LOG(f"{name} finish: exit now")
            else:
                Q2Full = CountQueueLength(BST.queue, request_type=2)
                if Q2Full:
                    system_performace_data['BH_call'] += 1
                    system_performace_data['BP2_call'] += 1
                    LOG(f"{name} Q2 full, blocked")
                else:

                    if queue_type == 0: # Dynamic queue
                        with BST.request(priority=1) as req:
                            result = yield req | env.timeout(TRANSITION_TIME)
                            
                            # Pass TRANSITION_TIME, and still not get served, so call
                            # transit to Q1 from Q2
                            if req not in result:
                                Q1Full = CountQueueLength(BST.queue, request_type=1)
                                if Q1Full:
                                    system_performace_data['P2_P1_drop_call'] += 1
                                    system_performace_data['BH_call'] += 1
                                    LOG(f"{name} p2 to p1, Q1 full, dropped")
                                else:
                                    # Join Q1
                                    with BST.request(priority=0) as req:
                                        system_performace_data['P2_P1_call'] += 1
                                        t = DWELL_TIME_2 - TRANSITION_TIME
                                        result = yield req | env.timeout(t)
                                        if req in result:
                                            LOG(f"{name} start: p2 to p1 get channel")
                                            t = HANDOFF_HOLDING_T
                                            yield env.timeout(t)
                                            LOG(f"{name} finish: p2 to p1 finish")
                                        else:
                                            system_performace_data['DP2_call'] += 1
                                            system_performace_data['BH_call'] += 1
                                            LOG(f"{name} p2 to p1 eventually dropped")

                    else: # FCFS queue
                        with BST.request(priority=1) as req:
                            # priority 2 call waits in Q2 for DWELL_TIME_2
                            # If still not get served, leaves Q2(dropped)
                            result = yield req | env.timeout(DWELL_TIME_2)
                            if req in result:
                                LOG(f"{name}: Q2 get served")
                                t = HANDOFF_HOLDING_T
                                yield env.timeout(t)
                            else:
                                system_performace_data['DP2_call'] += 1
                                system_performace_data['BH_call'] += 1
                                LOG(f"{name} Q2 get dropped, leaving system...")

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
        return p1Count >= Q1_SIZE
    elif request_type == 2:
        return p2Count >= Q2_SIZE
    else:
        pass

if __name__ == '__main__':
    main()
