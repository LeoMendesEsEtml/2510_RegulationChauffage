"""
Ordonnanceur de tâches périodiques pour la régulation.
Permet d'exécuter des fonctions à intervalles réguliers.
"""
from typing import Callable, Optional, Dict
from time import time, sleep
import logging
from threading import Thread, Event

class Task:
    def __init__(self, interval: float, func: Callable, name: Optional[str] = None):
        self.interval = interval
        self.func = func
        self.name = name or func.__name__
        self.last_run = 0.0
        self.next_run = 0.0
        
class Scheduler:
    def __init__(self):
        """Initialise l'ordonnanceur de tâches."""
        self.tasks: Dict[str, Task] = {}
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self.logger = logging.getLogger('scheduler')

    def add_task(self, interval_s: float, func: Callable, name: Optional[str] = None) -> str:
        """
        Ajoute une tâche périodique.
        
        Args:
            interval_s: Intervalle d'exécution en secondes
            func: Fonction à exécuter
            name: Nom optionnel de la tâche
            
        Returns:
            str: Identifiant de la tâche
            
        Raises:
            ValueError: Si l'intervalle est invalide ou la tâche existe déjà
        """
        if interval_s <= 0:
            raise ValueError("L'intervalle doit être positif")
        
        task_name = name or func.__name__
        if task_name in self.tasks:
            raise ValueError(f"Une tâche nommée '{task_name}' existe déjà")
            
        task = Task(interval_s, func, task_name)
        self.tasks[task_name] = task
        return task_name
        
    def remove_task(self, task_name: str) -> None:
        """
        Supprime une tâche.
        
        Args:
            task_name: Nom de la tâche à supprimer
        """
        if task_name in self.tasks:
            del self.tasks[task_name]
            
    def run(self) -> None:
        """
        Démarre l'ordonnanceur dans un thread séparé.
        Les tâches sont exécutées à leurs intervalles respectifs.
        """
        if self._thread and self._thread.is_alive():
            return
            
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="Scheduler")
        self._thread.daemon = True
        self._thread.start()
        
    def stop(self) -> None:
        """Arrête l'ordonnanceur."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            
    def _run_loop(self) -> None:
        """Boucle principale d'exécution des tâches."""
        while not self._stop_event.is_set():
            now = time()
            
            for task in self.tasks.values():
                if task.last_run == 0.0:
                    task.next_run = now + task.interval
                    task.last_run = now
                elif now >= task.next_run:
                    try:
                        task.func()
                        task.last_run = now
                        task.next_run = now + task.interval
                    except Exception as e:
                        self.logger.error(f"Erreur dans la tâche {task.name}: {str(e)}")
            
            sleep(0.1)  # Évite de surcharger le CPU
