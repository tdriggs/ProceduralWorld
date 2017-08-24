from enum import Enum

import numpy as np
from pygame import Surface, draw, font
from scipy.spatial import ConvexHull, qhull
from opensimplex import OpenSimplex

from Graph import Graph
from config import SEED, MAP_SIZE, LAND_PERLIN_WEIGHT, LAND_RADIAL_WEIGHT, LAND_THRESHOLD, \
    LAND_CORNER_FACTOR, RANDOM_LAKE_FACTOR, LAND_MASS_CULL_SIZE, STARTING_LAND, STARTING_LAND_POS, STARTING_LAND_SIZE, \
    DRAW_REGION_OUTLINE, DRAW_CORNERS, REGION_OUTLINE_WIDTH, DRAW_DISTANCE_FROM_OCEAN_CORNERS, \
    DRAW_DISTANCE_FROM_OCEAN_REGIONS, DRAW_DISTANCE_FROM_WATER_CORNERS, DRAW_DISTANCE_FROM_WATER_REGIONS, \
    DRAW_REGIONS_ELEVATION, DRAW_REGIONS_NORMAL, DRAW_REGIONS_OCEAN_DISTANCE, DRAW_REGIONS_WATER_DISTANCE, \
    DRAW_REGIONS_ELEVATION_COLORED, DRAW_ELEVATION_ON_REGIONS, ELEVATION_OCEAN_WEIGHT, ELEVATION_PERLIN_WEIGHT


class GeographyType(Enum):
    NOT_SET = (255, 255, 255)
    BORDER = (255, 0, 0)
    OCEAN = (50, 50, 150)
    WATER = (50, 50, 255)
    LAND = (75, 150, 75)
    COAST = (230, 220, 200)
    MOUNTAIN = (255, 0, 0)


class Corner:
    def __init__(self, location, index):
        self.location = location
        self.index = index

        self.landmass = None

        self.noise_factor = (OpenSimplex(seed=SEED).noise2d(x=self.location.x, y=self.location.y) + 1) / 2

        self.neighbors = set()
        self.regions = set()

        self.type = GeographyType.WATER

        self.elevation = 1

        self.steps_from_ocean = 0
        self.nearest_ocean_neighbor = None
        self.steps_from_water = 0
        self.nearest_water_neighbor = None

        self.font = font.SysFont('ariel', 40)

    def infer_land(self):
        if self.type is not GeographyType.BORDER:
            for region in self.regions:
                if region.type in (GeographyType.LAND, GeographyType.COAST):
                    self.type = GeographyType.LAND
                    return True
        return False

    def draw(self, surface):
        if DRAW_CORNERS:
            self.location.draw(surface, color=self.type.value)

        if DRAW_DISTANCE_FROM_OCEAN_CORNERS and \
                self.type in (GeographyType.LAND, GeographyType.COAST, GeographyType.WATER):
            font_surface = self.font.render(str(self.steps_from_ocean), 1, (0, 255, 0))
            surface.blit(font_surface, (self.location.x - int(font_surface.get_width() / 2),
                         self.location.y - int(font_surface.get_height() / 2)))
        elif DRAW_DISTANCE_FROM_WATER_CORNERS and \
                self.type in (GeographyType.LAND, GeographyType.COAST, GeographyType.WATER):
            font_surface = self.font.render(str(self.steps_from_water), 1, (0, 255, 0))
            surface.blit(font_surface, (self.location.x - int(font_surface.get_width() / 2),
                         self.location.y - int(font_surface.get_height() / 2)))


