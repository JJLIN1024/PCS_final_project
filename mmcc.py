""" mmcc.py

Simulate the result proposed in "Dynamic priority queueing of handoff requests in PCS".
Paper link: https://ieeexplore.ieee.org/document/936959

"""

import simpy
import random

# Global Parameter
"""
Total offered load is measured in Erlangs(E), E = lambda * h,
where lambda is the arrival rate, and h is mean call duration.
Ex: arrival rate(lambda) = 1/6 (calls/sec), mean call duration = 180(sec)
then the offered load is 1/6 * 180 = 30(Erlangs)
"""
RANDOM_SEED = 42
LAMBDA_ARRIVAL = 1/30                                     # Total arrival rate (calls / sec)
HANDOFF_TRAFFIC_RATIO = 0.5                                 # handoff_traffic / total arrival traffic
PRIORITY_1_RATIO = 0.5                                      # number of priority one handoff call / total handoff call
CHANNEL_HOLDING_T = 60                                      # mean service time(time unit = sec) for call in BST
HANDOFF_HOLDING_T = 30                                      # mean service time(time unit = sec) for call queued in Q1, Q2
DWELL_TIME_1 = 7.5                                          # mean waiting time(time unit = sec) before call in Q1 to be dropped
DWELL_TIME_2 = 12.5                                         # mean waiting time(time unit = sec) before call in Q2 to be dropped
TRANSITION_TIME = 6                                         # mean waiting time(time unit = sec) before call in Q2 to be transit from Q2 to Q1
N_CALLS = 10000                                             # number of new calls to simulate, simulation will stop either there's no more calls or simulation time ends.
N_Channels = 30                                             # number of channels in the BST(cell)
Q1_SIZE = 5                                                 # number of calls that can be queued in Q1
Q2_SIZE = 5                                                 # number of calls that can be queued in Q2
TRACING = True                                              # Logging
SIMULATION_TIME = 30000                                     # time unit(sec)

def main():
    system_performace_data = {'N_call':0, 'H_call':0, 'BN_call': 0, 'BH_call': 0,
                                'P1_call': 0, 'P2_call':0, 'BP1_call':0, 'BP2_call':0, 'P2_P1_call':0, 'DP1_call':0, 'DP2_call':0}
    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    BST = simpy.PriorityResource(env, capacity=N_Channels)
    callSource = CallSource(env, N_CALLS, LAMBDA_ARRIVAL,
                            HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data)
    
    env.process(callSource)
    env.run()
    # print("system_performace_data: ", system_performace_data)
    print(f"New call block rate: {system_performace_data['BN_call'] / system_performace_data['N_call']}")
    print(f"Handoff call block rate: {system_performace_data['BH_call'] / system_performace_data['H_call']}")
    print(f"Priority 1 call block rate: {system_performace_data['BP1_call'] / system_performace_data['P1_call']}")
    print(f"Priority 2 call block rate: {system_performace_data['BP2_call'] / system_performace_data['P2_call']}")
    print(f"Priority 1 call to Priority 2 call, transition rate: {system_performace_data['P2_P1_call'] / system_performace_data['P2_call']}")
    # env.run(until=SIMULATION_TIME)

# Model components 


def CallSource(env, N_CALLS, LAMBDA_ARRIVAL, HANDOFF_TRAFFIC_RATIO, PRIORITY_1_RATIO, BST, system_performace_data):
    """ generates a sequence of new calls """
    for i in range(N_CALLS):

        p1 = random.random()
        if p1 > HANDOFF_TRAFFIC_RATIO:
            call = Call(
                env, BST, 0, f"new call       , ID = {i}", system_performace_data)
            env.process(call)
        else:
            p2 = random.random()
            if p2 > PRIORITY_1_RATIO:
                call = Call(
                    env, BST, 1, f"Priority 1 call, ID = {i}", system_performace_data)
                env.process(call)
            else:
                call = Call(
                    env, BST, 2, f"Priority 2 call, ID = {i}", system_performace_data)
                env.process(call)
        t = random.expovariate(1 / LAMBDA_ARRIVAL)
        yield env.timeout(t)


