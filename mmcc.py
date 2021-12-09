""" mmcc.py

Simulate the result proposed in "Dynamic priority queueing of handoff requests in PCS".
Paper link: https://ieeexplore.ieee.org/document/936959

"""

import simpy 
import random as ran

# Experiment data -------------------------

RANDOM_SEED = 42
MESSAGE_DURATION = 180
CHANNEL_HOLDING_T = 60
HANDOFF_HOLDING_T = 30
DWELL_TIME_1 = 7.5
DWELL_TIME_2 = 12.5
HANDOFF1_PERCENT = 0.5
HANDOFF2_PERCENT = 0.5

NChannels = 30        # number of channels in the cell
maxN = 10000
ranSeed = 3333333
lam = 1.0              # per minute
mu = 0.6667            # per minute

TRACING = True


def main():
    env = simpy.Environment()
    cell = Cell(NChannels)

    env.process(cell)
    env.run(until=3000)


# Model components ------------------------

class CallSource(object):
    """ generates a sequence of calls """
    
    def execute(self, maxN, lam, cell):
        for i in range(maxN):
            j = Call("Call{0:03d}".format(i), sim=self.sim)
            self.sim.activate(j, j.execute(cell))
            yield hold, self, ran.expovariate(lam)


class Call(Process):
    """ Calls arrive at random at the cellphone hub"""

    def execute(self, cell):
        self.trace("arrived")
        if cell.Nfree == 0:
            self.trace("blocked and left")
        else:
            self.trace("got a channel")
            cell.Nfree -= 1
            if cell.Nfree == 0:
                self.trace("start busy period======")
                cell.busyStartTime = self.sim.now()
                cell.totalBusyVisits += 1
            yield hold, self, ran.expovariate(mu)
            self.trace("finished")
            if cell.Nfree == 0:
                self.trace("end   busy period++++++")
                cell.busyEndTime = self.sim.now()
                busy = self.sim.now() - cell.busyStartTime
                self.trace("         busy  = {0:9.4f}".format(busy))
                cell.totalBusyTime += busy
            cell.Nfree += 1

    def trace(self, message):
        if TRACING:
            print("{0:7.4f} {1:13s} {2}".format(
                self.sim.now(), message, self.name))


class Cell(object):
    """ Holds global measurements"""
    def __init__(self, N_free):
        self.N_free = N_free


if __name__ = 'main':
    main()

