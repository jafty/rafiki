import math

class Action:
    def __init__(self, city, type_, workers=0, resource=None, target_city=None, start_turn=0):
        """
        city : Ville initiatrice de l'action
        type_ : Type d'action ('harvest', 'construction', 'transport', 'raid_city', 'besiege', etc.)
        workers : Nombre d'hommes alloués
        resource : Ressource concernée (si applicable, ex: 'wood', 'food')
        target_city : Ville cible (pour les envois ou attaques)
        start_turn : Tour où l'action doit commencer
        """
        self.city = city
        self.type = type_
        self.workers = workers
        self.resource = resource
        self.target_city = target_city
        self.start_turn = start_turn
        self.remaining_duration = self._initialize_duration()
        self.result = None
        self.has_started = False

    def _initialize_duration(self):
        """
        Définit la durée initiale de l'action en fonction de son type.
        """
        if self.type == "besiege":
            return 10  # Durée fixe pour un siège
        elif self.type in {"raid_city", "transport"}:
            if self.target_city:
                distance = self.city.distance_to(self.target_city)
                return 2 * math.ceil(distance)  # Aller-retour basé sur la distance
        elif self.type == "harvest":
            return float("inf")  # Récolte infinie
        elif self.type == "construction":
            return None  # La durée dépend du progrès
        return 0

    def calculate_initial_food_cost(self):
        """
        Calcule le coût initial en nourriture pour lancer un siège, basé sur la distance et le nombre d'hommes.
        """
        if self.target_city:
            distance = self.city.distance_to(self.target_city)
            cost_per_worker = 0.5  # Chaque homme coûte 0.5 unité de nourriture par unité de distance
            return math.ceil(distance * self.workers * cost_per_worker)
        return 0

    def update(self):
        """
        Met à jour l'état de l'action. Retourne True si l'action est terminée.
        """
        if self.type == "harvest":
            return self._handle_harvest()
        elif self.type == "besiege":
            return self._handle_besiege()
        elif self.type == "raid_city":
            return self._handle_timed_action()
        elif self.type == "transport":
            return self._handle_timed_action()
        elif self.type == "construction":
            return self._handle_construction()
        return False

    def _handle_harvest(self):
        """
        Récolte une ressource infinie dans la ville. La production dépend du nombre d'hommes alloués.
        """
        if self.resource in self.city.yields:
            yield_per_worker = self.city.yields[self.resource]
            production = self.workers * yield_per_worker
            self.city.resources[self.resource] += production
            print(f"{self.workers} travailleurs dans {self.city.name} ont produit {production} unités de {self.resource}.")
        else:
            print(f"La ressource {self.resource} n'est pas disponible à {self.city.name}.")
        return False  # Harvest est une action continue


    def _handle_construction(self):
        """
        Gère le progrès des constructions en fonction des hommes alloués.
        """
        building = self.city.buildings.get(self.resource)
        if building:
            progress = self.workers
            building["progress"] += progress
            remaining_work = building["required_work"] - building["progress"]

            if remaining_work <= 0:  # Construction terminée
                building["progress"] = 0  # Réinitialiser pour permettre d'autres constructions
                building["count"] += 1
                print(f"{self.resource} construit dans {self.city.name} !")

                # Appliquer l'impact du bâtiment
                if self.resource == "granary":
                    self.city.yields["food"] += 1  # +1 au rendement de la nourriture
                elif self.resource == "barracks":
                    self.city.yields["wood"] += 0.5  # +0.5 au rendement du bois

                self.city.reassign_workers(self.workers)
                return True
            else:
                print(f"Construction de {self.resource} dans {self.city.name}: il reste {remaining_work} unités de travail.")
        return False

    def _handle_raid_city(self):
        """
        Gère un raid sur une ville ennemie pour voler des ressources.
        """
        self.remaining_duration -= 1
        if self.remaining_duration == self.remaining_duration // 2:  # Arrivée dans la ville cible
            loot = {}
            for resource, amount in self.target_city.resources.items():
                stolen_amount = min(amount, self.workers)  # Les hommes volent au maximum leur nombre en ressources
                loot[resource] = stolen_amount
                self.target_city.resources[resource] -= stolen_amount
                self.city.resources[resource] += stolen_amount
            print(f"Les hommes de {self.city.name} ont pillé {loot} à {self.target_city.name}.")

        if self.remaining_duration <= 0:  # Retour des hommes
            print(f"Les hommes de {self.city.name} sont revenus du raid sur {self.target_city.name}.")
            self.city.reassign_workers(self.workers)
            return True

        return False


    def _handle_timed_action(self):
        self.remaining_duration -= 1
        if self.remaining_duration <= 0:
            self.city.reassign_workers(self.workers)
            return True
        return False

    def _handle_besiege(self):
        self.remaining_duration -= 1
        travel_time = (self.remaining_duration - 10) // 2  # Temps aller simple

        if self.remaining_duration == 10:
            print(f"Les hommes de {self.city.name} partent pour assiéger {self.target_city.name}.")

        if self.remaining_duration == 10 - travel_time:
            print(f"Les hommes de {self.city.name} arrivent à {self.target_city.name} et commencent le siège.")

        if self.remaining_duration == travel_time:
            print(f"Le siège de {self.target_city.name} par {self.city.name} est terminé. Les hommes repartent.")

        if self.remaining_duration <= 0:
            print(f"Les hommes de {self.city.name} sont revenus après avoir assiégé {self.target_city.name}.")
            self.city.reassign_workers(self.workers)
            return True

        return False


