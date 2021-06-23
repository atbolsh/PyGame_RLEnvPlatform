import pygame, sys
from pygame.locals import *
import math
import numpy as np
from time import sleep
from copy import deepcopy

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

GOLD = (255, 200, 0)


class DiscreteEngine2:
  def __init__(self,
               env_width = 800,
               env_height = 800,
               initial_direction = 0,
               indicator_length = 400,
               initial_reward = 0,
               initial_agent_x = 400,
               initial_agent_y = 400,
               agent_r = 40,
               gold_r = 10,
               mode = 'machine',
               initial_gold = None,
               walls = None):
    self.env_width = env_width
    self.env_height = env_height
    self.initial_direction = initial_direction
    self.indicator_length = indicator_length
    self.initial_reward = initial_reward
    self.initial_agent_x = initial_agent_x
    self.initial_agent_y = initial_agent_y
    self.agent_r = agent_r
    self.gold_r = gold_r
    self.mode = mode # 'human' or 'machine'
    if initial_gold is not None: # Should be list of [x, y] positions
      self.initial_gold = initial_gold
    else:
      self.initial_gold = []
    if walls is not None: # Should be list of [top_left_x, top_left_y, width, height, rotation_angle] values
      self.walls = walls
    else:
      self.walls = []

    self.action_space = [(lambda : None), self.stepForward, self.stepBackward, self.swivel_clock, self.swivel_anticlock] 

    pygame.init()
    if mode == 'human':
      self.windowSurface = pygame.display.set_mode((self.env_width, self.env_height), 0, 32)
      pygame.display.set_caption('discrete engine2')
    elif mode == 'machine':
      self.windowSurface = pygame.Surface((self.env_width, self.env_height))
    else:
      raise AttributeError("mode must be 'human' or 'machine'")

#    self.par = pygame.PixelArray(self.windowSurface)
    self.reset()
    
  def reset(self):
    self.direction = self.initial_direction
    self.reward = self.initial_reward
    self.gold = deepcopy(self.initial_gold)
    self.agent_x = self.initial_agent_x
    self.agent_y = self.initial_agent_y
    self.draw()
    return self.get_array()

  def step(self, actionInd):
    prev_reward = self.reward
    self.action_space[actionInd]() # If needed, incudes a draw and display update
    reward_delta = self.reward - prev_reward
    done = False # Maybe change later.
    info = {'done': False} # Maybe change later.
    return self.get_array(), reward_delta, done, info 
  # draw funcs

  def draw(self):
    self.windowSurface.fill(WHITE)
    self.draw_agent()
    self.draw_walls()
    self.draw_gold()
    if self.mode == 'human': # stay in human-mode for now
      pygame.display.update() 

  def backRot(self, pos_x, pos_y, theta): # Counterclockwise, compensating
    c = math.cos(theta)
    s = math.sin(theta)
    return c*pos_x + s*pos_y, 0 - s*pos_x + c*pos_y
  
  def top_corner_adjustment(self, orig_x, orig_y, w, h, theta):
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
  
  def draw_agent(self): # the coordinates are global vars
    pygame.draw.circle(self.windowSurface, GREEN, (self.agent_x, self.agent_y), self.agent_r)
    pygame.draw.line(self.windowSurface, BLACK, (self.agent_x, self.agent_y),\
                     (self.agent_x + math.cos(self.direction)*self.indicator_length, self.agent_y + math.sin(self.direction)*self.indicator_length))
  
  def draw_gold(self):
    for coords in self.gold:
      pygame.draw.circle(self.windowSurface, GOLD, coords, self.gold_r)
  
  def draw_walls(self):
    for params in self.walls:
      clientSurface = pygame.Surface((params[2], params[3]))
      clientSurface = clientSurface.convert_alpha()
      pygame.draw.rect(clientSurface, BLACK, (0, 0, params[2], params[3]))
      clientSurface = pygame.transform.rotate(clientSurface, 0 - params[4]*180/math.pi) # Format is consistent with js
      newX, newY = self.top_corner_adjustment(params[0], params[1], params[2], params[3], params[4])
      self.windowSurface.blit(clientSurface, (newX, newY))

  # Funcs for rgb-array
  
  def rgb(self, val):
    return val // 65536, (val // 256) % 256, val % 256

  def get_array(self): # Probably not the fastest, but I'll replace it later. Maybe something on the gpu.
    par = pygame.PixelArray(self.windowSurface)
    return_val = np.zeros((3, self.env_width, self.env_height))
    for i in range(self.env_width):
      for j in range(self.env_height):
        val = par[i, j]
        return_val[0, i, j], return_val[1, i, j], return_val[2, i, j] = self.rgb(val)
    par.close() # Release the surface lock
    return return_val
 
  # Overlap-detection, updating funcs

  def mod2pi(self, theta):
    rotationAngle = math.floor(theta/(2*math.pi))*2*math.pi
    return theta-rotationAngle
  
  def spot_overlap_check(self, x, y, spot_x, spot_y, spot_r):
    pointing = (x - spot_x, y - spot_y)
    overlap = math.sqrt(pointing[0]**2 + pointing[1]**2) - self.agent_r - spot_r
    if (overlap < 0):
      return True
    else:
      return False
  
  def gold_update(self):
    for i in range(len(self.gold) -1, -1, -1):
      if (self.spot_overlap_check(self.agent_x, self.agent_y, self.gold[i][0], self.gold[i][1], self.gold_r)):
        del self.gold[i]
        self.reward += 1;
        print("Reward: " + str(self.reward));
  
  def universal_update(self):
    self.gold_update()
    self.draw()
