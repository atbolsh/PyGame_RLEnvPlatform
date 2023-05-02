import pygame, sys
from pygame.locals import *
import math
from time import sleep
from copy import deepcopy

from levels.skeleton2_5 import *


class discreteGame:
    def __init__(self, settings, envMode = False):
        self.reward = 0
        self.envMode = envMode
        self.initial = deepcopy(settings)
        self.settings = settings

        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BLUE = (0, 0, 255)
        
        self.GOLD = (255, 200, 0)

        self.actions = [(lambda : None), self.stepForward, self.stepBackward, self.swivel_clock, self.swivel_anticlock]
 
        if envMode:
            self.windowSurface = pygame.Surface((self.settings.gameSize, self.settings.gameSize))
        else:
            # set up pygame
            pygame.init()
            # set up the window
            self.windowSurface = pygame.display.set_mode((self.settings.gameSize, self.settings.gameSize), 0, 32)
            pygame.display.set_caption('discrete engine')
               
        self.windowSurface.fill(self.WHITE)
        self.universal_update()

        if not self.envMode:
            self.humanGame()
 
    # draw funcs    
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
    
    def true_coords(self, coords):
        return coords[0]*self.settings.gameSize, coords[1]*self.settings.gameSize

    def draw_agent(self):
        # I *could* move this to the init function, but I won't for now.
        # If CPU computation becomes a problem, that's an easy optimization
        agent_x = self.settings.agent_x * self.settings.gameSize
        agent_y = self.settings.agent_y * self.settings.gameSize
        agent_r = self.settings.agent_r * self.settings.gameSize
        indicator_length = self.settings.indicator_length * self.settings.gameSize
        pygame.draw.circle(self.windowSurface, \
                           self.GREEN, \
                           (agent_x, agent_y), \
                           agent_r)
        pygame.draw.line(self.windowSurface, \
                         self.BLACK, 
                         (agent_x, agent_y), (agent_x + math.cos(self.settings.direction)*indicator_length, agent_y + math.sin(self.settings.direction)*indicator_length))
    
    def draw_gold(self):
        gold_r = self.settings.gold_r * self.settings.gameSize
        for coords in self.settings.gold:
            tc = self.true_coords(coords)
            pygame.draw.circle(self.windowSurface, self.GOLD, tc, gold_r)

    def true_wall_params(self, params):
        tp = [val * self.settings.gameSize for val in params[:4]]
        tp.append(params[4]) # angle treated differently
        return tp
    
    def draw_walls(self):
        for params in self.settings.walls:
            tp = self.true_wall_params(params)
            clientSurface = pygame.Surface((tp[2], tp[3]))
            clientSurface.fill(self.WHITE)
            clientSurface.set_colorkey(self.WHITE)