class Region:
    def __init__(self, location, index):
        self.location = location
        self.index = index

        self.landmass = None

        self.hull = []
        self.corners = set()
        self.neighbors = set()

        self.type = GeographyType.WATER

        self.elevation = 1

        self.steps_from_ocean = 0
        self.nearest_ocean_neighbor = None
        self.steps_from_water = 0
        self.nearest_water_neighbor = None

        self.font = font.SysFont('ariel', 60)

    def make_hull(self):
        corner_list = list(self.corners)

        if len(corner_list) >= 3:
            try:
                convex_hull = [v for v in ConvexHull([c.location.tuple() for c in corner_list]).vertices]
            except qhull.QhullError:
                raise Exception('Regions are too close together, cannot create convex hull to draw polygon. ' +
                                'Lower the number of initial points entered into the Graph object.')
        else:
            return False

        self.hull = [corner_list[i].location.tuple() for i in convex_hull]

        return True

    def infer_land(self):
        if self.type is not GeographyType.LAND:
            number_water_corners = 0
            for corner in self.corners:
                if corner.type in (GeographyType.WATER, GeographyType.OCEAN) or \
                                np.random.uniform(0, 1) < RANDOM_LAKE_FACTOR:
                    number_water_corners += 1
            if number_water_corners / len(self.corners) < LAND_CORNER_FACTOR:
                self.type = GeographyType.LAND
                return True
            else:
                for corner in self.corners:
                    if corner.type is not GeographyType.BORDER:
                        corner.type = GeographyType.WATER
        return False

    def infer_ocean(self):
        if self.type is GeographyType.WATER:
            for region in self.neighbors:
                if region.type is GeographyType.OCEAN:
                    self.type = GeographyType.OCEAN
                    for corner in self.corners:
                        if corner.type is GeographyType.WATER:
                            corner.type = GeographyType.OCEAN
                        elif corner.type is GeographyType.LAND:
                            corner.type = GeographyType.COAST
                    return True
            else:
                for corner in self.corners:
                    if corner.type is GeographyType.BORDER:
                        self.type = GeographyType.OCEAN
                        return True
        return False

    def infer_coast(self):
        if self.type is GeographyType.LAND:
            for corner in self.corners:
                if corner.type is GeographyType.COAST:
                    self.type = GeographyType.COAST
                    return True
        return False

    def infer_elevation(self):
        for corner in self.corners:
            self.elevation += corner.elevation

        self.elevation /= int(len(self.corners))

    def draw(self, surface):
        if DRAW_REGIONS_NORMAL:
            draw.polygon(surface, self.type.value, self.hull, 0)
        elif DRAW_REGIONS_ELEVATION:
            draw.polygon(surface, (max(0, min(255, int(self.elevation * 255))),
                                   max(0, min(255, int(self.elevation * 255))),
                                   max(0, min(255, int(self.elevation * 255)))), self.hull, 0)
        elif DRAW_REGIONS_ELEVATION_COLORED:
            draw.polygon(surface, (max(0, min(255, int((self.type.value[0] * self.elevation)))),
                                   max(0, min(255, int((self.type.value[1] * self.elevation)))),
                                   max(0, min(255, int((self.type.value[2] * self.elevation))))), self.hull, 0)
        elif DRAW_REGIONS_OCEAN_DISTANCE:
            draw.polygon(surface, (max(0, min(255, self.steps_from_ocean * 20)),
                                   max(0, min(255, self.steps_from_ocean * 20)),
                                   max(0, min(255, self.steps_from_ocean * 20))), self.hull, 0)
        elif DRAW_REGIONS_WATER_DISTANCE:
            draw.polygon(surface, (max(0, min(255, self.steps_from_water * 20)),
                                   max(0, min(255, self.steps_from_water * 20)),
                                   max(0, min(255, self.steps_from_water * 20))), self.hull, 0)

        if DRAW_REGION_OUTLINE:
            draw.polygon(surface, (0, 0, 0), self.hull, REGION_OUTLINE_WIDTH)

        if DRAW_ELEVATION_ON_REGIONS and \
                self.type in (GeographyType.LAND, GeographyType.COAST, GeographyType.WATER):
            font_surface = self.font.render(str(int(self.elevation * 1000)), 1, (255, 0, 0))
            surface.blit(font_surface, (self.location.x - int(font_surface.get_width() / 2),
                         self.location.y - int(font_surface.get_height() / 2)))
        elif DRAW_DISTANCE_FROM_OCEAN_REGIONS and \
                self.type in (GeographyType.LAND, GeographyType.COAST, GeographyType.WATER):
            font_surface = self.font.render(str(self.steps_from_ocean), 1, (255, 0, 0))
            surface.blit(font_surface, (self.location.x - int(font_surface.get_width() / 2),
                         self.location.y - int(font_surface.get_height() / 2)))
        elif DRAW_DISTANCE_FROM_WATER_REGIONS and \
                self.type in (GeographyType.LAND, GeographyType.COAST, GeographyType.WATER):
            font_surface = self.font.render(str(self.steps_from_water), 1, (255, 0, 0))
            surface.blit(font_surface, (self.location.x - int(font_surface.get_width() / 2),
                                        self.location.y - int(font_surface.get_height() / 2)))


