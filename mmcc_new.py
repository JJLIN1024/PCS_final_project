""" mmcc_test.py
Simulate the result proposed in "Dynamic priority queueing of handoff requests in PCS".
Paper link: https://ieeexplore.ieee.org/document/936959 
"""

import simpy
import random
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MEAN_MESSAGE_DURATION = 3
RANDOM_SEED = 1
HANDOFF_TRAFFIC_RATIO = 0.5
PRIORITY_1_RATIO = 0.5
NEW_CALL_SERVICE_RATE = 60/60
HANDOFF_CALL_SERVICE_RATE = 60/30
P1CALL_DROP_RATE = 60/7.5
P2CALL_DROP_RATE = 60/12.5
TRANSITION_RATE = 60/6
N_CALLS = 10000
N_Channels = 30
Q1_SIZE = 5
Q2_SIZE = 5
TRACING = False

def main():

    lambda_range = np.array(np.arange(0.01, 50, 1))

    plot_data = {'Pb_d': [], 'Ph_d': [], 'Pb_f': [], 'Ph_f': [], 'Lambda_d': [], 'Lambda_f': []}
    for i in lambda_range:
        Simulation(i, plot_data, 0) # dynamic
        Simulation(i, plot_data, 1) # FCFS
    
    # simulation result data
    df = pd.DataFrame({
        'Offered_load': plot_data['Lambda_d'],
        'Block probability for new call(dynamic queue)': plot_data['Pb_d'],
        'Drop probability for handoff call(dynamic queue)': plot_data['Ph_d'],
        'Block probability for new call(FCFS queue)': plot_data['Pb_f'],
        'Drop probability for handoff call(FCFS queue)': plot_data['Ph_f'],
    })

    plt.plot('Offered_load', 'Block probability for new call(dynamic queue)',data=df, marker='.', color='skyblue', linewidth=2)
    plt.plot('Offered_load', 'Drop probability for handoff call(dynamic queue)',data=df, marker='.', color='olive', linewidth=2)
    plt.plot( 'Offered_load', 'Block probability for new call(FCFS queue)', data=df, marker='', color='red', linewidth=2)
    plt.plot('Offered_load', 'Drop probability for handoff call(FCFS queue)',data=df, marker='', color='green', linewidth=2)

    plt.xlabel('lambda: call/min')
    plt.ylabel('probability')
    plt.legend()
    plt.show()


def Simulation(lambd, plot_data, queue_type):

    system_performace_data = {'N_call': 0, 'H_call': 0, 'BN_call': 0, 'BH_call': 0, 
                            'P1_call': 0, 'P2_call': 0, 'BP1_call': 0, 'BP2_call': 0}

    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    BST = simpy.PriorityResource(env, capacity=N_Channels)
    callSource = CallSource(env, N_CALLS, lambd, HANDOFF_TRAFFIC_RATIO,PRIORITY_1_RATIO, BST, system_performace_data, queue_type)
    env.process(callSource)
    env.run()

    if queue_type == 0:
        plot_data["Lambda_d"].append(lambd)
        plot_data['Pb_d'].append(system_performace_data['BN_call'] / system_performace_data['N_call'])
        plot_data['Ph_d'].append(PRIORITY_1_RATIO * (system_performace_data['BP1_call'])/system_performace_data['H_call'] + (
            1 - PRIORITY_1_RATIO) * (system_performace_data['BP2_call'])/system_performace_data['H_call'])
    elif queue_type == 1:
        plot_data["Lambda_f"].append(lambd)
        plot_data['Pb_f'].append(system_performace_data['BN_call'] / system_performace_data['N_call'])
        plot_data['Ph_f'].append(PRIORITY_1_RATIO * (system_performace_data['BP1_call'])/system_performace_data['H_call'] + (
            1 - PRIORITY_1_RATIO) * (system_performace_data['BP2_call'])/system_performace_data['H_call'])

    # print("System average statistics: ")
    # print(f"New call block rate: {system_performace_data['BN_call'] / system_performace_data['N_call']}")
    # print(f"Priority 1 call block rate: {(system_performace_data['BP1_call'])/system_performace_data['H_call'] }")
    # print(f"Priority 2 call block rate: {(system_performace_data['BP2_call'])/system_performace_data['H_call'] }")
    # print(f"Handoff call block rate: {PRIORITY_1_RATIO * (system_performace_data['BP1_call'])/system_performace_data['H_call'] + (1 - PRIORITY_1_RATIO) * (system_performace_data['BP2_call'])/system_performace_data['H_call']}")

