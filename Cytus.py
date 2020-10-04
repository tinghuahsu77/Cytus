#Game modeled after Cytus made by Rayark Inc.
#https://www.rayark.com/g/cytus/mobile/

#112 graphics module
#from:https://www.cs.cmu.edu/~112/notes/cmu_112_graphics.py
from cmu_112_graphics import *
from tkinter import * 
import tkinter as tk

import math
import string
import copy
import os
import random

#documentation from: https://aubio.org/
import aubio
from aubio import source, tempo, onset, notes
#documentation from: https://numpy.org/doc/
from numpy import median, diff
#documentation from: https://realpython.com/intro-to-python-threading/
import sys
#only mixer feature of pygame used: https://www.pygame.org/docs/ref/music.html
import pygame
#seperate file
# https://github.com/aubio/aubio/blob/master/python/demos/demo_tempo.py

#circles representing onsets in audio
class NoteType(object):
    def __init__(self,onset,x,y,r,color):
        self.onset=onset
        self.x=x
        self.y=y
        self.r=r
        self.color=color
        self.accuracy=""
        self.popUpClock=0
        self.drawn=False
        self.shrink=False
        self.popUpClockStart=False
        self.makeTapNote=False
        self.makeHoldNote=False
        self.Fsize=30

    def __repr__(self):
        return str((self.onset,self.x,self.y,self.r,self.color))

class tapNote(NoteType):
    def __init__(self,onset,x,y,r,color):
        super().__init__(onset,x,y,r,color)

#buttons for user options
class Button(object):
    def __init__(self,label,topLeft,botRight,color):
        self.label=label
        self.color=color
        self.topLeft=topLeft
        self.botRight=botRight
        self.outline=None