class LandMass:
    def __init__(self, starting_region):
        self.regions = set()
        self.corners = set()

        self.regions.add(starting_region)

        self.size = 0
        self.max_region_steps_from_ocean = 0
        self.max_region_steps_from_water = 0
        self.max_corner_steps_from_ocean = 0
        self.max_corner_steps_from_water = 0

        self.surrounding_type = GeographyType.OCEAN

        self.build()

    def build(self):
        has_regions_left = True
        while has_regions_left:
            has_regions_left = False
            regions_to_add = set()
            for region in self.regions:
                for neighbor in region.neighbors:
                    if neighbor not in self.regions:
                        if neighbor.type in (GeographyType.WATER, GeographyType.LAND, GeographyType.COAST):
                            regions_to_add.add(neighbor)
                            has_regions_left = True
                        else:
                            self.surrounding_type = neighbor.type
            for region in regions_to_add:
                self.regions.add(region)
                region.landmass = self

        for region in self.regions:
            for corner in region.corners:
                self.corners.add(corner)
                corner.landmass = self

        self.size = len(self.regions)
        self.max_region_steps_from_ocean = max([r.steps_from_ocean for r in self.regions])
        self.max_region_steps_from_water = max([r.steps_from_water for r in self.regions])
        self.max_corner_steps_from_ocean = max([c.steps_from_ocean for c in self.corners])
        self.max_corner_steps_from_water = max([c.steps_from_water for c in self.corners])

    def sink(self):
        for region in self.regions:
            region.type = self.surrounding_type
            region.landmass = None
        for corner in self.corners:
            if corner.type is not GeographyType.BORDER:
                corner.type = self.surrounding_type
            corner.landmass = None

    def dissolve(self):
        for region in self.regions:
            region.landmass = None
        for corner in self.corners:
            corner.landmass = None

    def draw(self, surface):
        for corner in self.corners:
            corner.draw(surface)
        for region in self.regions:
            region.draw(surface)


