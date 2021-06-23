from math import pi
arg_dict = {
'initial_reward' : 0,

# Vastly incomplete; needs a tool, practice using it, and a way to get the gold with the tool. Later in program.

'initial_agent_x' : 600,
'initial_agent_y' : 600,
'agent_r' : 40,

'gold_r' : 10,

'initial_gold' : [[170, 269], [400, 400]],

'walls' : [
[0, 0, 50, 800, 0], 
[0, 0, 800, 50, 0],
[0, 800 - 50, 800, 50, 0],
[800 - 50, 0, 50, 800, 0],

[100, 100, 50, 450, 0], 
[100, 100, 50, 450, -pi/6]
]
}
