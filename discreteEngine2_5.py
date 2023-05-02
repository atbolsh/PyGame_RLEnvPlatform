import pygame, sys
from pygame.locals import *
import math
from time import sleep
from copy import deepcopy
import numpy as np
import random

from levels.skeleton2_5 import *


class discreteGame:
    def __init__(self, settings = None, envMode = False):
        # params for random initialization; usually ignored (put them into a Settings object?)
        self.typical_indicator_length = 0.5
        self.typical_wall_width = 100/800
        self.side_wall_width = 50/800
        self.typical_min_wall_height = 300/800
        self.typical_max_wall_height = 600 / 800
        self.typical_max_wall_num = 3 # not counting side walls
        self.typical_agent_r = 0.05
        self.typical_gold_r = 1.0/64
        self.typical_max_gold_num = 4
        if settings is None:
            settings = self.random_settings()

        # End of randomization params
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
 
    ####### Functions for drawing / evaluating position.
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
    
    ####### Overlap detection / updating function
    def mod2pi(self, theta):
        rotationAngle = math.floor(theta/(2*math.pi))*2*math.pi
        return theta-rotationAngle
    
    def spot_overlap_check(self, x, y, spot_x, spot_y, spot_r, agent_r=None):
        if agent_r is None:
            agent_r = self.settings.agent_r # typical case; also used for generating random games, hence the ambiguity.
        pointing = (x - spot_x, y - spot_y)
        overlap = math.sqrt(pointing[0]**2 + pointing[1]**2) - agent_r - spot_r
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
    
    def wall_overlap_check(self, old_agent_x, old_agent_y, wall_x, wall_y, wall_w, wall_h, wall_theta, agent_r = None):
        if agent_r is None:
            agent_r = self.settings.agent_r # we can use this to test gold placement for randomly generated levels, hence why different r's
        agent_x, agent_y = self.backRot(old_agent_x, old_agent_y, wall_theta)
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
        elif (self.spot_overlap_check(agent_x, agent_y, left_lim, top_lim, 0, agent_r)): # 4 corner checks 
            return True
        elif (self.spot_overlap_check(agent_x, agent_y, right_lim, top_lim, 0, agent_r)):
            return True
        elif (self.spot_overlap_check(agent_x, agent_y, left_lim, bot_lim, 0, agent_r)):
            return True
        elif (self.spot_overlap_check(agent_x, agent_y, right_lim, bot_lim, 0, agent_r)):
            return True
        else:
            return False
      
    def full_wall_check(self, test_x, test_y, walls=None, agent_r=None):
        if walls is None: # This is also used for random level generation, placing both gold and the agent, hence the ambiguity
            walls = self.settings.walls
        for params in walls:
            if self.wall_overlap_check(test_x, test_y, params[0], params[1], params[2], params[3], params[4], agent_r):
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

    ####### Function for "Arcade" UI   
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

    ####### Functions for machine UI: numpy arrays and zoomed-in numpy arrays as output.
    def getData(self):
        return pygame.surfarray.array3d(self.windowSurface)

    def blowup(self, factor):
        bigSettings = deepcopy(self.settings)
        bigSettings.gameSize = int(factor*self.settings.gameSize)
        slave = discreteGame(bigSettings, envMode=True)
        return slave.getData()

    def _zoom_helper(self, center, factor, canvas):
        bigSize = int(factor*self.settings.gameSize)
        maxCenterCoord = int(bigSize - (self.settings.gameSize/2))
        centerX = min(int(center[0]*factor*self.settings.gameSize), maxCenterCoord)
        centerY = min(int(center[1]*factor*self.settings.gameSize), maxCenterCoord)
        leftPoint = max(int(centerX - (self.settings.gameSize / 2)), 0)
        topPoint = max(int(centerY - (self.settings.gameSize / 2)), 0)
        return canvas[leftPoint:leftPoint + self.settings.gameSize, topPoint:topPoint + self.settings.gameSize]

    def zoom(self, centers, factor):
        assert factor >= 1, "factor must be larger than 1.9"
        canvas = self.blowup(factor) # this part may be slow; a better function would only draw what's in frame.
        batch = np.zeros((len(centers), self.settings.gameSize, self.settings.gameSize, 3))
        for i in range(len(centers)):
            batch[i] = self._zoom_helper(centers[i], factor, canvas)
        return batch
           
    def random_factor(self, minFactor, maxFactor):
        return random.uniform(minFactor, maxFactor)

    def center_near(self, point, scale=None):
        if scale is None:
            scale = self.settings.gold_r
        return (random.uniform(point[0] - scale, point[0] + scale), random.uniform(point[1] - scale, point[1] + scale))

    def corners(self, wall_x, wall_y, wall_w, wall_h, wall_theta):
        c = math.cos( 0 - wall_theta )
        s = math.sin( 0 - wall_theta )
        width_offset_x = wall_w * c
        width_offset_y = wall_w * s
        height_offset_x = wall_h * s # CHECK ME!
        height_offset_y = wall_h * c

        ul = (wall_x, wall_y)
        ur = (wall_x + width_offset_x, wall_y + width_offset_y)
        lr = (wall_x + width_offset_x + height_offset_x, wall_y + width_offset_y + height_offset_y)
        ll = (wall_x + height_offset_x, wall_y + height_offset_y)

        return [ul, ur, lr, ll]

    def random_point_on_line(self, a, b):
        val = random.random()
        nval = 1 - val
        return (a[0] * val + b[0] * nval, a[1] * val + b[1] * nval)

    def random_point_in_quadrilateral(self, corners):
        vals = [random.random() for i in range(4)]
        s = sum(vals)
        fracs = [v / s for v in vals]
        x = sum([fracs[i] * corners[i][0] for i in range(4)])
        y = sum([fracs[i] * corners[i][1] for i in range(4)])
        return (x, y)

    def random_wall_points(self, wall_params, num_points = 4):
        corners = self.corners(*wall_params)
        
        corner_probability = 0.8 # By far the hardest task, and the most important
        wall_probability = 0.15 # No need to go for wall interior too often, nothing there.

        points = []
        for i in range(num_points):
            val = random.random()
            if val < corner_probability:
                points.append(corners[random.randrange(0, 4)])
            elif val < corner_probability + wall_probability:
                ind1 = random.randrange(0, 4)
                ind2 = (ind1 + 1) % 4
                points.append(self.random_point_on_line(corners[ind1], corners[ind2]))
            else:
                points.append(self.random_point_in_quadrilateral(corners))
        return points

    def random_wall_centers(self, num_walls=2, num_each=2):
        points = []
        for i in range(num_walls):
            wall = random.choice(self.settings.walls)
            for point in self.random_wall_points(wall, num_each):
                points.append(point)
        return points

    def random_zoom_center(self, factor):
        offset = 1 / (2*factor)
        maxVal = 1 - offset
        x = random.uniform(offset, maxVal)
        y = random.uniform(offset, maxVal)
        return (x, y)

    def random_image_batch(self):
        """Batch of ML training images. Full picture, and zooms to some random / important places, at different magnifications"""
        num_factors = 2 # Total number of zoom factors to be used.
        num_gold = 2
        num_agent = 2
        num_walls = 2 # walls sampled for random points
        num_per_wall = 1 # random points per wall
        num_random = 3 # For each scale, 4 more random zooms will be included

        num_per_factor = num_gold + num_agent + num_walls*num_per_wall + num_random
        num_total = 1 + num_factors*num_per_factor
        
        gold_centers = [random.choice(self.settings.gold) for i in range(num_gold)]
        agent_centers = [(self.settings.agent_x, self.settings.agent_y)]
        for i in range(num_agent - 1):
            agent_centers.append(self.center_near(agent_centers[0], scale=self.settings.agent_r))
        wall_centers = self.random_wall_centers(num_walls, num_per_wall)

        rand_factor1 = random.uniform(2, 1/(4*self.settings.agent_r))
        rand_factor2 = random.uniform(3, (1/(3*self.settings.gold_r)))

        fac1List = gold_centers + agent_centers + wall_centers
        fac2List = gold_centers + agent_centers + wall_centers

        for i in range(num_random):
            fac1List.append(self.random_zoom_center(rand_factor1))
            fac2List.append(self.random_zoom_center(rand_factor2))

        batch = np.zeros((num_total, self.settings.gameSize, self.settings.gameSize, 3))
        batch[0] = self.getData()
        batch[1:(num_per_factor+1)] = self.zoom(fac1List, rand_factor1)
        batch[(num_per_factor+1):] = self.zoom(fac2List, rand_factor2)

        return batch
        
    ####### Functions for random initialization
    def random_ul_corner(self, wall_w, wall_h, wall_theta):
        corners = self.corners(0, 0, wall_w, wall_h, wall_theta)
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        mx = min(xs)
        Mx = max(xs)
        my = min(ys)
        My = max(ys)
        toplim = 1.0 - self.side_wall_width - My
        rightlim = 1.0 - self.side_wall_width - Mx
        botlim = self.side_wall_width - my
        leftlim = self.side_wall_width - mx
        return random.uniform(leftlim, rightlim), random.uniform(botlim, toplim)

    def random_wall(self):
        wall_w = self.typical_wall_width
        wall_h = random.uniform(self.typical_min_wall_height, self.typical_max_wall_height)
        wall_theta = random.uniform(0, 2*math.pi) # probably overkill, I don't think the symmetries matter for computational efficiency, though.
        wall_x, wall_y = self.random_ul_corner(wall_w, wall_h, wall_theta)
        return [wall_x, wall_y, wall_w, wall_h, wall_theta]

    def random_side_walls(self):
        walls = []
        probability_exit = 0.5
        if random.random() < probability_exit:
            exit_wall = random.randint(0, 3)
        else:
            exit_wall = -1
        for i in range(4):# left wall; top wall; bottom wall; right wall
            if i == exit_wall:
                longside = 0.5 - self.typical_agent_r
            else:
                longside = 1.0
            wall_theta = 0
            isTop = (i != 2) # all but bottom wall have ul on top.
            isLeft = (i < 3) # all but right wall have ul on left
            isHorizontal = ((i == 1) or (i == 2)) # I guess it could be cleaner . . .
            if isLeft:
                wall_x = 0
            else:
                wall_x = 1.0 - self.side_wall_width
            if isTop:
                wall_y = 0
            else:
                wall_y = 1.0 - self.side_wall_width
            if isHorizontal:
                wall_w = longside
                wall_h = self.side_wall_width
            else:
                wall_h = longside
                wall_w = self.side_wall_width
            walls.append([wall_x, wall_y, wall_w, wall_h, wall_theta])
            if i == exit_wall:
                if isHorizontal:
                    wall_y2 = wall_y
                    wall_x2 = longside + 2*self.typical_agent_r
                else:
                    wall_x2 = wall_x
                    wall_y2 = longside + 2*self.typical_agent_r
                walls.append([wall_x2, wall_y2, wall_w, wall_h, wall_theta])
        return walls

    def random_walls(self):
        walls = self.random_side_walls()
        for i in range(random.randint(1, self.typical_max_wall_num)):
            walls.append(self.random_wall())
        return walls

    def random_valid_coords(self, walls, radius):
        valid = False
        while not valid:
            test_x = random.uniform(self.side_wall_width, 1.0 - self.side_wall_width)
            test_y = random.uniform(self.side_wall_width, 1.0 - self.side_wall_width)
            valid = self.full_wall_check(test_x, test_y, walls, radius)
        return (test_x, test_y)

    def random_gold(self, walls):
        gold = []
        num_gold = random.randint(1, self.typical_max_gold_num)
        for i in range(num_gold):
            gold.append(self.random_valid_coords(walls, self.typical_gold_r))
        return gold

    def random_settings(self, gameSize=64):
        walls = self.random_walls()
        gold = self.random_gold(walls)
        agent_x, agent_y = self.random_valid_coords(walls, self.typical_agent_r)
        direction = random.uniform(0, 2*math.pi)
        res = Settings(gameSize=gameSize,
                       indicator_length = self.typical_indicator_length,
                       agent_r = self.typical_agent_r,
                       gold_r = self.typical_gold_r,
                       walls = walls,
                       gold = gold,
                       agent_x = agent_x,
                       agent_y = agent_y,
                       direction = direction)
        return res





















