# PCS_final_project

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Prerequisites](#prerequisites)
- [Prototype Test](#run-prototype-test)
- [Simulation](#run-simulation)

## Overview

This project is for NTU 2021 FALL Personal Communication System final project, the goal is using [simPy(3.0.13)](https://simpy.readthedocs.io/en/3.0.13/index.html) to simulate the paper's handoff model, evaluate performace matrix, and analize the conclusion presented in this paper.

Simulated paper: A. Xhafa and O. K. Tonguz, "Dynamic priority queueing of handoff requests in PCS," ICC 2001. IEEE International Conference on Communications. Conference Record (Cat. No.01CH37240), 2001, pp. 341-345 vol.2, doi: 10.1109/ICC.2001.936959.

Paper link: https://ieeexplore.ieee.org/document/936959

## Prerequisites

1. Install [python](https://www.python.org/downloads/)
2. Make sure you have [pip](https://pip.pypa.io/en/stable/installation/) installed.
3. Install [numpy](https://numpy.org/) & [pandas](https://pandas.pydata.org/): `pip install numpy pandas`
4. Install [matplotlib](https://matplotlib.org/): `pip install matplotlib`
5. Install [simPy(3.0.13)](https://simpy.readthedocs.io/en/3.0.13/index.html): `pip install simpy`

## Run Prototype Test

1. Clone this repo: `git clone https://github.com/JJLIN1024/PCS_final_project.git`
2. Change into the repo directory: `cd PCS_final_project`
3. Use python(version >= 3.6) to run: `python prototype_test.py`

One should be able to see Steady state probability & System average statistics being generated and printed out. Compare it with [mathematics result](https://hackmd.io/Wen6lG5RTxmwrPxWDrCUKw) shows that our simulation code's logic is correct.

## Run Simulation

1. Clone this repo: `git clone https://github.com/JJLIN1024/PCS_final_project.git`
2. Change into the repo directory: `cd PCS_final_project`
3. Use python(version >= 3.6) to run simulation and you should see the following figure being generated:`python Simulation.py`

![alt text](https://github.com/JJLIN1024/PCS_final_project/blob/main/Statistics/Fig3.png)

4. Change the global parameter `P1CALL_DROP_RATE = 60/12.5` and `P1CALL_DROP_RATE = 60/17.5`, and run `python Simulation.py` again, you should see the following figure.

![alt text](https://github.com/JJLIN1024/PCS_final_project/blob/main/Statistics/Fig4.png)

5. Run `python Dropping_probability_diff.py` to observe the difference of handoff call dropping probability between FCFS queue scheme & Dynamic queue scheme. Result figure should be generated according to global parameter `LAMBD`, take `LAMBD = 50` as a example listed below.

![alt text](https://github.com/JJLIN1024/PCS_final_project/blob/main/Statistics/diff_lambda50.png)

