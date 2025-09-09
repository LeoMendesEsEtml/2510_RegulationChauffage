# -*- coding: utf-8 -*-
"""
Ordonnanceur de tâches périodiques pour le système de régulation.

Fonctionnalités:
- Exécution de tâches à intervalles réguliers
- Gestion des priorités
- Surveillance des délais d'exécution
- Robustesse aux erreurs de tâches

Utilisé pour:
- Échantillonnage des capteurs
- Calcul de la régulation
- Mise à jour des sorties
- Surveillance du système
"""

import threading
from typing import Dict, Callable, Optional, Any
from time import time, sleep
import logging
from dataclasses import dataclass
from utils.logging_config import setup_module_logger

@dataclass
class Task:
    """
    Représente une tâche périodique.
    """
    name: str                 # Nom unique de la tâche
    interval: float          # Intervalle en secondes
    callback: Callable       # Fonction à exécuter
    last_run: float = 0.0    # Timestamp dernière exécution
    next_run: float = 0.0    # Timestamp prochaine exécution
    running: bool = False    # État d'exécution
    overruns: int = 0        # Nombre de dépassements

class Scheduler:
    """
    Ordonnanceur de tâches périodiques.
    Exécute les tâches dans un thread dédié.
    """
    
    def __init__(self, name: str = "MainScheduler"):
        """
        Initialise l'ordonnanceur.
        
        Args:
            name: Nom de l'ordonnanceur pour les logs
        """
        self.name = name
        self.tasks: Dict[str, Task] = {}
        self.logger = setup_module_logger(f"scheduler.{name}")
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_task(self, interval_s: float, func: Callable, 
                 name: Optional[str] = None) -> str:
        """
        Ajoute une tâche périodique.
        
        Args:
            interval_s: Intervalle d'exécution en secondes
            func: Fonction à exécuter
            name: Nom optionnel de la tâche
            
        Returns:
            str: Identifiant de la tâche
            
        Raises:
            ValueError: Si l'intervalle est invalide
        """
        if interval_s <= 0:
            raise ValueError("L'intervalle doit être positif")
            
        task_name = name or func.__name__
        if task_name in self.tasks:
            raise ValueError(f"Une tâche '{task_name}' existe déjà")
            
        with self._lock:
            task = Task(
                name=task_name,
                interval=interval_s,
                callback=func,
                last_run=0.0,
                next_run=time() + interval_s
            )
            self.tasks[task_name] = task
            self.logger.info(f"Tâche ajoutée: {task_name} ({interval_s}s)")
            
        return task_name

    def remove_task(self, task_name: str) -> None:
        """
        Supprime une tâche.
        
        Args:
            task_name: Nom de la tâche à supprimer
        """
        with self._lock:
            if task_name in self.tasks:
                self.tasks.pop(task_name)
                self.logger.info(f"Tâche supprimée: {task_name}")

    def get_task_info(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Retourne les informations sur une tâche.
        
        Args:
            task_name: Nom de la tâche
            
        Returns:
            Dict avec les informations ou None
        """
        task = self.tasks.get(task_name)
        if not task:
            return None
            
        return {
            "name": task.name,
            "interval": task.interval,
            "last_run": task.last_run,
            "next_run": task.next_run,
            "running": task.running,
            "overruns": task.overruns
        }

    def run(self) -> None:
        """
        Démarre l'ordonnanceur dans un thread séparé.
        """
        if self._thread and self._thread.is_alive():
            self.logger.warning("L'ordonnanceur est déjà en cours")
            return
            
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"Scheduler-{self.name}"
        )
        self._thread.daemon = True
        self._thread.start()
        self.logger.info("Ordonnanceur démarré")

    def stop(self) -> None:
        """
        Arrête l'ordonnanceur.
        Attend la fin du thread.
        """
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None
        self.logger.info("Ordonnanceur arrêté")

    def _run_loop(self) -> None:
        """
        Boucle principale d'exécution des tâches.
        Vérifie et exécute les tâches dues.
        """
        while not self._stop_event.is_set():
            now = time()
            
            # Copie les tâches pour éviter les modifications pendant l'itération
            with self._lock:
                tasks = list(self.tasks.values())
                
            for task in tasks:
                if task.running:
                    # Détecte les dépassements
                    if now - task.last_run > task.interval * 2:
                        task.overruns += 1
                        self.logger.warning(
                            f"Dépassement détecté: {task.name} "
                            f"(+{now - task.last_run:.1f}s)"
                        )
                    continue
                    
                if now >= task.next_run:
                    try:
                        task.running = True
                        task.callback()
                        task.last_run = now
                        task.next_run = now + task.interval
                        task.running = False
                    except Exception as e:
                        self.logger.error(
                            f"Erreur dans la tâche {task.name}: {str(e)}"
                        )
                        task.running = False
                        
            # Attente optimisée
            next_due = min(
                (t.next_run for t in tasks if not t.running),
                default=now + 0.1
            )
            sleep_time = max(0, min(next_due - now, 0.1))
            sleep(sleep_time)

    def reset_statistics(self) -> None:
        """
        Réinitialise les statistiques des tâches.
        """
        with self._lock:
            for task in self.tasks.values():
                task.overruns = 0
                task.running = False
