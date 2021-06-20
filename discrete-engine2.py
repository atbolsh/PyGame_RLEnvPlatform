import pygame, sys
from pygame.locals import *
import math
from time import sleep

# Defaults

direction = 0
indicator_length = 400

reward = 0

agent_x = 400
agent_y = 400
agent_r = 40

gold_r = 10

gold = []

walls = []

# Choose level-file here
from levels.tool_use_advanced import *

# set up pygame
pygame.init()

# set up the window
windowSurface = pygame.display.set_mode((800, 800), 0, 32)
pygame.display.set_caption('discrete engine')

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

GOLD = (255, 200, 0)

windowSurface.fill(WHITE)

# draw funcs

def backRot(pos_x, pos_y, theta): # Counterclockwise, compensating
  c = math.cos(theta)
  s = math.sin(theta)
  return c*pos_x + s*pos_y, 0 - s*pos_x + c*pos_y

def top_corner_adjustment(orig_x, orig_y, w, h, theta):
  """Used for the correct top corner of the frame containing the wall, 
so that the (pre-rotation) top-left corner of the WALL is at  orig_x, orig_y.
That is, the wall can be thought of as drawn with corner at orig_x, orig_y,
then rotated clockwise through angle theta around this anchoring corner."""
  quadrant = (math.floor(theta / (0.5*math.pi)) % 4 ) + 1 # Clockwise from 
  if quadrant == 1:
    return orig_x - h*math.sin(theta), orig_y
  elif quadrant == 2:
    d = math.sqrt(h**2 + w**2)
    direction_angle = theta - math.atan(w / h)
    return orig_x - d*math.sin(direction_angle), orig_y + h*math.cos(theta) # cosine is negative.
  elif quadrant == 3:
    d = math.sqrt(h**2 + w**2)
    direction_angle = theta - math.atan(w / h)
    return orig_x - w*math.sin(theta - math.pi/2), orig_y + d*math.cos(direction_angle)
  else: # quadrant == 4
    return orig_x, orig_y + w*math.cos(theta - math.pi/2)

def draw_agent(windowSurface): # the coordinates are global vars
  pygame.draw.circle(windowSurface, GREEN, (agent_x, agent_y), agent_r)
  pygame.draw.line(windowSurface, BLACK, (agent_x, agent_y), (agent_x + math.cos(direction)*indicator_length, agent_y + math.sin(direction)*indicator_length))

def draw_gold(windowSurface):
  for coords in gold:
    pygame.draw.circle(windowSurface, GOLD, coords, gold_r)

def draw_walls(windowSurface):
  for params in walls:
    clientSurface = pygame.Surface((params[2], params[3]))
    clientSurface = clientSurface.convert_alpha()
    pygame.draw.rect(clientSurface, BLACK, (0, 0, params[2], params[3]))
    clientSurface = pygame.transform.rotate(clientSurface, 0 - params[4]*180/math.pi) # Format is consistent with js
    newX, newY = top_corner_adjustment(params[0], params[1], params[2], params[3], params[4])
    windowSurface.blit(clientSurface, (newX, newY))


def draw(windowSurface, envMode = False):
  windowSurface.fill(WHITE)
  draw_agent(windowSurface)
  draw_walls(windowSurface)
  draw_gold(windowSurface)
  if not envMode:
    pygame.display.update()

draw(windowSurface)

# Overlap-detection, updating funcs

def mod2pi(theta):
  rotationAngle = math.floor(theta/(2*math.pi))*2*math.pi
  return theta-rotationAngle

def spot_overlap_check(x, y, spot_x, spot_y, spot_r):
  pointing = (x - spot_x, y - spot_y)
  overlap = math.sqrt(pointing[0]**2 + pointing[1]**2) - agent_r - spot_r
  if (overlap < 0):
    return True
  else:
    return False

def gold_update():
  global reward
  for i in range(len(gold) -1, -1, -1):
    if (spot_overlap_check(agent_x, agent_y, gold[i][0], gold[i][1], gold_r)):
      del gold[i]
      reward += 1;
      print("Reward: " + str(reward));

