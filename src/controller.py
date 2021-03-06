import pygame as py
import math
import threading as th
import os
import sys
import copy
from os import path
from src import sprites
vec = py.math.Vector2

def collideHitRect(one, two):    #callback function for collision comparison, returns a bool
    return one.hit_rect.colliderect(two.rect)

class Controller():
    def __init__(self):
        '''Initialize all the settings for the game'''
        #Initalize
        py.mixer.pre_init(88200, -16, 1, 256)
        py.init()
        py.mixer.init()
        py.font.init()

        #Game
        self.wn_width,self.wn_height = 1920,1024
        self.tile_size =32
        self.wn = py.display.set_mode((self.wn_width,self.wn_height))
        self.state = "MENU"

        #Time
        self.clock = py.time.Clock()
        self.dt = self.clock.tick(30)/1000.0

        #Images
        self.background = py.transform.scale(py.image.load('assets/Background.jpg').convert_alpha(), (self.wn_width,self.wn_height))
        self.player_images = ('assets/blueTank.png', 'assets/bluecannon.png' )
        self.enemy_images =  {"brownTank":'assets/brownTank.png', "brownTurret":'assets/brownTurret.png',
                              "greyTank" : 'assets/greyTank.png', "greyTurret":'assets/greyTurret.png'}

        self.bullet_image =  'assets/bulletSilver_outline.png'
        self.wall_image = 'assets/wall.png'
        self.tracksLarge = py.transform.scale(py.image.load('assets/tracksLarge.png').convert_alpha(), (64,64))

        #Minigame Features
        self.timer = 0
        self.last_shot = 0
        self.enemy_count = 0
        self.lives = 3
        self.score = 0
        self.mission_number = 1

        #Mission maps
        self.missions = {1 :'src/mission1.txt', 2 :'src/mission2.txt', 3:'src/mission3.txt'}
        self.new_mission = self.missions[self.mission_number]

        #Colors
        self.green, self.bright_green, self.red, self.bright_red, self.cyan, self.bright_cyan , self.black, self.white, self.yellow = (0,240,0),(0,200,0),(255,0,0),(220,0,0),(0,255,255),(90,255,255),(0,0,0),(255,255,255), (255,255,0)

        #Sounds
        self.trumpet_sound = py.mixer.Sound('assets/trumpet_intro.wav')
        self.explosion = py.mixer.Sound('assets/explosion.wav')
        self.shoot = py.mixer.Sound('assets/shoot.wav')
        self.mission_complete = py.mixer.Sound('assets/round_end.wav')
        self.mission_failed = py.mixer.Sound('assets/mission_failed.wav')

        #Enemy stats
        self.enemy_rounds_per_sec = 1.5

        #Miscellaneous
        self.mouse_pos = py.mouse.get_pos()
        self.keys  = py.key.get_pressed()
        self.bullet_spawned = False
        self.hit_flag = True
        self.timer_flag = False
        self.paused_flag = True
        self.paused = False
        self.count_flag = True
        self.respawn_flag = True

    def mainLoop(self):
        while True:
            if(self.state == "MENU"):
                self.menuLoop()
            elif(self.state == "GAMEON"):
                self.introLoop()
            elif(self.state == "GAME"):
                self.gameLoop()
            elif(self.state == "GAMEOVER"):
                self.gameOverLoop()
            elif(self.state == "GAMEWON"):
                self.youWinLoop()

    def loadSprites(self):
        '''Create instances of sprite classes '''
        self.enemies = py.sprite.Group()
        self.turrets = py.sprite.Group()
        self.bullets = py.sprite.Group()
        self.walls = py.sprite.Group()

        self.new_mission = self.missions[self.mission_number]

        with open(self.new_mission, 'r') as fref:          #reads data in file
            self.map_data = []
            for line in fref:
                self.map_data.append(line)            # add each line of data into an array

            for row, tiles in enumerate(self.map_data):    #enumerate returns index and item, go through every row

                for col, tile in enumerate(tiles):         #for each row, go through its string one column at a time
                    '''an exact coordinate (row, col) says where to spawn on screen'''
                    if tile == '1':         #spawn a wall at any column/row (map.txt)
                        self.wall = sprites.Wall( col, row, self.walls, self.wall_image)
                        self.walls.add(self.wall)
                    if tile == 'P':         #set spawn point for player
                        self.tank = sprites.Player(col*self.tile_size, row*self.tile_size, self.dt, self.player_images[0], self.walls)
                        self.cannon = sprites.Cannon(col*self.tile_size, row*self.tile_size , self.dt, self.player_images[1], self.walls)
                        self.spawn_point = (col*self.tile_size, row*self.tile_size)
                    if tile == 'B':         #set spawn point for enemies
                        self.enemy = sprites.Enemy(col*self.tile_size, row*self.tile_size, self.enemy_images["brownTank"], self.dt, self.tank.pos, self.walls, 'B')
                        self.turret = sprites.Turret(col*self.tile_size, row*self.tile_size, self.enemy_images["brownTurret"], self.dt, self.tank.pos, self.walls, 'B')
                        self.enemies.add((self.enemy, self.turret))
                        self.turrets.add(self.turret)
                        self.enemy_count += 1
                    if tile == 'G':
                        self.enemy = sprites.Enemy(col*self.tile_size, row*self.tile_size, self.enemy_images["greyTank"], self.dt, self.tank.pos, self.walls, 'G')
                        self.turret = sprites.Turret(col*self.tile_size, row*self.tile_size, self.enemy_images["greyTurret"], self.dt, self.tank.pos, self.walls, 'G')
                        self.enemies.add((self.enemy, self.turret))
                        self.turrets.add(self.turret)
                        self.enemy_count += 1

            self.all_sprites = py.sprite.Group((self.tank,), (self.cannon,), tuple(self.walls), tuple(self.enemies), tuple(self.bullets))

    def reloadSprites(self, tank, cannon):
        self.all_sprites.add(tank)
        self.all_sprites.add(cannon)


    def menuLoop(self):
        '''The GUI, where the user can start the game. Has nested functions which make creating objects easier. '''
        py.display.set_caption("PyTanks!")

        py.mixer.music.load('assets/menu_music.wav')
        py.mixer.music.play(-1)

        #Function to make creating text easier
        def text_objects(text,font):
            '''Creates a text object with desired font '''
            textSurface = font.render(text, True, (0,0,0))
            return textSurface,textSurface.get_rect()

        #Function to actually place text on screen
        def textToScreen(msg,font,size,x,y):
            Text = py.font.Font(font,size)
            TextSurf, TextRect = text_objects(msg, Text)
            TextRect.center = (x,y)
            self.wn.blit(TextSurf, TextRect)

        #Function to make creating buttons easier
        def button(msg,x,y,w,h,ic,ac,ts,action=None):
            '''Makes a functional button, when pressed calls a method '''
            mouse = py.mouse.get_pos()
            click = py.mouse.get_pressed()
            if x+w > mouse[0] > x and y+h > mouse[1] > y:
                py.draw.rect(self.wn, ic,(x,y,w,h))
                if click[0] == 1 and action != None:
                    if action == 'play':
                        self.introLoop()
                    elif action == 'exit':
                        sys.exit()
                    elif action == 'controls':
                        controlScreen()
                    else:
                        action()

            else:
                py.draw.rect(self.wn, ac,(x,y,w,h))

            textToScreen(msg,'freesansbold.ttf',ts,(x+(w/2)),(y+(h/2)))

        #Trying to find out how to leave control menu
        def exitControl():
            '''This was never completed lol. '''
            super()

        #Screen to display controls
        def controlScreen():

            #Creating control screen window
            self.wn_width,self.wn_height = 1920,1024
            self.wn = py.display.set_mode((self.wn_width,self.wn_height))
            self.wn.fill(self.white)

            cont = True
            while cont:
                for event in py.event.get():
                    if event.type == py.QUIT:
                        sys.exit()

                #self.wn.blit is necessary for the first text object of each screen in the GUI
                self.wn.blit(self.background, (0,0))
                textToScreen("Controls",'freesansbold.ttf',105,(self.wn_width/2),(self.wn_height/2)-400)

                button("",640,820,245,130,self.black,self.black,50)
                button("PLAY",640,820,230,115,self.green,self.bright_green,50,'play')
                button("",1040,820,245,130,self.black,self.black,70)
                button("EXIT",1040,820,230,115,self.red,self.bright_red,50,'exit')
                #button("",10,10,180,90,self.black,self.black,30)
                #button("RETURN",10,10,170,80,self.bright_cyan,self.cyan,30,exitControl)

                # Write Controls Under Here:
                textToScreen("WASD: Forwards/Turn Left/Turn Right/Backwards",'freesansbold.ttf',65,(self.wn_width/2),(self.wn_height/2)-250)
                textToScreen("Left Click: Fire",'freesansbold.ttf',65,(self.wn_width/2),(self.wn_height/2)-160)

                py.display.flip()

        while True:

            self.clock.tick(20)

            for event in py.event.get():
                if event.type == py.QUIT:
                    sys.exit()

            #Creates Title Text
            self.wn.blit(self.background, (0,0))
            textToScreen("PyTanks!",'freesansbold.ttf',155,(self.wn_width/2),(self.wn_height/2)-150)

            #Creating Buttons
            #Every other button acts as a drop shadow
            button("",580,750,320,170,self.black,self.black,70)
            button("PLAY",580,750,300,150,self.green,self.bright_green,70,'play')
            button("",1030,750,320,170,self.black,self.black,70)
            button("EXIT",1030,750,300,150,self.red,self.bright_red,70,'exit')
            button("",10,10,210,110,self.black,self.black,30)
            button("CONTROLS",10,10,200,100,self.bright_cyan,self.cyan,30,'controls')

            #Tank Images for Main Menu
            self.mainMenuTank = py.image.load('assets/MainMenuTank.png')
            self.wn.blit(self.mainMenuTank, (100,400))
            self.mainMenuTank = py.image.load('assets/MainMenuTankReverse.png')
            self.wn.blit(self.mainMenuTank, (1425,400))

            py.display.update()

    def introLoop(self):
        ''' Screen that displays the mission number with trumpet accompaniment '''
        if self.respawn_flag:
            self.loadSprites()
        #Function to make creating text easier
        def text_objects(text,font):
            textSurface = font.render(text, True, (0,0,0))
            return textSurface,textSurface.get_rect()

        #Function to actually place text on screen
        def textToScreen(msg,font,size,x,y):
            Text = py.font.Font(font,size)
            TextSurf, TextRect = text_objects(msg, Text)
            TextRect.center = (x,y)
            self.wn.blit(TextSurf, TextRect)

        #Function to make creating buttons easier
        def button(msg,x,y,w,h,ic,ac,ts,action=None):
            mouse = py.mouse.get_pos()
            click = py.mouse.get_pressed()
            if x+w > mouse[0] > x and y+h > mouse[1] > y:
                py.draw.rect(self.wn, ic,(x,y,w,h))

            else:
                py.draw.rect(self.wn, ac,(x,y,w,h))

            textToScreen(msg,'freesansbold.ttf',ts,(x+(w/2)),(y+(h/2)))

        self.wn_width,self.wn_height = 1920,1024
        self.wn = py.display.set_mode((self.wn_width,self.wn_height))
        self.wn.fill(self.white)
        py.mixer.music.pause()
        self.trumpet_sound.play()
        py.time.set_timer(py.USEREVENT, 3 * 1000)
        cont = True
        while cont:

            for event in py.event.get():
                if event.type == py.QUIT:
                    sys.exit()
                if event.type == py.USEREVENT:
                    self.gameLoop()

            self.wn.blit(self.background, (0,0))

            #Messages
            missionMessage = "Mission " + str(self.new_mission[-5])
            enemyRemaining = "Enemy Tanks: "+ str(self.enemy_count)
            livesRemaining = str(self.lives)

            button("",0,self.wn_height//3,self.wn_width,250,self.red,self.red,100)
            textToScreen(missionMessage,'freesansbold.ttf',120,(0+(self.wn_width/2)),(self.wn_height//3+(250/2))-30)
            textToScreen(enemyRemaining,'freesansbold.ttf',50,(0+(self.wn_width/2)),(self.wn_height//3+(250/2))+70)
            button("",0,(self.wn_height//3)+235,self.wn_width,10,self.yellow,self.yellow,100)
            button("",0,(self.wn_height//3)+5,self.wn_width,10,self.yellow,self.yellow,100)


            self.livesTank = py.image.load('assets/livesTank.png')
            self.wn.blit(self.livesTank,((self.wn_width//2)-230,800))
            textToScreen("X",'freesansbold.ttf',85,self.wn_width//2,880)
            textToScreen(livesRemaining,'freesansbold.ttf',85,(self.wn_width//2)+110,880)

            py.display.flip()

    def gameLoop(self):

        self.count_flag = True
        self.loop_once = True

        if not self.paused:
            py.mixer.music.load('assets/game_music.wav')
            py.mixer.music.play(-1)
            py.mixer.music.set_volume(0.5)
            py.time.set_timer(py.USEREVENT, int(self.enemy_rounds_per_sec) * 1000)

        while True: #handle events

            keys  = py.key.get_pressed()
            self.mouse_angle = self.cannon.getMouseAngleRad()

            self.bullet_timer = py.time.get_ticks()
            if self.bullet_timer > 5 * 1000:
                self.timer_flag = True



            for event in py.event.get():

                if event.type == py.QUIT or keys[py.K_ESCAPE]:
                    sys.exit()

                if event.type == py.MOUSEBUTTONDOWN:

                    if not self.tank.collideWithAnyWall():
                        now = py.time.get_ticks()
                        if (now - self.last_shot > 500) and self.timer_flag:     #prevents bullet spaming
                            self.shoot.play()
                            self.last_shot = now
                            self.bullet_spawned = True
                            self.bullet = sprites.Projectile(self.tank.pos.x + self.tank.width*math.cos(self.mouse_angle), self.tank.pos.y - self.tank.height*math.sin(self.mouse_angle), self.cannon.getMouseAngle(), self.dt, self.bullet_image, self.walls)
                            self.bullets.add(self.bullet)
                            self.all_sprites.add(self.bullet)

                if keys[py.K_p]:
                    self.paused = not self.paused

                if event.type == py.USEREVENT:


                    for self.turret in self.turrets:

                        dist_bt_plyr_enmy_squared = (self.tank.pos.x - self.turret.pos.x)**2 + (self.tank.pos.y - self.turret.pos.y)**2
                        target_radius = 600
                        if dist_bt_plyr_enmy_squared < target_radius**2:
                            if not self.turret.collideWithAnyWall():
                                self.turret.shoot()
                                self.shoot.play()
                                self.shoot_flag = True
                                if self.shoot_flag:
                                    self.bullets.add(self.turret.bullet)
                                    self.all_sprites.add(self.turret.bullet)
                                    self.shoot_flag = False


            for self.bullet in self.bullets:
                hits = py.sprite.groupcollide(self.bullets, self.enemies, False, True, collideHitRect)
                if hits:

                    self.explosion.play()
                    now = py.time.get_ticks()
                    hit_time = 0
                    if now - hit_time > 500 and not self.hit_flag:

                        self.score += 1
                        self.enemy_count -= 1
                        hit_time = now
                        self.bullet.kill()
                        self.hit_flag = True
                    else:
                        self.hit_flag = False

            if self.enemy_count == 0 and self.count_flag : #Next Mission

                self.count_flag = False
                self.respawn_flag = True
                self.mission_number += 1

                if self.mission_number == 4:
                    self.youWinLoop()
                elif self.mission_number < 4:
                    for sprite in self.all_sprites:
                        sprite.kill()
                    self.missionCompleteLoop()

            hits = py.sprite.spritecollideany(self.tank, self.bullets, collideHitRect)
            if hits:
                now = py.time.get_ticks()
                hit_time = 0
                self.lives -= 1
                if self.loop_once:

                    self.tank.remove()
                    self.cannon.remove()
                    self.loop_once = False
                if now - hit_time > 500:
                    hit_time = now
                    for self.bullet in self.bullets:
                        self.bullet.kill()
                    self.hit_flag = True
                    self.respawn_flag = True
                    if self.lives > 0:
                        self.explosion.play()
                        self.missionFailedLoop()
                    else:
                        self.gameOverLoop()

            if not self.paused:
                self.paused_flag = True
                py.mixer.music.unpause()

                for self.bullet in self.bullets:

                    self.bullet.update()

                self.all_sprites.update()

                for sprite in self.all_sprites:
                    self.wn.blit(sprite.image, sprite.rect)

                py.display.flip()

                self.wn.blit(self.background,(0,0))     #stamps background on top of prev frame


            elif self.paused:
                py.mixer.music.pause()
                self.font = py.font.SysFont('', 150, bold=True)
                self.paused_surf = self.font.render('PAUSED', True, self.red)
                self.paused_rect = self.paused_surf.get_rect()
                self.dim_screen = py.Surface(self.wn.get_size()).convert_alpha()
                self.dim_screen.fill((0,0,0,180))
                py.display.flip()
                if self.paused_flag:
                    self.all_sprites.draw(self.wn)
                    self.wn.blit(self.dim_screen, (0,0))
                    self.paused_flag = False

                self.wn.blit(self.paused_surf, (750,450))



    def missionCompleteLoop(self):
        py.mixer.music.pause()
        self.mission_complete.play()
        py.time.set_timer(py.USEREVENT, 3 * 1000)
        while 1:
            for event in py.event.get():
                if event.type == py.QUIT:
                    sys.exit()
                if event.type == py.USEREVENT:
                    self.introLoop()

    def missionFailedLoop(self):
        py.mixer.music.pause()
        self.mission_failed.play()
        py.time.set_timer(py.USEREVENT, 3 * 1000)
        while 1:
            for event in py.event.get():
                if event.type == py.QUIT:
                    sys.exit()
                if event.type == py.USEREVENT:
                    self.gameLoop()

    def youWinLoop(self):

        keys  = py.key.get_pressed()
        py.mixer.music.load('assets/you_win.wav')
        py.mixer.music.play()
        timer = py.time.set_timer(py.USEREVENT , 20 * 1000)
        while 1:
            for event in py.event.get():
                if event.type == py.QUIT or keys[py.K_ESCAPE]:
                    sys.exit()
                if event.type == py.USEREVENT:
                    sys.exit()

    def gameOverLoop(self):

        keys  = py.key.get_pressed()
        py.mixer.music.load('assets/gameover_music.wav')
        py.mixer.music.play()
        timer = py.time.set_timer(py.USEREVENT , 15 * 1000)
        while 1:
            for event in py.event.get():
                if event.type == py.QUIT or keys[py.K_ESCAPE] :
                    sys.exit()
                if event.type == py.USEREVENT:
                    sys.exit()

        #game over display
        #show how many tanks the player destroyed
        #prompt the menu loop
