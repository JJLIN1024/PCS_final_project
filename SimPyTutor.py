import simpy


class Car(object):
    def __init__(self, env):
        self.env = env
        self.action = env.process(self.run())

    def run(self):
        while True:
            print(f'Start parking and charging at {self.env.now}')
            charging_duration = 5

            try:
                yield self.env.process(self.charge(charging_duration))
            except simpy.Interrupt:
                print("Oh no we were interrupted :(((")

            print(f'Start driving at {self.env.now}')
            driving_duration = 2
            yield self.env.timeout(driving_duration)

    def charge(self, duration):
        yield self.env.timeout(duration)


def driver(env, car):
    yield env.timeout(3)
    car.action.interrupt()


env = simpy.Environment()
car = Car(env)
env.process(driver(env, car))
env.run(until=15)