def universal_update(envMode = False):
  gold_update()
  draw(windowSurface, envMode)
  if not envMode:
    sleep(1.0/10)

def wall_overlap_check(old_agent_x, old_agent_y, wall_x, wall_y, wall_w, wall_h, wall_theta):
  agent_x, agent_y = backRot(old_agent_x, old_agent_y, wall_theta);
  left_lim, top_lim = backRot(wall_x, wall_y, wall_theta)
  right_lim = left_lim + wall_w
  bot_lim = top_lim + wall_h
  if ((agent_y >= top_lim) and (agent_y <= bot_lim) and (agent_x >= left_lim) and (agent_x <= right_lim)): # Exotic case, agent inside wall
    return True
  elif ((agent_y >= top_lim) and (agent_y <= bot_lim) and (agent_x <= left_lim) and (agent_x + agent_r > left_lim)): # Hitting from the left
    return True
  elif ((agent_y >= top_lim) and (agent_y <= bot_lim) and (agent_x >= right_lim) and (agent_x - agent_r < right_lim)): # Hitting from the right
    return True
  elif ((agent_x >= left_lim) and (agent_x <= right_lim) and (agent_y <= top_lim) and (agent_y + agent_r > top_lim)): # Hitting from the top
    return True
  elif ((agent_x >= left_lim) and (agent_x <= right_lim) and (agent_y >= bot_lim) and (agent_y - agent_r < bot_lim)): # Hitting from the bottom 
    return True
  elif (spot_overlap_check(agent_x, agent_y, left_lim, top_lim, 0)): # 4 corner checks 
    return True
  elif (spot_overlap_check(agent_x, agent_y, right_lim, top_lim, 0)):
    return True
  elif (spot_overlap_check(agent_x, agent_y, left_lim, bot_lim, 0)):
    return True
  elif (spot_overlap_check(agent_x, agent_y, right_lim, bot_lim, 0)):
    return True
  else:
    return False

def full_wall_check(test_x, test_y):
  for params in walls:
    if wall_overlap_check(test_x, test_y, params[0], params[1], params[2], params[3], params[4]):
      return False
  return True

def biggest_step(lim, coords_from_step):
  for i in range(lim, -1, -1):
    test_x, test_y = coords_from_step(i)
    if full_wall_check(test_x, test_y):
      return i
  return 0

## Full definition of actions from here.

def stepForward(lim=10, envMode = False):
  global agent_x
  global agent_y
  global direction
  stepSize = biggest_step(lim, lambda step : (agent_x + step*math.cos(direction), agent_y + step*math.sin(direction)))
  agent_x += stepSize*math.cos(direction)
  agent_y += stepSize*math.sin(direction)
  universal_update(envMode)

def stepBackward(lim=10, envMode = False):
  global agent_x
  global agent_y
  global direction
  stepSize = biggest_step(lim, lambda step : (agent_x - step*math.cos(direction), agent_y - step*math.sin(direction)))
  agent_x -= stepSize*math.cos(direction)
  agent_y -= stepSize*math.sin(direction)
  universal_update(envMode)

def swivel_anticlock(envMode = False):
  global direction
  direction = mod2pi(direction + math.pi/30)
  universal_update(envMode)

def swivel_clock(envMode = False):
  global direction
  direction = mod2pi(direction - math.pi/30)
  universal_update(envMode)


actions = [(lambda : None), stepForward, stepBackward, swivel_clock, swivel_anticlock] # Later, for the official env.
# Code to actually update everything
pygame.display.update() 

while True:
  keys=pygame.key.get_pressed()
  if keys[K_LEFT]:
    swivel_clock()
  if keys[K_RIGHT]:
    swivel_anticlock()
  if keys[K_UP]:
    stepForward()
  if keys[K_DOWN]:
    stepBackward() 
  # Adding in a 'sleep' by default means some keypresses are just missed, which is a shame
  # It's possible that, in 'env mode', there should be no sleep, with the environment updates triggered by agent actions alone.
  for event in pygame.event.get():
    if event.type == QUIT:
      pygame.quit()
      sys.exit()

