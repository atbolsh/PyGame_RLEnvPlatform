from math import pi

reward = 0

# Vastly incomplete; needs a tool, practice using it, and a way to get the gold with the tool. Later in program.

agent_x = 600
agent_y = 600
agent_r = 40

gold_r = 10

gold = [[170, 269], [400, 400]]

walls = [
[0, 0, 50, 800, 0], 
[0, 0, 800, 50, 0],
[0, 800 - 50, 800, 50, 0],
[800 - 50, 0, 50, 800, 0],

[100, 100, 50, 450, 0], 
[100, 100, 50, 450, -pi/6]
]