def CountQueueLength(resourceQueue):
    p1Count = 0
    p2Count = 0
    for request in resourceQueue:
        if request.priority == 0:
            p1Count += 1
        if request.priority == 1:
            p2Count += 1
    if p1Count == Q1_SIZE and p2Count == Q2_SIZE:
        return 0
    elif p1Count == Q1_SIZE and p2Count < Q2_SIZE:
        return 1
    elif p1Count < Q1_SIZE and p2Count == Q2_SIZE:
        return 2
    else:
        return 3


def Call(env, BST, callType, name, system_performace_data):
    """
    Calls arrive at random at the BST(base station transmitter)
    , callType: 0 means new call, 1 means handoff call with priority 1, 2 means handoff call with priority 2.
    """

    def LOG(message):
        if TRACING:
            time = env.now
            print(f"{time: 2f}: {message}")

    if callType == 0:  # new call
        system_performace_data['N_call'] += 1
        with BST.request(priority=3) as req:
            result = yield req | env.timeout(0)
            if req in result:
                LOG(f"{name} start: get a channel, being served...")
                yield env.timeout(CHANNEL_HOLDING_T)
                LOG(f"{name} finish: leaving system...")
            else:
                system_performace_data['BN_call'] += 1
                LOG(f"{name} get blocked, leaving system...")
    elif callType == 1:  # priority 1 handoff call
        system_performace_data['H_call'] += 1
        system_performace_data['P1_call'] += 1
        with BST.request(priority=0) as req:
            result = yield req | env.timeout(0)
            if req in result:
                LOG(f"{name} start: get a channel, being served...")
                yield env.timeout(HANDOFF_HOLDING_T)
                LOG(f"{name} finish: leaving system...")
            else:
                num1 = CountQueueLength(BST.queue)
                if num1 == 0 or num1 == 1:
                    system_performace_data['BH_call'] += 1
                    system_performace_data['BP1_call'] += 1
                    LOG(f"{name} Q1 full, blocked")
                else:
                    with BST.request(priority=0) as req11:
                        result11 = yield req11 | env.timeout(DWELL_TIME_1)
                        if req11 in result11:
                            LOG(f"{name}: Q1 get served")
                            yield env.timeout(CHANNEL_HOLDING_T)
                        else:
                            system_performace_data['DP1_call'] += 1
                            LOG(f"{name} Q1 get dropped, leaving system...")

    elif callType == 2:  # priority 2 handoff call
        system_performace_data['H_call'] += 1
        system_performace_data['P2_call'] += 1
        with BST.request(priority=1) as req:
            result = yield req | env.timeout(0)
            if req in result:
                LOG(f"{name} start: get a channel")
                yield env.timeout(HANDOFF_HOLDING_T)
                LOG(f"{name} finish: exit now")
            else:
                num = CountQueueLength(BST.queue)
                if num == 0 or num == 2:
                    system_performace_data['BH_call'] += 1
                    system_performace_data['BP2_call'] += 1
                    LOG(f"{name} Q2 full, blocked")
                else:
                    with BST.request(priority=1) as req2:
                        result2 = yield req2 | env.timeout(TRANSITION_TIME)
                        if req2 not in result2:
                            with BST.request(priority=0) as req111:
                                system_performace_data['P2_P1_call'] += 1
                                rrr = yield req111 | env.timeout(DWELL_TIME_2 - TRANSITION_TIME)
                                if req111 in rrr:
                                    LOG(f"{name} start: p2 to p1 get channel")
                                    yield env.timeout(HANDOFF_HOLDING_T)
                                    LOG(f"{name} finish: p2 to p1 finish")
                                else:
                                    system_performace_data['DP2_call'] += 1
                                    LOG(f"{name} p2 to p1 eventually dropped")
                        else:
                            LOG(f"{name}: Q2 get served")
    else:
        LOG("Something went wrong, unknown type of call.")

if __name__ == '__main__':
    main()