#            clientSurface = clientSurface.convert_alpha(self.windowSurface)
            pygame.draw.rect(clientSurface, self.BLACK, (0, 0, tp[2], tp[3]))
            clientSurface = pygame.transform.rotate(clientSurface, 0 - params[4]*180/math.pi) # Format is consistent with js
            newX, newY = self.top_corner_adjustment(tp[0], tp[1], tp[2], tp[3], tp[4])
            self.windowSurface.blit(clientSurface, (newX, newY))
    
    
    def draw(self):
      self.windowSurface.fill(self.WHITE)
      self.draw_agent()
      self.draw_walls()
      self.draw_gold()
      if not self.envMode:
          pygame.display.update()
    
    # Overlap-detection, updating funcs
    # Unless stated, assume unadjusted space (no gameSize multiplication)

    def mod2pi(self, theta):
        rotationAngle = math.floor(theta/(2*math.pi))*2*math.pi
        return theta-rotationAngle
    
    def spot_overlap_check(self, x, y, spot_x, spot_y, spot_r): 
      pointing = (x - spot_x, y - spot_y)
      overlap = math.sqrt(pointing[0]**2 + pointing[1]**2) - self.settings.agent_r - spot_r
      if (overlap < 0):
        return True
      else:
        return False
    
    def gold_update(self):
        # Going backward to prevent the deletions from affecting the traversal
        for i in range(len(self.settings.gold) -1, -1, -1):
            if (self.spot_overlap_check(self.settings.agent_x, \
                                   self.settings.agent_y, \
                                   self.settings.gold[i][0], \
                                   self.settings.gold[i][1], \
                                   self.settings.gold_r)):
                del self.settings.gold[i]
                self.reward += 1;
                print("Reward: " + str(self.reward));
    
    def universal_update(self):
        self.gold_update()
        self.draw()
        if not self.envMode:
            sleep(1.0/10)
    
    def wall_overlap_check(self, old_agent_x, old_agent_y, wall_x, wall_y, wall_w, wall_h, wall_theta):
        agent_x, agent_y = self.backRot(old_agent_x, old_agent_y, wall_theta)
        agent_r = self.settings.agent_r # for ease of typing the function
        left_lim, top_lim = self.backRot(wall_x, wall_y, wall_theta)
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
        for params in self.settings.walls:
            if self.wall_overlap_check(test_x, test_y, params[0], params[1], params[2], params[3], params[4]):
                return False
        return True
    
    # biggest possible step; performed in the original coordinates, NOT in the full, pixel-scale coordinates.
    def biggest_step(self, lim, coords_from_step, min_step=None):
        if min_step is None:
            min_step = 1.0/self.settings.gameSize
        step = lim
        while step > 0:
            test_x, test_y = coords_from_step(step)
            if self.full_wall_check(test_x, test_y):
                return step
            step -= min_step
        return 0
    
    ## Full definition of actions from here.
    
    def stepForward(self, lim=None):
        if lim is None:
            lim = 1.0/64 # big enough for most pixelations, small enough to make gameSize 800 interesting.
        stepSize = self.biggest_step(lim, lambda step : (self.settings.agent_x + step*math.cos(self.settings.direction), self.settings.agent_y + step*math.sin(self.settings.direction)))
        self.settings.agent_x += stepSize*math.cos(self.settings.direction)
        self.settings.agent_y += stepSize*math.sin(self.settings.direction)
        self.universal_update()
    
    def stepBackward(self, lim=None):
        if lim is None:
            lim = 1.0/64 # big enough for most pixelations, small enough to make gameSize 800 interesting.
        stepSize = self.biggest_step(lim, lambda step : (self.settings.agent_x - step*math.cos(self.settings.direction), self.settings.agent_y - step*math.sin(self.settings.direction)))
        self.settings.agent_x -= stepSize*math.cos(self.settings.direction)
        self.settings.agent_y -= stepSize*math.sin(self.settings.direction)
        self.universal_update()
    
    def swivel_anticlock(self):
        self.settings.direction = self.mod2pi(self.settings.direction + math.pi/30)
        self.universal_update()
    
    def swivel_clock(self):
        self.settings.direction = self.mod2pi(self.settings.direction - math.pi/30)
        self.universal_update()
    
    def humanGame(self):    
        assert (not self.envMode), "initialize with envMode = False to play"

        # Code to actually update everything
        self.draw()
        pygame.display.update() 

        while True:
            keys=pygame.key.get_pressed()
            if keys[K_LEFT]:
                self.swivel_clock()
            if keys[K_RIGHT]:
                self.swivel_anticlock()
            if keys[K_UP]:
                self.stepForward()
            if keys[K_DOWN]:
                self.stepBackward() 
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    return None

    def getData(self):
        return pygame.surfarray.array3d(self.windowSurface)

    def blowup(self, factor):
        bigSettings = deepcopy(self.settings)
        bigSettings.gameSize = int(factor*self.settings.gameSize)
        slave = discreteGame(bigSettings, envMode=True)
        return slave.getData()

    def zoom(self, center, factor):
        assert factor >= 1, "factor must be larger than 1.9"
        canvas = self.blowup(factor) # this part may be slow; a better function would only draw what's in frame.
        bigSize = int(factor*self.settings.gameSize)
        maxCenterCoord = int(bigSize - (self.settings.gameSize/2))
        centerX = min(int(center[0]*factor), maxCenterCoord)
        centerY = min(int(center[1]*factor), maxCenterCoord)
        leftPoint = max(int(centerX - (self.settings.gameSize / 2)), 0)
        topPoint = max(int(centerY - (self.settings.gameSize / 2)), 0)
        return canvas[leftPoint:leftPoint + self.settings.gameSize, topPoint:topPoint + self.settings.gameSize]

 
