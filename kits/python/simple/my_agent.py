import math, sys
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

DIRECTIONS = Constants.DIRECTIONS
game_state = None


# this snippet finds all resources stored on the map and puts them into a list so we can search over them
def find_resources(game_state):
    resource_tiles: list[Cell] = []
    width, height = game_state.map_width, game_state.map_height
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
    return resource_tiles


# the next snippet finds the closest resources that we can mine given position on a map
def find_closest_resources(pos, player, resource_tiles):
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        # we skip over resources that we can't mine due to not having researched them
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
        if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
        dist = resource_tile.pos.distance_to(pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile
    return closest_resource_tile


def city_has_enough_fuel(player):
    for city in player.cities.values():
        burn = 23 - 5 * len(city.citytiles)
        if city.fuel <= burn * 10:
            return False
    return True


def is_empty(cell):
    if cell.citytile is not None: # already city
        return False
    if cell.resource is not None:
        return False
    return True


def get_next_cells(game_map, pos):
    width, height = game_state.map.width, game_state.map.height
    cells = []
    deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for d in deltas:
        x = pos.x + d[0]
        y = pos.y + d[1]
        if x <= 0 or width < x:
            continue
        if y <= 0 or height < y:
            continue
        cell = game_map.get_cell(x, y)
        cells.append(cell)
    return cells


def is_city_candidate(game_map, pos):
    width, height = game_state.map.width, game_state.map.height
    cell = game_map.get_cell_by_pos(pos)
    if not is_empty(cell):
        return False
    deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for d in deltas:
        x = pos.x + d[0]
        y = pos.y + d[1]
        if x <= 0 or width < x:
            continue
        if y <= 0 or height < y:
            continue
        cell = game_map.get_cell(x, y)
        if cell.citytile is not None: # the cell is next to city
            return True
    return False

# snippet to find the closest city tile to a position
def find_closest_city_tile(pos, player):
    closest_city_tile = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
    return closest_city_tile


def find_closest_city_candidate(game_map, pos, player):
    closest_pos = None
    if len(player.cities) > 0:
        closest_dist = math.inf
        # the cities are stored as a dictionary mapping city id to the city object, which has a citytiles field that
        # contains the information of all citytiles in that city
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                cell = game_map.get_cell_by_pos(city_tile.pos)
                cells = get_next_cells(game_map, cell.pos)
                
                for cell in cells:
                    if not is_empty(cell):
                        continue
                    dist = cell.pos.distance_to(pos)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_pos = cell.pos
    return closest_pos


def calc_citytile_burn_fuel(game_map, cell):
    cells = get_next_cells(game_map, cell.pos)
    num_adjacent_cities = 0
    for cell in cells:
        if cell.citytile is not None:
            num_adjacent_cities += 1
    return 23 - 5 * num_adjacent_cities


def calc_city_burn_fuel(game_map, cities):
    tile_info = {}
    for city in cities:
        total_burn_fuel = 0
        for tile in city.citytiles:
            cell = game_map.get_cell_by_pos(tile.pos)
            burn_fuel = calc_citytile_burn_fuel(game_map, cell)
            total_burn_fuel += burn_fuel
        print (city.fuel, total_burn_fuel)
        may_be_burn_out = city.fuel <= total_burn_fuel * 10
        tile_info[(tile.pos.x, tile.pos.y)] = (burn_fuel, may_be_burn_out)
    return tile_info

def agent(observation, configuration):
    global game_state

    
    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []

    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height
    game_map = game_state.map


    # get resource_tiles
    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)

    # count units
    num_workers = sum([unit.is_worker() for unit in player.units])
    num_carts = sum([unit.is_cart() for unit in player.units])

    num_cititiles = sum([len(city.citytiles) for city in player.cities.values()])
    cititiles = []
    for city in player.cities.values():
        for tile in city.citytiles:
            cititiles.append(tile)
            # city has enough fuel
            if tile.can_act():
                if num_cititiles > len(player.units):
                    if num_workers / 5 <= num_carts:
                        action = tile.build_worker()
                    else:
                        action = tile.build_cart()
                else:
                    action = tile.research()
                actions.append(action)

    tile_info = calc_city_burn_fuel(game_map, player.cities.values())
    enough_fuel = True
    burn_out_city_pos = None
    for tile_pos, (burn_fuel, burn_out) in tile_info.items():
        if burn_out:
            enough_fuel = False
            burn_out_city_pos = tile_pos
            break
    

    # we iterate over all our units and do something with them
    for unit in player.units:
        if unit.is_worker() and unit.can_act():
            if unit.get_cargo_space_left() > 0:
                closest_resource_tile = find_closest_resources(unit.pos, player, resource_tiles)
                if closest_resource_tile is not None:
                    action = unit.move(unit.pos.direction_to(closest_resource_tile.pos))
                    actions.append(action)
            else:
                action = None
                if enough_fuel:
                    if unit.can_build(game_map):
                        action = unit.build_city()
                    else: # move to freespace next to city
                        pos = find_closest_city_candidate(game_map, unit.pos, player)
                        
                        if pos is not None:
                            action = unit.move(unit.pos.direction_to(pos))
                            actions.append(annotate.circle(pos.x, pos.y))

                if action is None:
                    if burn_out_city_pos is not None:
                        action = unit.move(unit.pos.direction_to(Position(burn_out_city_pos[0], burn_out_city_pos[1])))
                    # resource drop to closest city
                    else:
                        closest_city_tile = find_closest_city_tile(unit.pos, player)
                        if closest_city_tile is not None:
                            action = unit.move(unit.pos.direction_to(closest_city_tile.pos))
                
                if action is not None:
                    actions.append(action)
            print (actions)

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    return actions
