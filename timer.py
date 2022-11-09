""" https://github.com/flytocc/debug-timer
"""

import time
from collections import defaultdict, deque
from functools import partial
from typing import Callable

import numpy as np


class Timer(object):
    """
    A timer which computes the time elapsed since the tic/toc of the timer.
    """

    def __init__(self, window_size=20):
        self.deque = deque(maxlen=window_size)
        self.start_time = 0.
        self.total_time = 0.
        self.calls = 0

    def tic(self):
        # using time.time instead of time.clock because time time.clock
        # does not normalize for multithreading
        self.start_time = time.time()

    def toc(self):
        diff = time.time() - self.start_time
        self.total_time += diff
        self.calls += 1
        self.deque.append(diff)
        return diff

    @property
    def median(self):
        return np.median(self.deque) if self.deque else 0.

    @property
    def avg(self):
        return np.mean(self.deque) if self.deque else 0.

    @property
    def global_avg(self):
        return self.total_time / self.calls

    @property
    def max(self):
        return max(self.deque) if self.deque else 0.

    @property
    def value(self):
        return self.deque[-1] if self.deque else 0.


class _DebugTimer(object):
    """
    Track vital debug statistics.
    Usage:
        1. from timer import debug_timer

        2. with debug_timer("timer1"):
               code1

           debug_timer.tic("timer2")
           code2
           debug_timer.toc("timer2")

           debug_timer.timer3_tic()
           code3
           debug_timer.timer3_toc()

           @debug_timer("timer4")
           def func(*args, **kwargs):
               code4

        3. debug_timer.log()
    """

    __TIMER__ = None
    prefix = ""
    window_size = 50

    def __new__(cls, *args, **kwargs):
        if cls.__TIMER__ is None:
            cls.__TIMER__ = super(_DebugTimer, cls).__new__(cls)
        return cls.__TIMER__

    def __init__(self, num_warmup=0):
        super(_DebugTimer, self).__init__()
        self.num_warmup = num_warmup
        self.context_stacks = []
        self.calls = 0
        self.timers = defaultdict(Timer)
        self.set_sync_func(lambda: None)
        self.set_window_size(self.window_size)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        elif name.endswith("_tic"):
            return lambda: self.tic(name[:-4])
        elif name.endswith("_toc"):
            return lambda: self.toc(name[:-4])
        raise AttributeError(name)

    def __call__(self, name_or_func):
        if isinstance(name_or_func, str):
            self.context_stacks.append(name_or_func)
            return self

        name = self.context_stacks.pop(-1)

        def func_wrapper(*args, **kwargs):
            with self(name):
                return name_or_func(*args, **kwargs)
        return func_wrapper

    def __enter__(self):
        name = self.context_stacks[-1]
        self.tic(name)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        name = self.context_stacks.pop(-1)
        self.toc(name)
        if exc_type is not None:
            raise exc_value

    def set_sync_func(self, func):
        assert isinstance(func, Callable)
        self.sync = func

    def set_window_size(self, window_size):
        assert isinstance(window_size, int)
        assert len(self.timers) == 0
        self.window_size = window_size
        timer_obj = partial(Timer, window_size=self.window_size) \
            if window_size > 0 else Timer
        self.timers = defaultdict(timer_obj)

    def reset_timer(self):
        for timer in self.timers.values():
            timer.reset()

    def tic(self, name):
        timer = self.timers[name]
        self.sync()
        timer.tic()
        return timer

    def toc(self, name):
        timer = self.timers.get(name, None)
        if timer is None:
            raise ValueError(
                f"Trying to toc a non-existent Timer which is named '{name}'!")
        if self.calls >= self.num_warmup:
            self.sync()
            return timer.toc()

    def log(self, logperiod=10, prefix="", log_func=print):
        """
        Log the tracked statistics.
        Eg.: | timer1: xxxs | timer2: xxxms | timer3: xxxms |
        """
        self.calls += 1
        if self.calls % logperiod == 0 and self.timers:
            lines = [prefix or self.prefix]
            for name, timer in self.timers.items():
                avg_time = timer.avg if self.window_size > 0 else timer.global_avg
                suffix = "s"
                if avg_time < 0.01:
                    avg_time *= 1000
                    suffix = "ms"
                lines.append(" {}: {:.3f}{} ".format(name, avg_time, suffix))
            lines.append("")
            log_func("|".join(lines))


debug_timer = _DebugTimer()


if __name__ == "__main__":
    # debug_timer.set_sync_func(torch.cuda.synchronize)

    @debug_timer('timer0')
    def code():
        s = 0
        for i in range(100000):
            s += i
        return True

    for iter_i in range(1000):
        with debug_timer('timer1'):
            code()

        debug_timer.tic("timer2")
        code()
        debug_timer.toc("timer2")

        debug_timer.timer3_tic()
        code()
        debug_timer.timer3_toc()

        debug_timer.log(prefix=f"{iter_i}:")