# Model components
def CallSource(env, N_CALLS, LAMBD, HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data, queue_type):
    """ 
    Generates a sequence of new calls depends on HANDOFF_TRAFFIC_RATIO & PRIORITY_1_RATIO,
    In this case, HANDOFF_TRAFFIC_RATIO = 1/2, and PRIORITY_1_RATIO = 1/2, which means the handoff traffic is roughly  
    50% of the total in-comming call traffic, and among the total handoff traffic, calls that have priority 1 is roughly 50%. 
    """
    for i in range(N_CALLS):
        p1 = random.random()
        if p1 > HANDOFF_TRAFFIC_RATIO:
            call = Call(
                env, BST, 0, f"new call       , ID = {i}", system_performace_data, queue_type)
            env.process(call)
        else:
            p2 = random.random()
            if p2 > PRIORITY_1_RATIO:
                call = Call(
                    env, BST, 2, f"Priority 2 call, ID = {i}", system_performace_data, queue_type)
                env.process(call)
            else:
                call = Call(
                    env, BST, 1, f"Priority 1 call, ID = {i}", system_performace_data, queue_type)
                env.process(call)
        # t is the interarrival time, given the arrival rate is LAMBD
        t = random.expovariate(LAMBD)
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
        LOG(f"{name} Incoming")
        system_performace_data['N_call'] += 1

        req = BST.request(priority=3)
        yield req | env.timeout(0)
        if req.triggered:
            LOG(f"{name} start: get a channel")
            t = random.expovariate(NEW_CALL_SERVICE_RATE)
            yield env.timeout(t)
            BST.release(req)
            LOG(f"{name} finish: leaving system...")
        else:
            req.cancel()
            system_performace_data['BN_call'] += 1
            LOG(f"{name} get blocked, leaving system...")

    elif callType == 1:
        LOG(f"{name} Incoming")
        system_performace_data['H_call'] += 1
        system_performace_data['P1_call'] += 1
        total_service_time = random.expovariate(HANDOFF_CALL_SERVICE_RATE)
        wait_time = random.expovariate(P1CALL_DROP_RATE)
        req = BST.request(priority=0)
        yield req | env.timeout(0)
        if req.triggered:
            LOG(f"{name} start: get a channel, being served...")
            # Suspend this process for time period of length = mean service time for handoff calls
            yield env.timeout(total_service_time)
            BST.release(req)
            LOG(f"{name} finish: leaving system...")
        else:
            Q1Full = CountQueueLength(BST.queue, request_type=1)
            if Q1Full:
                system_performace_data['BP1_call'] += 1
                req.cancel()
                LOG(f"{name} Q1 full, blocked")
            else:
                yield req | env.timeout(wait_time)
                if req.triggered:
                    LOG(f"{name} start: get a channel(from Q1), being served...")
                    yield env.timeout(total_service_time)
                    LOG(f"{name} finish: leaving system...")
                    BST.release(req)
                else:
                    system_performace_data['BP1_call'] += 1
                    req.cancel()
                    LOG(f"{name} Q1 get dropped, leaving system...")

    elif callType == 2:
        LOG(f"{name} Incoming")
        wait_time = random.expovariate(P2CALL_DROP_RATE)
        transition_time = random.expovariate(TRANSITION_RATE)
        service_time = random.expovariate(HANDOFF_CALL_SERVICE_RATE)

        system_performace_data['H_call'] += 1
        system_performace_data['P2_call'] += 1

        req = BST.request(priority=1)
        yield req | env.timeout(0)
        if req.triggered:
            LOG(f"{name} start: get a channel, being served...")
            yield env.timeout(service_time)
            BST.release(req)
            LOG(f"{name} finish: leaving system...")
        else:
            Q2Full = CountQueueLength(BST.queue, request_type=2)
            if Q2Full:
                system_performace_data['BP2_call'] += 1
                req.cancel()
                LOG(f"{name} Q2 full, blocked")
            else:
                if queue_type == 0: 
                    t0 = env.now
                    yield req | env.timeout(transition_time)
                    if req.triggered:
                        LOG(f"{name} start: get a channel(from Q2), being served...")
                        t1 = env.now
                        time_spent_in_queue = t1 - t0
                        service_time_left = max(
                            service_time - time_spent_in_queue, 0)
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
                            t = random.expovariate(P1CALL_DROP_RATE)
                            t_before = env.now
                            yield new_req | env.timeout(t)
                            if new_req.triggered:
                                LOG(f"{name} start: get a channel(from Q1), being served...")
                                t_after = env.now
                                time_spent_in_queue = t_after - t0
                                service_time_left = max(
                                    service_time - time_spent_in_queue, 0)
                                yield env.timeout(service_time_left)
                                LOG(f"{name} finish: leaving system...")
                                BST.release(new_req)
                            else:
                                new_req.cancel()
                                system_performace_data['BP1_call'] += 1
                                LOG(f"{name} Q1 get dropped, leaving system...")

                        else:
                            wait_time_left = max(wait_time - transition_time, 0)
                            yield req | env.timeout(wait_time_left)
                            if req.triggered:
                                LOG(f"{name} start: get a channel(from Q2), being served...")
                                t2 = env.now
                                time_spent_in_queue = t2 - t0
                                service_time_left = max(
                                    service_time - time_spent_in_queue, 0)
                                yield env.timeout(service_time_left)
                                LOG(f"{name} finish: leaving system...")
                                BST.release(req)
                            else:
                                req.cancel()
                                system_performace_data['BP2_call'] += 1
                                LOG(f"{name}: Q2 get dropped")
                else: # FCFS
                    Q2_SIZE = CountQueueLength(BST.queue, request_type=2)
                    if Q2_SIZE:
                        system_performace_data['BP2_call'] += 1
                        req.cancel()
                        LOG(f"{name} Q2 full, blocked")
                    else:
                        yield req | env.timeout(random.expovariate(P2CALL_DROP_RATE))
                        if req.triggered:
                            LOG(f"{name} start: get a channel, being served...")
                            yield env.timeout(random.expovariate(HANDOFF_CALL_SERVICE_RATE))
                            LOG(f"{name} finish: leaving system...")
                            BST.release(req)
                        else:
                            system_performace_data['BP2_call'] += 1
                            req.cancel()
                            LOG(f"{name} Q2 get dropped, leaving system...")




                

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
