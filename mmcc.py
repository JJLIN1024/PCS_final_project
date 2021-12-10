""" mmcc.py

Simulate the result proposed in "Dynamic priority queueing of handoff requests in PCS".
Paper link: https://ieeexplore.ieee.org/document/936959

"""

import simpy
import random

# Global Parameter

RANDOM_SEED = 42

"""
M/M/c/k queue, traffic load = lam / k * mu, 
if traffic load approach 1, one should expected the probability that arriving
call get blocked rises dramatically.
"""

lambda_n = 50                  # arrival rate for new call
lambda_h = 30                  # arrival rate for handoff call
p1_ratio = 0.5                # number of priority one handoff call / total handoff call

MESSAGE_DURATION = 180        # mean message duration
CHANNEL_HOLDING_T = 60        # mean service time for call in BST
HANDOFF_HOLDING_T = 30       # mean service time for call queued in Q1, Q2

DWELL_TIME_1 = 7.5            # mean waiting time before call in Q1 to be dropped
DWELL_TIME_2 = 12.5           # mean waiting time before call in Q2 to be dropped
TRANSITION_TIME = 6           # time for transition from Q1 to Q2

# number of new calls to simulate, simulation will stop either there's no more calls or simulation time ends.
NnewCalls = 100
# number of new calls to simulate, simulation will stop either there's no more calls or simulation time ends.
NhCalls = 100
NChannels = 1      # number of channels in the BST(cell)

Q1SIZE = 5
Q2SIZE = 5
# Logging
TRACING = True


def main():
    random.seed(RANDOM_SEED)
    env = simpy.Environment()
    CellChannel = simpy.PriorityResource(env, capacity=NChannels)

    newCallSource = NewCallSource(
        env, NnewCalls, lambda_n, CellChannel)
    handoffCallSource = HandOffCallSource(
        env, NhCalls, lambda_h, p1_ratio, CellChannel)
    env.process(newCallSource)
    env.process(handoffCallSource)
    env.run(until=3000)

# Model components ------------------------


def NewCallSource(env, NnewCalls, lambda_n, CellChannel):
    """ generates a sequence of new calls """
    for i in range(NnewCalls):
        call = Call(env, CellChannel, 0,
                    "New call, Call ID = {0:03f}".format(env.now))
        env.process(call)
        t = random.expovariate(1 / lambda_n)
        yield env.timeout(t)


def HandOffCallSource(env, NhCalls, lambda_h, p1_ratio, CellChannel):
    """ generates a sequence of new calls """
    for i in range(NhCalls):
        prob = random.random()
        if prob > p1_ratio:  # priority 1 handoff call
            call = Call(
                env, CellChannel, 1, "P1  call, Call ID = {0:03f}".format(env.now))
            env.process(call)
        else:
            call = Call(
                env, CellChannel, 2, "P2  call, Call ID = {0:03f}".format(env.now))
            env.process(call)
        t = random.expovariate(1 / lambda_h)
        yield env.timeout(t)


def CountQueueLength(resourceQueue):
    p1Count = 0
    p2Count = 0
    for request in resourceQueue:
        if request.priority == 0:
            p1Count += 1
        if request.priority == 1:
            p2Count += 1
    if p1Count == Q1SIZE and p2Count == Q2SIZE:
        return 0
    elif p1Count == Q1SIZE and p2Count < Q2SIZE:
        return 1
    elif p1Count < Q1SIZE and p2Count == Q2SIZE:
        return 2
    else:
        return 3


def Call(env, CellChannel, callType, name):
    """ 
    Calls arrive at random at the BST(base station transmitter)
    , callType: 0 means new call, 1 means handoff call with priority 1, 2 means handoff call with priority 2.
    """

    def trace(message):
        if TRACING:
            time = env.now
            print(f"{time: 2f}: {message}")
    if callType == 0:  # new call
        with CellChannel.request(priority=3) as req:
            result = yield req | env.timeout(0)
            if req in result:
                trace(f"{name} start: get a channel, being served...")
                yield env.timeout(CHANNEL_HOLDING_T)
                trace(f"{name} finish: leaving system...")
            else:
                trace(f"{name} get blocked, leaving system...")
    elif callType == 1:  # priority 1 handoff call

        with CellChannel.request(priority=0) as req:
            result = yield req | env.timeout(0)
            if req in result:
                trace(f"{name} start: get a channel, being served...")
                yield env.timeout(HANDOFF_HOLDING_T)
                trace(f"{name} finish: leaving system...")
            else:
                num1 = CountQueueLength(CellChannel.queue)
                if num1 == 0 or num1 == 1:
                    trace(f"{name} Q1 full, blocked")
                else:
                    with CellChannel.request(priority=0) as req11:
                        result11 = yield req11 | env.timeout(DWELL_TIME_1)
                        if req11 in result11:
                            trace(f"{name}: Q1 get served")
                            yield env.timeout(CHANNEL_HOLDING_T)
                        else:
                            trace(f"{name} Q1 get dropped, leaving system...")

    elif callType == 2:  # priority 2 handoff call
        with CellChannel.request(priority=1) as req:
            result = yield req | env.timeout(0)
            if req in result:
                trace(f"{name} start: get a channel")
                yield env.timeout(HANDOFF_HOLDING_T)
                trace(f"{name} finish: exit now")
            else:
                num = CountQueueLength(CellChannel.queue)
                if num == 0 or num == 2:
                    trace(f"{name} Q2 full, blocked")
                else:
                    with CellChannel.request(priority=1) as req2:
                        result2 = yield req2 | env.timeout(TRANSITION_TIME)
                        if req2 not in result2:
                            with CellChannel.request(priority=0) as req111:
                                rrr = yield req111 | env.timeout(DWELL_TIME_2 - TRANSITION_TIME)
                                if req111 in rrr:
                                    trace(
                                        f"{name} start: p2 to p1 get channel")
                                    yield env.timeout(HANDOFF_HOLDING_T)
                                    trace(f"{name} finish: p2 to p1 finish")
                                else:
                                    trace(
                                        f"{name} p2 to p1 eventually dropped")
                        else:
                            trace(f"{name}: Q2 get served")
    else:
        trace("Something went wrong, unknown type of call.")


if __name__ == '__main__':
    main()