class Agenda:
    def __init__(self):
        self.actions = []
        self.current_turn = 0
        self.cities = []

    def add_city(self, city):
        self.cities.append(city)

    def add_action(self, action):
        """
        Ajoute une action à l'agenda sans la valider immédiatement.
        Les validations (ressources, travailleurs, etc.) seront effectuées au moment où l'action commence.
        """
        if action.start_turn > self.current_turn:
            print(f"Action planifiée pour {action.city.name} : {action.type} à partir du tour {action.start_turn}.")
            self.actions.append(action)
        else:
            print(f"Erreur : L'action pour {action.city.name} doit être planifiée dans le futur.")

    def update(self):
        """
        Met à jour toutes les actions et applique leurs effets.
        Supprime les actions terminées ou impossibles à démarrer.
        """
        self.current_turn += 1
        print(f"--- Tour {self.current_turn} ---")

        completed_actions = []
        for action in self.actions:
            if not action.has_started and self.current_turn >= action.start_turn:
                # Valider les ressources et travailleurs uniquement au moment du démarrage
                if action.type in {"harvest", "raid_city"}:
                    action.has_started = True
                    print(f"L'action {action.type} commence pour {action.city.name}.")
                if action.type == "construction":
                    building = action.city.buildings.get(action.resource)
                    if building and all(action.city.resources[res] >= qty for res, qty in building["cost"].items()):
                        for res, qty in building["cost"].items():
                            action.city.resources[res] -= qty
                        action.has_started = True
                        print(f"{action.city.name} commence la construction de {action.resource}.")
                    else:
                        print(f"Action annulée : Pas assez de ressources dans {action.city.name} pour construire {action.resource}.")
                        completed_actions.append(action)  # Supprimer l'action
                        continue
                elif action.type == "besiege":
                    food_cost = action.calculate_initial_food_cost()
                    if action.city.resources["food"] >= food_cost:
                        action.city.resources["food"] -= food_cost
                        action.has_started = True
                        print(f"{action.city.name} lance un siège sur {action.target_city.name}.")
                    else:
                        print(f"Action annulée : Pas assez de nourriture dans {action.city.name} pour lancer le siège.")
                        completed_actions.append(action)  # Supprimer l'action
                        continue
                elif not action.city.can_allocate_workers(action.workers):
                    print(f"Action annulée : Pas assez d'hommes disponibles dans {action.city.name}.")
                    completed_actions.append(action)  # Supprimer l'action
                    continue

            if action.has_started and action.update():
                completed_actions.append(action)

        # Retirer les actions terminées ou annulées
        for action in completed_actions:
            self.actions.remove(action)



class City:
    def __init__(self, name, population, yields, coordinates):
        self.name = name
        self.total_population = population
        self.available_population = population
        self.allocated_population = 0
        self.yields = yields  # Rendements par ressource
        self.resources = {key: 0 for key in yields.keys()}
        self.resources["food"] = 1000  # Quantité initiale de nourriture
        self.buildings = {
            "granary": {"required_work": 100, "cost": {"wood": 50, "stone": 30}, "progress": 0, "count": 0},
            "barracks": {"required_work": 150, "cost": {"wood": 100, "food": 50}, "progress": 0, "count": 0},
        }
        self.coordinates = coordinates




    def distance_to(self, other_city):
        """
        Calcule la distance entre cette ville et une autre.
        """
        x1, y1 = self.coordinates
        x2, y2 = other_city.coordinates
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def reassign_workers(self, workers):
        self.available_population += workers
        self.allocated_population -= workers

    def can_allocate_workers(self, workers):
        if self.available_population >= workers:
            self.available_population -= workers
            self.allocated_population += workers
            return True
        return False


if __name__ == "__main__":
    city_a = City("City A", 150, {"food": 2, "wood": 1, "stone": 0.5}, (0, 0))
    city_b = City("City B", 150, {"food": 1.5, "wood": 0.8, "stone": 0.3}, (10, 15))

    agenda = Agenda()
    agenda.add_city(city_a)
    agenda.add_city(city_b)

    # Ajouter une construction (granary)
    construction_granary = Action(
        city=city_a,
        type_="construction",
        workers=20,
        resource="granary",
        start_turn=13
    )
    agenda.add_action(construction_granary)

    harvesting = Action(
        city=city_a,
        type_="harvest",
        workers=50,
        resource="granary",
        start_turn=13
    )
    agenda.add_action(construction_granary)

    harvest_action = Action(
        city=city_a,
        type_="harvest",
        workers=30,
        resource="wood",
        start_turn=1
    )
    agenda.add_action(harvest_action)


    harvest_action = Action(
        city=city_a,
        type_="harvest",
        workers=30,
        resource="stone",
        start_turn=1
    )
    agenda.add_action(harvest_action)

    # Ajouter une construction (barracks)
    construction_barracks = Action(
        city=city_b,
        type_="construction",
        workers=30,
        resource="barracks",
        start_turn=2
    )
    agenda.add_action(construction_barracks)

    # Simulation de 15 tours
    for _ in range(15):
        agenda.update()
        print(f"Ressources dans {city_a.name}: {city_a.resources}")
        print(f"Ressources dans {city_b.name}: {city_b.resources}")
        print(f"Population dans {city_a.name}: {city_a.total_population}")
        print(f"Population dans {city_b.name}: {city_b.total_population}")
        print(f"Bâtiments dans {city_a.name}: {city_a.buildings}")
        print(f"Bâtiments dans {city_b.name}: {city_b.buildings}")
        print("---")
