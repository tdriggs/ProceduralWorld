from enum import Enum

import numpy as np
from pygame import Surface, draw
from scipy.spatial import ConvexHull, qhull
from opensimplex import OpenSimplex

from Graph import Graph
from config import SEED, MAP_SIZE, LAND_PERLIN_WEIGHT, LAND_RADIAL_WEIGHT, LAND_THRESHOLD, \
    LAND_CORNER_FACTOR, RANDOM_LAKE_FACTOR, LAND_MASS_CULL_SIZE, STARTING_LAND, STARTING_LAND_POS, STARTING_LAND_SIZE, \
    DRAW_REGION_OUTLINE, DRAW_CORNERS, REGION_OUTLINE_WIDTH


class GeographyType(Enum):
    NOT_SET = (255, 255, 255)
    BORDER = (255, 0, 0)
    OCEAN = (50, 50, 150)
    WATER = (50, 50, 255)
    LAND = (75, 150, 75)
    COAST = (230, 220, 200)


class Corner:
    def __init__(self, location, index):
        self.location = location
        self.index = index

        self.landmass = None

        self.noise_factor = (OpenSimplex(seed=SEED).noise2d(x=self.location.x, y=self.location.y) + 1) / 2

        self.neighbors = set()
        self.regions = set()

        self.type = GeographyType.WATER

        self.elevation = 0

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


class Region:
    def __init__(self, location, index):
        self.location = location
        self.index = index

        self.landmass = None

        self.hull = []
        self.corners = set()
        self.neighbors = set()

        self.type = GeographyType.WATER

        self.elevation = 0

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
        draw.polygon(surface, self.type.value, self.hull, 0)
        # draw.polygon(surface, (max(0, min(255, self.type.value[0] + self.elevation)),
        #                        max(0, min(255, self.type.value[1] + self.elevation)),
        #                        max(0, min(255, self.type.value[2] + self.elevation))), self.hull, 0)
        # draw.polygon(surface, (self.elevation, self.elevation, self.elevation), self.hull, 0)
        if DRAW_REGION_OUTLINE:
            draw.polygon(surface, (0, 0, 0), self.hull, REGION_OUTLINE_WIDTH)


class LandMass:
    def __init__(self, starting_region):
        self.regions = set()
        self.corners = set()

        self.starting_region = starting_region

        self.regions.add(self.starting_region)

        self.size = 0
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
                        if neighbor.type in (GeographyType.LAND, GeographyType.COAST):
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

    def sink(self):
        for region in self.regions:
            region.type = self.surrounding_type
            region.landmass = None
        for corner in self.corners:
            if corner.type is not GeographyType.BORDER:
                corner.type = self.surrounding_type
            corner.landmass = None


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
            self.land_masses.pop().sink()

    def finalize(self):
        print('Finalizing Valid Landmasses.\n')
        self.create_oceans()
        self.create_land_masses()
        # self.set_elevation()

    def unfinalize(self):
        print('Reverting Finalization.\n')
        for region in self.regions.values():
            if region.type is GeographyType.COAST:
                region.type = GeographyType.LAND
            if region.type is GeographyType.OCEAN:
                region.type = GeographyType.WATER
            region.elevation = 0

        for corner in self.corners.values():
            if corner.type is GeographyType.COAST:
                corner.type = GeographyType.LAND
            if corner.type is GeographyType.OCEAN:
                corner.type = GeographyType.WATER
            corner.elevation = 0

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

    def set_elevation(self):
        for corner in self.corners.values():
            if corner.type in (GeographyType.OCEAN, GeographyType.BORDER):
                corner.elevation = 50
            else:
                distance_from_center = int(((corner.location.x - corner.landmass.starting_region.location.x) ** 2 +
                                            (corner.location.y - corner.landmass.starting_region.location.y) ** 2) **
                                           0.5)
                distance_factor = 1 - (distance_from_center / 5000)

                corner.elevation = int(min(255.0, ((corner.noise_factor * LAND_PERLIN_WEIGHT) +
                                                   (distance_factor * LAND_RADIAL_WEIGHT)) * 128))

        for region in self.regions.values():
            region.infer_elevation()

    def draw(self):
        print('Drawing.\n')
        for region in self.regions.values():
            region.draw(self.surface)
        for corner in self.corners.values():
            corner.draw(self.surface)