class GameMode(Mode):
    def appStarted(mode):
        
        if(mode.app.pickedSong=='chemicalStar.wav'):
            #img from https://i.ytimg.com/vi/sRuFHOFa0_c/maxresdefault.jpg
            bkg='chemStar.jpg'
        elif(mode.app.pickedSong=='lastIllusion.wav'):
            #https://vignette.wikia.nocookie.net/cytus/images/b/b7/7-2.png/
            # revision/latest?cb=20140326041247
            bkg='lastIllu.png'
        elif(mode.app.pickedSong=='retrospective.wav'):
            #https://vignette.wikia.nocookie.net/cytus/images/b/ba/1-6.png/
            # revision/latest?cb=20140324054128
            bkg='retro.png'
        else:
            #https://i.ytimg.com/vi/ySchCX95oCk/maxresdefault.jpg
            bkg='saika.jpg'

        background=mode.loadImage(bkg)
        mode.background=mode.scaleImage(background, 1)
        #top of bar y coord
        mode.barY=0
        mode.barThk = 10
        #vary speed of sweep bar based on mode
        if(mode.app.chosenMode=='Keyboard'):
            mode.dy=8
        elif(mode.app.chosenMode=='MouseClick'):
            mode.dy=4

        mode.offset=0
        mode.margin=100
        mode.offsetY=150
        mode.offsetX=100

        x,y=6,8
        mode.blockHeight=mode.height//x
        mode.blockWidth=mode.width//y
        mode.numXBlocks=mode.width//mode.blockWidth
        mode.numYBlocks=mode.height//mode.blockHeight

        mode.comboFont=30
        mode.comboShow=False
        mode.comboClock=0
        mode.comboCount=0
        
        mode.beatClock=0
        mode.countDown=31
        mode.cdSize=55

        #from: https://www.pygame.org/docs/ref/music.html
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.music.load(mode.app.fileName)

        mode.tapNotes=[]
        mode.holdNotes=[]
        mode.clock=0
        
        mode.paused=False
        mode.xBlock=0 
        mode.dx=1
        mode.showBeat=False
        
        mode.onsets = mode.getOnsets(str(mode.app.fileName))
        mode.app.numOnsets=len(mode.onsets)
        mode.onsetsCopy=[]
        for onset in mode.onsets:  
            rate=48000
            mode.onsetsCopy.append(onset//rate)

    
    def redrawAll(mode,canvas):
        canvas.create_image(mode.width/2,mode.height/2, \
            image=ImageTk.PhotoImage(mode.background))

        #draw 3 sec countdown before game starts
        if(mode.cdSize>0):
            cDown=''
            if(mode.countDown%10==0 and mode.countDown>0):
                cDown=mode.countDown//10
                mode.cdSize=50
            canvas.create_text(mode.width/2,mode.height/2,text=str(cDown),
                font=f'Arial {int(mode.cdSize)}',fill='red')
            mode.cdSize-=1

        canvas.create_text(200,20,text='Press p to pause, q to manual quit', \
            font='Helvetica 14',fill='black',anchor='c')

        #show progress through the song
        percent = round(mode.app.progress/mode.app.numOnsets*100, 2)
        canvas.create_text(700,20,text=f'Progress:{percent}', \
            font='Helvetica 14',fill='black',anchor='c')

        for holdNote in mode.holdNotes:
            canvas.create_oval(holdNote.x-holdNote.r,holdNote.y-holdNote.r,
                    holdNote.x+holdNote.r,holdNote.y+holdNote.r,fill=holdNote.color,outline=holdNote.color)
            canvas.create_rectangle(holdNote.x-holdNote.r,holdNote.y,holdNote.x+holdNote.r,
                holdNote.y+holdNote.holdL,fill=holdNote.color,outline=holdNote.color)
        
        if(mode.countDown<=0):
            #draw tapNotes
            for tapNotes in mode.tapNotes:
                #make note shrink as bar leaves it 
                if(mode.barLeavingNote(tapNotes)==True ):
                    if(tapNotes.r>1 and tapNotes.shrink==True):
                        tapNotes.r-=3
                        canvas.create_oval(tapNotes.x-tapNotes.r,tapNotes.y-tapNotes.r,
                            tapNotes.x+tapNotes.r,tapNotes.y+tapNotes.r,fill=tapNotes.color)
                else:
                    canvas.create_oval(tapNotes.x-tapNotes.r,tapNotes.y-tapNotes.r,
                        tapNotes.x+tapNotes.r,tapNotes.y+tapNotes.r,fill=tapNotes.color)
                    tapNotes.drawn=True

                #draw accuracy word
                if(tapNotes.popUpClock<500):
                    if(tapNotes.Fsize>0):
                        #make words shrink 

                        #make words white for retrospective background
                        if(mode.app.pickedSong=='retrospective.wav'):
                            canvas.create_text(tapNotes.x,tapNotes.y,text=tapNotes.accuracy,anchor='c',
                                    font=f'Arial {tapNotes.Fsize}',fill='white')
                        else:
                            canvas.create_text(tapNotes.x,tapNotes.y,text=tapNotes.accuracy,anchor='c',
                                    font=f'Arial {tapNotes.Fsize}',fill='black')
                        tapNotes.Fsize-=1
                else:
                    tapNotes.popUpClockStart=False
                
                #combo word pop up every 10 increase in combo
                if(mode.comboCount%10==0 and mode.comboCount>0 and \
                    mode.comboClock<500):
                    canvas.create_text(mode.width/2,mode.height/2, \
                    text=f'COMBO: {mode.comboCount}', \
                    font=f'Arial {mode.comboFont}',fill='red')
                
                
            #sweep bar
            canvas.create_rectangle(mode.margin-10,mode.barY,mode.width-mode.margin+10,mode.barY+mode.barThk,
                fill='black',outline='gold')
    #from: tempo module 
    # https://github.com/aubio/aubio/blob/master/python/demos/demo_tempo.py
    #documentation from: https://aubio.org/

    def getTempo(mode,filename):
        win_s = 512                 # fft size
        hop_s = win_s // 2          # hop size

        samplerate = 48000

        s = source(filename, samplerate, hop_s)
        samplerate = s.samplerate
        o = tempo("default", win_s, hop_s, samplerate)

        # tempo detection delay, in samples
        # default to 4 blocks delay to catch up with
        delay = 4. * hop_s

        # list of beats, in samples
        beats = []

        # total number of frames read
        total_frames = 0
        while True:
            samples, read = s()
            is_beat = o(samples)
            if is_beat:
                this_beat = int(total_frames - delay + is_beat[0] * hop_s)
                #print("%f" % (this_beat / float(samplerate)))
                beats.append(this_beat)
            total_frames += read
            if read < hop_s: break

        return(beats, total_frames, len(beats))

    #modified from: https://github.com/aubio/aubio/blob/master/python/demos/
    # demo_onset.py
    def getOnsets(mode,filename):
        win_s = 512                 # fft size
        hop_s = win_s // 2          # hop size

        #samplerate = sampRate
        #if len( sys.argv ) > 2: samplerate = int(sys.argv[2])
        samplerate=48000
        s = aubio.source(filename, samplerate, hop_s)
        samplerate = s.samplerate
        o = aubio.onset("default", win_s, hop_s, samplerate)

        # list of onsets, in samples
        onsets = []

        # total number of frames read
        total_frames = 0
        while True:
            
            samples, read = s()
            if o(samples):
                onsets.append(o.get_last())
            total_frames += read
            if read < hop_s: break
        return (onsets)
    

    #returns block number 
    def getBlockNum(mode,coord,size):
        return coord//size

    #from https://www.cs.cmu.edu/~112/notes/notes-variables-and-functions.
    # html#ModuleFunctions
    def almostEqual(mode,x, y):
        return abs(x - y) < 10**-9

    #returns true if 2 notes passed in are within a certain distrance 
    # from each other
    def beatsIntersect(n1,n2):
        buffer = 100
        return ((n1.x-n2.x)**2+(n1.y-n2.y)**2)**.5 < n1.r+n2.r+buffer

    #fills up list of tapNotes depending on list of onsets
    def addNotes(mode):
        noteX=0
        noteY=0
        noteR=20

        #place down notes semi-randomly, random inside assigned block so more spread out
        #blocks to put note in: x block alternates 0->7 then backwards,
        #y block is always 1 more than the block the bar is in 
        for onset in mode.onsets:  
            onset//=48
            if(mode.app.chosenMode=='MouseClick'):
                offset=900
            elif(mode.app.chosenMode=='Keyboard'):
                offset=900
            if(onset%offset == mode.clock):  
                #min/maxY set based on being 1 block ahead/beind block bar is in

                barBlock=mode.getBlockNum(mode.barY,mode.blockHeight)

                #bar is moving down canvas
                if(mode.dy>0):
                    #sweep bar is reaching bottom of canvas
                    if(barBlock>=mode.numYBlocks-2):
                        minY=(barBlock-1)*mode.blockHeight
                        maxY=(barBlock+1)*mode.blockHeight
                    else:
                        minY=(barBlock+1)*mode.blockHeight
                        maxY=(barBlock+2)*mode.blockHeight

                #if bar is moving up
                else:
                    #sweep bar is reaching top of canvas
                    if(barBlock<=1):
                        minY=(barBlock+1)*mode.blockHeight
                        maxY=(barBlock+2)*mode.blockHeight
                    else:
                        minY=(barBlock-1)*mode.blockHeight
                        maxY=barBlock*mode.blockHeight

                mode.xBlock+=mode.dx      
                if(mode.xBlock+2>=mode.numXBlocks):
                    mode.dx=-1
                    
                elif(mode.xBlock==1):
                    mode.dx=1
                    
                if(mode.dx==-1):
                    minX=(mode.xBlock-1)*mode.blockWidth
                    maxX=mode.xBlock*mode.blockWidth

                elif(mode.dx==1):
                    minX=(mode.xBlock+1)*mode.blockWidth
                    maxX=(mode.xBlock+2)*mode.blockWidth

                #while(mode.beatsIntersect(tapNote(onset,noteX,noteY,noteR,'blue'), ))
                #blocks determines a smaller range that the note can be set,
                # a random number is chosen within that range
                noteY=random.randint(minY,maxY)   

                noteX=random.randint(minX,maxX)
                for note in mode.tapNotes:
                    #keep generating random X until find one not on same line 
                    # as others
                    while(mode.onSameY(noteY,note.y)):
                        noteY=random.randint(minY,maxY)   
                
                mode.tapNotes.append(tapNote(onset,noteX,noteY,noteR,'blue'))

    #return true is 2 Y values are close to each other
    def onSameY(mode,y1,y2):
        return abs(y1-y2)<5

    #returns true if bar is leaving a note 
    def barLeavingNote(mode,note):
        #bar is moving up
        if(mode.dy<0):
            return note.y-note.r > mode.barY-mode.barThk
        #bar is moving down
        else:
            return note.y+note.r < mode.barY+mode.barThk

    def checkGameOver(mode):
        #check game over if song is still playing, then game is not over yet
        if(pygame.mixer.music.get_busy()):
            return False
        return True

    
    def timerFired(mode):
        mode.countDown-=1
        if(mode.countDown==0):
            #start music when countdown is over
            pygame.mixer.music.play()

        if(mode.countDown<=0):
            mode.clock+=1
            mode.beatClock+=.1
            
            mode.addNotes()
            mode.moveBar()

            if(mode.checkGameOver()):
                mode.app.setActiveMode(mode.app.resultsScreenMode)
            
            #show combo pop up for every multiple of 10
            mode.comboClock+=1
            if(mode.comboCount%10==0):          
                mode.comboClock=0


            for note in mode.tapNotes:
                #for animating shrinking circles
                if(note.drawn==True):
                    note.shrink=True
                #timer for how long accuracy words stay on screen
                if(note.popUpClockStart==True):
                    note.popUpClock+=1
                #accuracy of note is missed if bar leaves note
                if(mode.barLeavingNote(note) and note.drawn==True and note.accuracy==''):
                    note.accuracy='Missed'
                    #reset combocount to zero when a note is missed
                    mode.comboCount=0
                    mode.app.missed+=1
                    mode.app.progress+=1
            
            if(mode.beatClock in mode.onsetsCopy): 
                mode.showBeat=True
      

    #moves bar up and down the screen
    def moveBar(mode):
        mode.barY+=mode.dy
        if(mode.barY+mode.barThk>mode.height):
            mode.barY=mode.height-mode.barThk
            mode.dy*=-1    
        
        #switch direction of bar if it hits either top or bottom
        elif(mode.barY<0):
            mode.barY=0
            mode.dy*=-1 
        
    #returns true if bar is intersecting note
    def intersect(mode,note):
        if(mode.dy>0):
            return note.y-note.r <= mode.barY +mode.barThk
        else:
            return note.y+note.r >= mode.barY
        
    #pausing game
    def keyPressed(mode,event):
        if(event.key=='p'):
            pygame.mixer.music.pause()
            mode.app.setActiveMode(mode.app.pauseMode)
        if(event.key=='q'):
            #manual quit--> goes to results screen w current score/progress
            mode.app.setActiveMode(mode.app.resultsScreenMode)

    
    #calculates the accuracy and returns an accuracy word for a note
    def accuracyJudger(mode,note):

        #part of the bar is inside note
        if((mode.barY<note.y-note.r and mode.barY+mode.barThk<note.y+note.r) or
            (mode.barY>note.y-note.r and mode.barY+mode.barThk>note.y+note.r)):
            mode.app.goods+=1
            return ('Good')

        #thickness of bar is completely inside note
        elif((mode.barY>note.y-note.r and mode.barY+mode.barThk<note.y+note.r)):
            mode.app.greats+=1
            return ('Great')

        #middle of bar is exactly at middle of note
        elif(mode.barY+mode.barThk//2 == note.y):
            mode.app.perfects+=1
            return ('Perfect!')

           
#keyboard mode is a game mode where user taps space bar to clear notes
class KeyBoardMode(GameMode):
    def appStarted(mode):
        mode.currPressed=None
        super().appStarted()
        
    def keyPressed(mode,event):
        #call super so pressing p pauses game
        super().keyPressed(event)
        if(event.key=='Space'):
            mode.currPressed='Space'

            for note in mode.tapNotes:
                #if bar is intersecting current note
                if(mode.intersect(note) and note.drawn):
                    if(mode.currPressed=='Space'):
                        note.accuracy=mode.accuracyJudger(note)
                        if(note.accuracy == 'Perfect!' or \
                            note.accuracy == 'Great' or \
                            note.accuracy == 'Good'):
                            mode.comboCount+=1
                            mode.app.progress+=1
                    
                    note.popUpClockStart=True 

    def keyReleased(mode,event):
        if(event.key=='Space'):
            mode.currPressed=None         

class MouseClickMode(GameMode):
    def appStarted(mode):
        super().appStarted()
        mode.clickLoc=(-1,-1)
        mode.pressed=False
        
    #return true if mouse is in bounds of note
    def inNote(mode,mouseCoord,note):
        return note.x-note.r<=mouseCoord[0]<=note.x+note.r and \
            note.y-note.r<=mouseCoord[1]<=note.y+note.r

    #return the note that the mouseCoordinate is on
    def getNote(mode,mouseCoord):
        for note in mode.tapNotes:
            if(mode.inNote(mouseCoord,note)):
                return note

    def mouseReleased(mode,event):
        mode.pressed=False

    def mousePressed(mode,event):
        mode.pressed=True         
        mode.clickLoc=(event.x,event.y)
        note=mode.getNote((event.x,event.y))
        
        for note in mode.tapNotes:
            #if bar is intersecting current note
            if(mode.intersect(note) and note.drawn):
                #check if player clicked on a note
                if(note != None):
                    note.accuracy=mode.accuracyJudger(note)
                    if(note.accuracy == 'Perfect!' or \
                        note.accuracy == 'Great' or \
                        note.accuracy == 'Good'):
                        mode.comboCount+=1
                        mode.app.progress+=1

                note.popUpClockStart=True 

class ModeSelectionMode(Mode):
    def appStarted(mode):
        super().appStarted()
        #image from 
        # https://www.game-accessibility.com/wp/wp-content/uploads/2016/04/dsds.png
        background=mode.loadImage('modeSelectBkg.png')
        mode.background=mode.scaleImage(background, .85)

        #buttons for modes
        mode.buttons=set()
        x,y,y2=80,150,50
        mode.kbModeButton = Button("Keyboard Mode",(mode.width/4-x,mode.height/2+y),
            (mode.width/4+x,mode.height*3/4+y2),'blue')
        mode.buttons.add(mode.kbModeButton)
        mode.mouseModeButton = Button("Mouse Click Mode",(mode.width*3/4-x, 
            mode.height/2+y),(mode.width*3/4+x,mode.height*3/4+y2),'blue')
        mode.buttons.add(mode.mouseModeButton)
        mode.app.chosenMode=None

    def redrawAll(mode,canvas):
        #from:https://www.game-accessibility.com/wp/wp-content/uploads/2016/04/dsds.png
        canvas.create_image(mode.width/2,mode.height/2,
            image=ImageTk.PhotoImage(mode.background))
        canvas.create_text(mode.width/2,mode.height/2+150,text='Choose a mode:',
            font='Arial 16',fill='black')
        for button in mode.buttons:
            buttonWidth=button.botRight[0]-button.topLeft[0]
            buttonHeight=button.botRight[1]-button.topLeft[1]
            if(button.outline != None):
                #make button glow when mouse is over it
                canvas.create_rectangle(button.topLeft[0],button.topLeft[1],
                button.botRight[0],button.botRight[1],fill=button.color,
                outline=button.outline,width=4)
            else:
                canvas.create_rectangle(button.topLeft[0],button.topLeft[1],
                    button.botRight[0],button.botRight[1],fill=button.color)
            #label
            canvas.create_text(button.topLeft[0]+buttonWidth/2,
                button.topLeft[1]+buttonHeight/2,text=button.label,anchor='c',
                font='Takoma 16',width=buttonWidth)

        #descriptions for each mode
        off=27
        canvas.create_rectangle(0,button.botRight[1]+off,mode.width,mode.height,
            fill='white')
        if(mode.app.chosenMode=='Keyboard'):
            canvas.create_text(mode.width/2,button.botRight[1]+off*2,anchor='c',
                text='Keyboard Mode:\
            \nPress space bar to clear notes when sweep bar passes over.',
                font='Takoma 16',fill='blue')
        elif(mode.app.chosenMode=='MouseClick'):
            canvas.create_text(mode.width/2,button.botRight[1]+off*2,anchor='c',
                text='Mouse Click Mode:\
            \nUse mouse to click on notes to clear when sweep bar passes over.',
                font='Takoma 16',fill='blue')
    


    #draw outline around box when moused over
    def mouseMoved(mode,event):
        for button in mode.buttons:
            if(not button.label == None):
                if(mode.app.inBounds((event.x,event.y),button.topLeft,
                    button.botRight)):
                    button.outline='gold'
                    if(button.label=='Keyboard Mode'):
                        mode.app.chosenMode='Keyboard'
                    elif(button.label=='Mouse Click Mode'):
                        mode.app.chosenMode='MouseClick'
                    else:
                        mode.app.chosenMode=''
                else:
                    button.outline=None
                    
                

    def mousePressed(mode,event):
        #check which button user clicked, switch to mode of gameplay accordingly
        for button in mode.buttons:
            if(not button.label == None):
                if(mode.app.inBounds((event.x,event.y),button.topLeft,
                    button.botRight)):
                    pygame.mixer.music.stop()
                    if(button.label=='Keyboard Mode'):
                        mode.app.setActiveMode(mode.app.keyboardMode)

                    elif(button.label=='Mouse Click Mode'):
                        mode.app.setActiveMode(mode.app.mouseClickMode)
                    
   

#first screen that pops up, includes menu of modes/ difficulties
class WelcomeMode(Mode):
    def appStarted(mode):
        pygame.init()
        pygame.mixer.init()
        #audio from: https://www.youtube.com/watch?v=Ul8eDFEeGhc
        pygame.mixer.music.load('opening.wav')
        pygame.mixer.music.play()
        #from: https://www.androidpolice.com/2018/03/08/cytus-ii-30-off-first-week/
        url='https://www.androidpolice.com/wp-content/uploads/2018/03/nexus'+\
        '2cee_Screenshot-26.png'
        mode.bkgnd = mode.loadImage(url)
        scale=24/25
        mode.background = mode.scaleImage(mode.bkgnd, scale)
        #made using Microsoft Word
        mode.pressKey = mode.loadImage('anyKey.PNG')
        mode.selectedMode=None
        mode.stip=''
        mode.clock=-1

    def redrawAll(mode,canvas):
        canvas.create_rectangle(0,0,mode.width,mode.height,fill='black')
        canvas.create_image(mode.width/2, mode.height/2, 
            image=ImageTk.PhotoImage(mode.background))
        canvas.create_image(mode.width/2,mode.height*3/4,
            image=ImageTk.PhotoImage(mode.pressKey))
        canvas.create_rectangle(mode.width/2-511//2,mode.height*3/4-47//2, \
            mode.width/2+511//2,mode.height*3/4+47//2,fill='black',
                stipple=mode.stip)

    #press any key to proceed to song pick screen
    def keyPressed(mode,event):
        
        mode.app.setActiveMode(mode.app.songPickMode)
    
    #stipple values from:
    #http://www.kosbie.net/cmu/fall-11/15-112/handouts/misc-demos/src/semi-
    # transparent-stipple-demo.py
    def timerFired(mode):
        mode.clock+=1
        if(mode.clock==0):
            mode.stip=''
        elif(mode.clock==1):
            mode.stip='gray75'
        elif(mode.clock==2):
            mode.stip='gray50'
        elif(mode.clock==3):
            mode.stip='gray25'
        elif(mode.clock==4):
            mode.stip='gray12'
            mode.clock=-1

class songPickMode(GameMode):
    def appStarted(mode):
        
        mode.select = mode.loadImage('selectASong.png')
        mode.files=['chemicalStar.wav','lastIllusion.wav','retrospective.wav',
            'saika.wav']
        mode.clock=0
        mode.stip=''
        #dictionary with value as filename and key as button object
        mode.songs=dict()
        mode.buttonS=150
        mode.chemButton=Button('Chemical Star',(mode.width/2-mode.buttonS,
            mode.height/2-180),\
        (mode.width/2+mode.buttonS,mode.height/2-100),'green')
        mode.lastButton=Button('Last Illusion',(mode.width/2-mode.buttonS,
            mode.height/2-80),
        (mode.width/2+mode.buttonS,mode.height/2),'green')
        mode.retroButton=Button('Retrospective',(mode.width/2-mode.buttonS,
            mode.height/2+20),
        (mode.width/2+mode.buttonS,mode.height/2+100),'green')
        mode.saikaButton=Button('Saika',(mode.width/2-mode.buttonS,
            mode.height/2+120),
        (mode.width/2+mode.buttonS,mode.height/2+200),'green')
        mode.songs[mode.chemButton]=mode.files[0]
        mode.songs[mode.lastButton]=mode.files[1]
        mode.songs[mode.retroButton]=mode.files[2]
        mode.songs[mode.saikaButton]=mode.files[3]

        #filename is key, beats in song is value
        mode.beatsInSongs=dict()
        for song in mode.songs:
            # https://github.com/aubio/aubio/blob/master/python/demos/demo_tempo.py
            beats,totalFrames,lenBeats=mode.getTempo(mode.songs[song])
            mode.beatsInSongs[mode.songs[song]]=lenBeats

        allBeats=[]
        for beats in mode.beatsInSongs:
            allBeats.append(beats)
        #sort songs in order by number of beats found in song
        allBeats.sort()
        mode.difficulty=dict()
        mode.difficulty[allBeats[0]]='Level 1'
        mode.difficulty[allBeats[1]]='Level 2'
        mode.difficulty[allBeats[2]]='Level 3'
        mode.difficulty[allBeats[3]]='Level 4'


    def mouseMoved(mode,event):
        for song in mode.songs:
            if(not song.label == None):
                if(mode.app.inBounds((event.x,event.y),song.topLeft,
                    song.botRight)):
                    song.outline='gold'
                else:
                    song.outline=None

    def mousePressed(mode,event):
        for song in mode.songs:
            if(not song.label == None):
                if(mode.app.inBounds((event.x,event.y),song.topLeft,
                    song.botRight)):
                    mode.app.pickedSong=mode.songs[song]
                    mode.app.fileName=mode.songs[song]
                    mode.app.setActiveMode(mode.app.ModeSelectionMode)
        
    def timerFired(mode):
    #stipple values from:
    #http://www.kosbie.net/cmu/fall-11/15-112/handouts/misc-demos/src/semi-
    # transparent-stipple-demo.py
        mode.clock+=1
        if(mode.clock==0):
            mode.stip=''
        elif(mode.clock==1):
            mode.stip='gray75'
        elif(mode.clock==2):
            mode.stip='gray50'
        elif(mode.clock==3):
            mode.stip='gray25'
        elif(mode.clock==4):
            mode.stip='gray12'
            mode.clock=-1

    def redrawAll(mode,canvas):
        canvas.create_rectangle(0,0,mode.width,mode.height,fill='black')
        canvas.create_image(mode.width/2,mode.height/8,
            image=ImageTk.PhotoImage(mode.select))
        r,s=150,40
        canvas.create_rectangle(0,0,mode.width,mode.height/8+50,fill='black',
            stipple=mode.stip)
        
        for song in mode.songs:
            if(song.outline == None):
                canvas.create_rectangle(song.topLeft[0],song.topLeft[1],
                    song.botRight[0],song.botRight[1],fill=song.color)
            else:
                canvas.create_rectangle(song.topLeft[0],song.topLeft[1],
                    song.botRight[0],song.botRight[1],fill=song.color,
                        outline=song.outline,width=4)
            canvas.create_text(song.topLeft[0]+r,song.topLeft[1]+s,
                text=song.label,font='Arial 20')
            canvas.create_text(song.topLeft[0]+r,song.topLeft[1]+s+20,
                text=mode.difficulty[mode.songs[song]],font='Arial 12')

class ResultsScreenMode(GameMode):
    def appStarted(mode):
        super().appStarted()
        #image from: http://the-app-shack.com/wp-content/uploads/2012/08/
        # Cytus-New-02.jpg
        mode.bkg=mode.loadImage('results.jpg')
        pygame.mixer.music.stop()
        mode.score=(mode.app.perfects+mode.app.greats+mode.app.goods)/mode.app.numOnsets

        mode.restart=Button('Restart',(mode.width/8-50,mode.height/6-50),
            (mode.width/8+50,mode.height/8+50),'black')
    
    #restart game
    def mousePressed(mode,event):
        if(mode.app.inBounds((event.x,event.y),mode.restart.topLeft,
            mode.restart.botRight)):
            mode.app.appStarted()
            
    def redrawAll(mode,canvas):
        canvas.create_image(mode.width/2,mode.height/2,
            image=ImageTk.PhotoImage(mode.bkg))
        canvas.create_text(mode.width/2,mode.height/10,
            text='Results:',font='Helvetica 30 bold italic',fill='white')
        canvas.create_text(mode.width/2,mode.height/6,
            text=f'{round(mode.score*100,2)}',font='Helvetica 30 bold italic',
                fill='white')
        
        #restart button
        canvas.create_rectangle(mode.restart.topLeft[0],mode.restart.topLeft[1],
                mode.restart.botRight[0],mode.restart.botRight[1],width=4)
        canvas.create_text(mode.restart.topLeft[0]+50,mode.restart.topLeft[1]+50,
            text=mode.restart.label,font='Helvetica 16',fill='white')  

        r=80
        x=mode.width/5
        y=mode.height*3/4
        canvas.create_oval(x-r,y-r,x+r,y+r,width=5)
        canvas.create_text(x,y,text=f'Perfects:{mode.app.perfects}',
            font='Helvetica 16',fill='white')
        canvas.create_oval(x*2-r,y-r,x*2+r,y+r,width=5)
        canvas.create_text(x*2,y,text=f'Greats:{mode.app.greats}',
            font='Helvetica 16',fill='white')
        canvas.create_oval(x*3-r,y-r,x*3+r,y+r,width=5)
        canvas.create_text(x*3,y,text=f'Goods:{mode.app.goods}',
            font='Helvetica 16',fill='white')
        canvas.create_oval(x*4-r,y-r,x*4+r,y+r,width=5)
        canvas.create_text(x*4,y,text=f'Misses:{mode.app.missed}',
            font='Helvetica 16',fill='white')


class PauseMode(Mode):
    def appStarted(mode):
        #image from https://www.pinterest.com/pin/449304500302387606/?lp=true
        mode.bkg=mode.loadImage('pauseBkg.jpg')
        #made in Microsoft word
        mode.text=mode.loadImage('pauseText.png')
    def redrawAll(mode,canvas):
        canvas.create_rectangle(0,0,mode.width,mode.height,fill='black')
        canvas.create_image(mode.width/2,mode.height/2, \
            image=ImageTk.PhotoImage(mode.bkg))
        canvas.create_image(mode.width/2,mode.height-50, \
            image=ImageTk.PhotoImage(mode.text))

    def keyPressed(mode,event):
        print(mode.app.chosenMode)
        if(event.key=='p'):
            pygame.mixer.music.unpause()
            #PlaySound(mode.app.fileName,SND_FILENAME)
            if( mode.app.chosenMode=='Keyboard'):
                mode.app.setActiveMode(mode.app.keyboardMode)
            elif( mode.app.chosenMode=='MouseClick'):
                mode.app.setActiveMode(mode.app.mouseClickMode)


class modalApp(ModalApp):
    
    def appStarted(app):
        #variables needed in multiple modes
        app.fileName=''
        app.chosenMode=''
        app.progress=0
        app.perfects=0
        app.greats=0
        app.goods=0
        app.missed=0
        app.pickedSong=''
        app.numOnsets=0

        app.welcomeMode=WelcomeMode()
        app.ModeSelectionMode=ModeSelectionMode()
        app.songPickMode=songPickMode()
        app.keyboardMode=KeyBoardMode()

        app.mouseClickMode=MouseClickMode()
        app.pauseMode=PauseMode()
        app.resultsScreenMode=ResultsScreenMode()

        app.setActiveMode(app.welcomeMode)

    #check if mouse click is in bounds of button
    def inBounds(mode,mouseCoord,topL,botR):
        return topL[0]<=mouseCoord[0]<=botR[0] and \
            topL[1]<=mouseCoord[1]<=botR[1]

    def appStopped(app):
        pygame.mixer.music.stop()

    
app=modalApp(width=800, height=600)