class Geography:
    def __init__(self):
        np.random.seed(SEED)

        self.regions = {}
        self.corners = {}
        self.land_masses = set()

        self.surface = Surface((MAP_SIZE, MAP_SIZE))

        self.initialize()
        if STARTING_LAND:
            self.create_land(STARTING_LAND_POS, STARTING_LAND_SIZE)
        self.draw()

    def reset(self):
        print('Resetting Land Masses.\n')
        while len(self.land_masses) > 0:
            self.land_masses.pop().dissolve()

        for corner in self.corners.values():
            if corner.type is not GeographyType.BORDER:
                corner.type = GeographyType.WATER
        for region in self.regions.values():
            region.type = GeographyType.WATER

        self.unfinalize()

    def finalize(self):
        print('Finalizing Valid Landmasses.\n')
        self.create_oceans()
        self.find_nearest_ocean()
        self.find_nearest_water()
        self.create_land_masses()
        # self.create_mountain_range()
        self.set_elevation()

    def unfinalize(self):
        print('Reverting Finalization.\n')
        for region in self.regions.values():
            if region.type is GeographyType.COAST:
                region.type = GeographyType.LAND
            if region.type is GeographyType.OCEAN:
                region.type = GeographyType.WATER
            region.elevation = 1
            region.steps_from_ocean = 0
            region.steps_from_water = 0

        for corner in self.corners.values():
            if corner.type is GeographyType.COAST:
                corner.type = GeographyType.LAND
            if corner.type is GeographyType.OCEAN:
                corner.type = GeographyType.WATER
            corner.elevation = 1
            corner.steps_from_ocean = 0
            corner.steps_from_water = 0

        while len(self.land_masses) > 0:
            self.land_masses.pop().dissolve()

    def initialize(self):
        graph = Graph()

        print('Converting Graph To Geographical Representation.')
        for i in graph.corners:
            self.corners[i] = Corner(graph.corners[i].location, i)
            if graph.corners[i].is_border:
                self.corners[i].type = GeographyType.BORDER

        for i in graph.centers:
            self.regions[i] = Region(graph.centers[i].location, i)

        for i in graph.corners:
            for c in graph.corners[i].corners:
                self.corners[i].neighbors.add(self.corners[c.index])
            for c in graph.corners[i].centers:
                self.corners[i].regions.add(self.regions[c.index])

        for i in graph.centers:
            for c in graph.centers[i].corners:
                self.regions[i].corners.add(self.corners[c.index])
            for c in graph.centers[i].centers:
                self.regions[i].neighbors.add(self.regions[c.index])

        for i in self.regions:
            self.regions[i].make_hull()

        print('Converted!\n')

    def create_land(self, origin, max_distance):
        corners_to_update = set()
        regions_to_update = set()

        print('Assigning Land Corners.')
        for corner in self.corners.values():
            distance_from_origin = int(((corner.location.x - origin[0]) ** 2 +
                                        (corner.location.y - origin[1]) ** 2) ** 0.5)

            if distance_from_origin < max_distance and corner.type is not GeographyType.BORDER:
                land_factor = ((corner.noise_factor * LAND_PERLIN_WEIGHT) +
                               (1 - (distance_from_origin / max_distance) * LAND_RADIAL_WEIGHT))

                if land_factor > LAND_THRESHOLD:
                    corner.type = GeographyType.LAND

                corners_to_update.add(corner)

        for corner in corners_to_update:
            for region in corner.regions:
                regions_to_update.add(region)

        print('Inferring Land Regions.')
        for region in regions_to_update:
            region.infer_land()

        print('Inferring Land Corners.\n')
        for corner in corners_to_update:
            corner.infer_land()

    def create_oceans(self):
        print('Inferring Ocean Regions.')
        has_regions_left = True
        while has_regions_left:
            has_regions_left = False
            for region in self.regions.values():
                if region.infer_ocean():
                    has_regions_left = True

        print('Inferring Coast Regions.')
        for region in self.regions.values():
            region.infer_coast()

        print('Geography Created!\n')

    def create_land_masses(self):
        print('Grouping Land Masses.')
        for region in self.regions.values():
            if region.type in (GeographyType.LAND, GeographyType.COAST, GeographyType.WATER):
                for land_mass in self.land_masses:
                    if region in land_mass.regions:
                        break
                else:
                    self.land_masses.add(LandMass(region))

        print('Removing Small Land Masses.')
        land_masses_to_sink = set()
        for land_mass in self.land_masses:
            if land_mass.size <= LAND_MASS_CULL_SIZE:
                land_masses_to_sink.add(land_mass)

        for land_mass in land_masses_to_sink:
            land_mass.sink()
            self.land_masses.remove(land_mass)

        print('Land Masses Cleaned Up!\n')

    def find_nearest_ocean(self):
        print('Finding distance to ocean for regions.')
        regions_to_check = set()
        for region in self.regions.values():
            if region.type is GeographyType.COAST:
                regions_to_check.add(region)

        steps = 1

        while len(regions_to_check) > 0:
            new_regions_to_check = set()
            for region in regions_to_check:
                if region.steps_from_ocean == 0:
                    region.steps_from_ocean = steps
                    for neighbor in region.neighbors:
                        if neighbor.type in (GeographyType.LAND, GeographyType.WATER):
                            new_regions_to_check.add(neighbor)

            regions_to_check = new_regions_to_check
            steps += 1

        print('Finding distance to ocean for corners.')
        corners_to_check = set()
        for corner in self.corners.values():
            if corner.type is GeographyType.COAST:
                corners_to_check.add(corner)

        steps = 1

        while len(corners_to_check) > 0:
            new_corners_to_check = set()
            for corner in corners_to_check:
                if corner.steps_from_ocean == 0:
                    corner.steps_from_ocean = steps
                    for neighbor in corner.neighbors:
                        if neighbor.type in (GeographyType.LAND, GeographyType.WATER):
                            new_corners_to_check.add(neighbor)

            corners_to_check = new_corners_to_check
            steps += 1

    def find_nearest_water(self):
        print('Finding distance to water for regions.')
        regions_to_check = set()
        for region in self.regions.values():
            if region.type is GeographyType.COAST:
                regions_to_check.add(region)
            elif region.type is GeographyType.WATER:
                for neighbor in region.neighbors:
                    if neighbor.type is not GeographyType.WATER:
                        regions_to_check.add(neighbor)

        steps = 1

        while len(regions_to_check) > 0:
            new_regions_to_check = set()
            for region in regions_to_check:
                if region.steps_from_water == 0:
                    region.steps_from_water = steps
                    for neighbor in region.neighbors:
                        if neighbor.type is GeographyType.LAND:
                            new_regions_to_check.add(neighbor)

            regions_to_check = new_regions_to_check
            steps += 1

        print('Finding distance to water for corners.')
        corners_to_check = set()
        for corner in self.corners.values():
            if corner.type is GeographyType.COAST:
                corners_to_check.add(corner)
            elif corner.type is GeographyType.LAND:
                for region in corner.regions:
                    if region.type is GeographyType.WATER:
                        corners_to_check.add(corner)
                        break

        steps = 1

        while len(corners_to_check) > 0:
            new_corners_to_check = set()
            for corner in corners_to_check:
                if corner.steps_from_water == 0:
                    corner.steps_from_water = steps
                    for neighbor in corner.neighbors:
                        if neighbor.type is GeographyType.LAND:
                            new_corners_to_check.add(neighbor)

            corners_to_check = new_corners_to_check
            steps += 1

    def create_mountain_range(self):
        largest_landmass = max(self.land_masses, key=lambda l: l.size)
        iterator = iter(largest_landmass.corners)
        range_start = next(iterator)
        range_end = next(iterator)
        i = 0
        done = False
        while not done:
            range_end = next(iterator)
            i += 1

            if range_end.type is GeographyType.LAND and i > 10:
                done = True

        print(range_start.type, range_end.type)

        range_start.type = GeographyType.MOUNTAIN
        range_end.type = GeographyType.MOUNTAIN

        path = [range_start]
        indices_visited = set()
        indices_visited.add(range_start.index)

        done = False
        while not done:
            distances = {}
            for neighbor in path[-1].neighbors:
                if neighbor.index not in indices_visited:
                    distance = int((neighbor.location.x - range_end.location.x) ** 2 +
                                   (neighbor.location.y - range_end.location.y) ** 2)
                    distances[distance] = neighbor
                    indices_visited.add(neighbor.index)

            if len(distances) == 0:
                path.remove(path[-1])
            else:
                curr_node = distances[min(distances.keys())]
                if curr_node == range_end:
                    done = True
                else:
                    curr_node.type = GeographyType.MOUNTAIN
                    path.append(curr_node)

    def set_elevation(self):
        for corner in self.corners.values():
            if corner.type in (GeographyType.OCEAN, GeographyType.BORDER):
                corner.elevation = 0.2
            else:
                corner.elevation = ((corner.noise_factor * ELEVATION_PERLIN_WEIGHT) +
                                    ((corner.steps_from_ocean / corner.landmass.max_corner_steps_from_ocean) *
                                     ELEVATION_OCEAN_WEIGHT)) / 2

        for region in self.regions.values():
            region.infer_elevation()

    def draw(self):
        print('Drawing.\n')
        self.surface.fill((0, 0, 0))
        for region in self.regions.values():
            region.draw(self.surface)
        for corner in self.corners.values():
            corner.draw(self.surface)