#    if not envMode:
#      sleep(1.0/10)
  
  def wall_overlap_check(self, old_agent_x, old_agent_y, wall_x, wall_y, wall_w, wall_h, wall_theta):
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
    elif (self.spot_overlap_check(agent_x, agent_y, left_lim, top_lim, 0)): # 4 corner checks 
      return True
    elif (self.spot_overlap_check(agent_x, agent_y, right_lim, top_lim, 0)):
      return True
    elif (self.spot_overlap_check(agent_x, agent_y, left_lim, bot_lim, 0)):
      return True
    elif (self.spot_overlap_check(agent_x, agent_y, right_lim, bot_lim, 0)):
      return True
    else:
      return False
  
  def full_wall_check(self, test_x, test_y):
    for params in self.walls:
      if self.wall_overlap_check(test_x, test_y, params[0], params[1], params[2], params[3], params[4]):
        return False
    return True
  
  def biggest_step(self, lim, coords_from_step):
    for i in range(lim, -1, -1):
      test_x, test_y = coords_from_step(i)
      if self.full_wall_check(test_x, test_y):
        return i
    return 0

  # Full definition of actions from here.

  def stepForward(self, lim=10):
    stepSize = self.biggest_step(lim, lambda step : (self.agent_x + step*math.cos(self.direction), self.agent_y + step*math.sin(self.direction)))
    self.agent_x += stepSize*math.cos(self.direction)
    self.agent_y += stepSize*math.sin(self.direction)
    self.universal_update()
  
  def stepBackward(self, lim=10):
    stepSize = self.biggest_step(lim, lambda step : (self.agent_x - step*math.cos(self.direction), self.agent_y - step*math.sin(self.direction)))
    self.agent_x -= stepSize*math.cos(self.direction)
    self.agent_y -= stepSize*math.sin(self.direction)
    self.universal_update()
  
  def swivel_anticlock(self):
    self.direction = mod2pi(self.direction + math.pi/30)
    self.universal_update(envMode)
  
  def swivel_clock(self):
    self.direction = mod2pi(self.direction - math.pi/30)
    self.universal_update()


if __name__ == "__main__":
  from dict_levels.tool_use_advanced import arg_dict
  env = DiscreteEngine2(**arg_dict, mode = 'human') # Debugging purposes only. Will not capture keystrokes.

