arg_dict = {
'initial_reward' : 0,
'initial_agent_x' : 200,
'initial_agent_y' : 600,
'agent_r' : 40,
'gold_r' : 10,
'initial_gold' : [[600, 400], [603, 407], [595, 401], [597, 396]],
'walls' : [
[0, 0, 50, 800, 0], 
[0, 0, 800, 50, 0],
[0, 800 - 50, 800, 50, 0], # I know it's 750, doing this for clarity 
[800 - 50, 0, 50, 800, 0],
[(800 - 50)/2, 200, 50, 800, 0]
]}
