arg_dict = {
'reward' : 0,
'initial_agent_x' : 200,
'initial_agent_y' : 600 + 800, # So, off-screen.
'agent_r' : 40,
'gold_r' : 10,
'initial_gold' : [[300, 300], [303, 307], [295, 301], [297, 296]],
'walls' : [
[0, 0, 50, 800, 0], 
[0, 0, 800, 50, 0],
[0, 800 - 50, 350, 50, 0], # I know it's 750, doing this for clarity
[450, 800 - 50, 350, 50, 0],
[800 - 50, 0, 50, 800, 0]
]}
