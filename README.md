# debug-timer
A Timer for Debug. 

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

3. debug_timer.log()

TODO: multithreading support
