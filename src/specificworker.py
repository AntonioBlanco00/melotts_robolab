#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2021 by YOUR NAME HERE
#
#    This file is part of RoboComp
#
#    RoboComp is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RoboComp is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RoboComp.  If not, see <http://www.gnu.org/licenses/>.
#

import subprocess
import sys

try:
	from Queue import Queue
except ImportError:
	from queue import Queue

from PySide2.QtCore import QTimer
from PySide2.QtWidgets import QApplication
from genericworker import *
import time

# Nuevos imports
from melo.api import TTS
from pydub import AudioSegment
from pydub.playback import play
import threading
import os
import random

max_queue = 100
charsToAvoid = ["'", '"', '{', '}', '[', '<', '>', '(', ')', '&', '$', '|', '#']

# If RoboComp was compiled with Python bindings you can use InnerModel in Python
sys.path.append('/opt/robocomp/lib')
# import librobocomp_qmat
# import librobocomp_osgviewer
# import librobocomp_innermodel

class SpecificWorker(GenericWorker):
    def __init__(self, proxy_map, startup_check=False):
        super(SpecificWorker, self).__init__(proxy_map)
        self.Period = 2000
        self.audioenviado = False
        self.text_queue = Queue(max_queue)
        
        self.device = 'cuda:0' # Usando la gráfica
        self.model = TTS(language='ES', device=self.device)
        self.speaker_ids = self.model.hps.data.spk2id
        self.speed = 1.0
       
        #device = 'cpu'  # Este si se ejecuta en raspberry (EBO)
        
        if startup_check:
            self.startup_check()
        else:
            self.timer.timeout.connect(self.compute)
            self.timer.start(self.Period)

    def __del__(self):
        print('SpecificWorker destructor')

    def setParams(self, params):
        if "tts" in params:
            self._tts = params["tts"]
        else:
            self._tts = "festival"
        # try:
        #	self.innermodel = InnerModel(params["InnerModelPath"])
        # except:
        #	traceback.print_exc()
        #	print "Error reading config params"
        return True


    @QtCore.Slot()
    def compute(self):
        if self.text_queue.empty():
            #print("Cola vacía")
            pass
        else:
            text_to_say = self.text_queue.get()
            if text_to_say == "m":
                text_to_say = self.random_tag()
                
            elif text_to_say == "f":
                self.emotionalmotor_proxy.expressJoy()
                text_to_say = ""
            elif text_to_say == "s":
                
                self.emotionalmotor_proxy.expressSurprise()
                text_to_say = ""
            elif text_to_say == "t":
                
                self.emotionalmotor_proxy.expressSadness()
                text_to_say = ""
                
            else: 
                for rep in charsToAvoid:
                    text_to_say = text_to_say.replace(rep, '\\' + rep)
              
            self.new_tts(text_to_say)

    def Speech_say(self, text, owerwrite):
        if owerwrite:
            self.text_queue = Queue(max_queue)
        self.text_queue.put(text)
        return True


        # Función que selecciona una muletilla al azar para hacer tiempo en la terapia
    def random_tag(self):
        opciones = [
        "¡Entendido! Déjame pensar un momento a ver como continuaría la historia",
        "Buena elección, veamos cómo seguimos la historia.",
        "¡Claro, vamos a ver cómo continuamos! Déjame pensar un momento sobre la historia.",
        "Entiendo perfectamente tu decisión, déjame echarle un vistazo rápido a ver qué se me ocurre para seguir.",
        "¡Por supuesto! Déjame pensar un poco a ver como podría continuar la aventura",
        "¡Que elección más interesante! Continuemos",
        "¡Excelente elección, me encanta!",
        "¡Me alegra mucho que hayas decidido eso!"
        ]

        return random.choice(opciones)
    
    # Función que contiene y ejecuta todo lo necesario para generar el audio TTS a partir del texto y reproducirlo. Con la nueva voz del TTS.
    def new_tts(self, text):
        # Función para dividir el texto en partes más pequeñas
        def split_text(text):
            parts = []
            start = 0
            end = 0
            while end < len(text):
                # Encontrar el final de la parte basado en las reglas especificadas
                if len(parts) == 0 or len(parts) == 1:
                    # Para la primera y segunda parte, encontrar el primer punto después de 75 caracteres
                    end = min(start + 75, len(text))
                    while end < len(text) and text[end] not in [".", "!", "?"]:
                        end += 1
                else:
                    # Para las siguientes partes, encontrar "." "!" o "?" después de 150 caracteres
                    end = min(start + 150, len(text))
                    while end < len(text) and text[end] not in [".", "!", "?"]:
                        end += 1

                # Agregar la parte al resultado
                parts.append(text[start:end + 1].strip())

                # Mover el inicio al siguiente punto de división
                start = end + 1 if end < len(text) else len(text)

            return parts

        # Función para generar audio y agregar las rutas de salida a la cola
        def generate_audio(queue):
            for i, part in enumerate(text_parts):
                output_path = output_paths[i]
                self.model.tts_to_file(part, self.speaker_ids['ES'], output_path, speed=self.speed)
                queue.put(output_path)
            # Marcar el final de la cola
            queue.put(None)

        # Función para reproducir el audio en orden
        def play_audio(queue):
            while True:
                output_path = queue.get()
                if output_path is None:
                    break
                audio = AudioSegment.from_file(output_path)
                self.emotionalmotor_proxy.talking(True)
                play(audio)
                self.emotionalmotor_proxy.talking(False)
                queue.task_done()
                semaphore.release()

        # Obtener las partes del texto
        text_parts = split_text(text)

        # Ruta de salida
        output_paths = [f"es_{i}.wav" for i in range(len(text_parts))]
        # Cola para almacenar las rutas de salida de los archivos de audio generados
        output_queue = Queue()
        # Semáforo para sincronizar la generación y reproducción
        semaphore = threading.Semaphore(0)
        # Hilo para generar audio
        generate_thread = threading.Thread(target=generate_audio, args=(output_queue,))
        generate_thread.start()
        # Hilo para reproducir el audio
        play_thread = threading.Thread(target=play_audio, args=(output_queue,))
        play_thread.start()
        # Esperar a que todos los archivos de audio estén listos para reproducirse
        for _ in range(len(text_parts)):
            semaphore.acquire()
        # Esperar a que ambos hilos terminen
        generate_thread.join()
        play_thread.join()
        # Eliminar archivos temporales
        for output_path in output_paths:
            os.remove(output_path)


    ######################
    # From the RoboCompEmotionalMotor you can call this methods:
    # self.emotionalmotor_proxy.expressAnger(...)
    # self.emotionalmotor_proxy.expressDisgust(...)
    # self.emotionalmotor_proxy.expressFear(...)
    # self.emotionalmotor_proxy.expressJoy(...)
    # self.emotionalmotor_proxy.expressSadness(...)
    # self.emotionalmotor_proxy.expressSurprise(...) 
    # self.emotionalmotor_proxy.isanybodythere(...)
    # self.emotionalmotor_proxy.listening(...)
    # self.emotionalmotor_proxy.pupposition(...)
    # self.emotionalmotor_proxy.talking(...)