import simpy
import random
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from Simulation import Call

# Variable, for lambda in (40, 50), the blocking probability 
# is roughly 20% when handoff traffic is about 50% of total traffic
LAMBD = 50

# Constant
MEAN_MESSAGE_DURATION = 3
RANDOM_SEED = 1
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

    handoff_traffic_range = np.array(np.arange(0.01, 1, 0.01))

    plot_data = {'Ph_d': [], 'Ph_f': [], 'Pb_d': [], 'Pb_f': [], 'ratio_d': [], 'ratio_f': []}
    for i in handoff_traffic_range:
        Simulation(i, LAMBD, plot_data, 0)  # dynamic
        Simulation(i, LAMBD, plot_data, 1)  # FCFS
    
    diff = []
    for i in range(len(plot_data['Ph_d'])):
        diff.append(plot_data['Ph_f'][i] - plot_data['Ph_d'][i])

    # simulation result data
    df = pd.DataFrame({
        'Handoff traffic ratio': plot_data['ratio_d'],
        'Blocking probability(FCFS)': plot_data['Pb_f'],
        'Blocking probability(dynamic queue)': plot_data['Pb_d'],
        'Drop probability for handoff call(FCFS queue)': plot_data['Ph_f'],
        'Drop probability for handoff call(dynamic queue)': plot_data['Ph_d'],
        'Dropping probability difference': diff
    })

    
    plt.plot('Handoff traffic ratio', 'Drop probability for handoff call(dynamic queue)',data=df, marker='.', color='red', linewidth=2)
    plt.plot('Handoff traffic ratio', 'Drop probability for handoff call(FCFS queue)',data=df, marker='.', color='orange', linewidth=2)
    plt.plot('Handoff traffic ratio', 'Blocking probability(FCFS)',data=df, marker='.', color='skyblue', linewidth=2)
    plt.plot('Handoff traffic ratio', 'Blocking probability(dynamic queue)',data=df, marker='.', color='blue', linewidth=2)
    plt.plot('Handoff traffic ratio', 'Dropping probability difference',data=df, marker='.', color='green', linewidth=2)

    plt.xlabel('handoff traffic ratio')
    plt.ylabel('probability')
    plt.legend()
    plt.show()


def Simulation(handoff_ratio, lambd, plot_data, queue_type):

    system_performace_data = {'N_call': 0, 'H_call': 0, 'BN_call': 0, 'BH_call': 0,
                            'P1_call': 0, 'P2_call': 0, 'BP1_call': 0, 'BP2_call': 0, 'DP1_call': 0, 'DP2_call': 0}

    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    BST = simpy.PriorityResource(env, capacity=N_Channels)
    callSource = CallSource(env, N_CALLS, lambd, handoff_ratio,PRIORITY_1_RATIO, BST, system_performace_data, queue_type)
    env.process(callSource)
    env.run()

    if queue_type == 0:
        plot_data["ratio_d"].append(handoff_ratio)
        plot_data['Pb_d'].append((system_performace_data['BN_call'] + system_performace_data['BP1_call'] + system_performace_data['BP2_call'])/ N_CALLS)
        plot_data['Ph_d'].append(PRIORITY_1_RATIO * (system_performace_data['DP1_call'])/system_performace_data['H_call'] + (
            1 - PRIORITY_1_RATIO) * (system_performace_data['DP2_call'])/system_performace_data['H_call'])
    elif queue_type == 1:
        plot_data["ratio_f"].append(handoff_ratio)
        plot_data['Pb_f'].append((system_performace_data['BN_call'] + system_performace_data['BP1_call'] + system_performace_data['BP2_call'])/ N_CALLS)
        plot_data['Ph_f'].append(PRIORITY_1_RATIO * (system_performace_data['DP1_call'])/system_performace_data['H_call'] + (
            1 - PRIORITY_1_RATIO) * (system_performace_data['DP2_call'])/system_performace_data['H_call'])

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

if __name__ == '__main__':
    main()
