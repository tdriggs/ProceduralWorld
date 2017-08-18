import numpy as np
from pygame import draw, Surface
from scipy.spatial import Voronoi

from config import MAP_SIZE, GRAPH_MAX_POINTS, GRAPH_RELAXATIONS, POINT_RADIUS


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def tuple(self):
        return int(self.x), int(self.y)

    def draw(self, surface, color=(0, 0, 0)):
        draw.circle(surface, color, self.tuple(), POINT_RADIUS)


class Edge:
    def __init__(self, index, start_center, end_center, start_corner, end_corner):
        self.index = index

        self.start_corner = start_corner
        self.end_corner = end_corner
        self.start_center = start_center
        self.end_center = end_center

        self.has_center_edge = True

        self.start_center.edges.add(self)
        self.end_center.edges.add(self)

        self.start_corner.edges.add(self)
        self.end_corner.edges.add(self)

        self.start_center.centers.add(self.end_center)
        self.end_center.centers.add(self.start_center)

        self.start_center.corners.add(self.start_corner)
        self.start_center.corners.add(self.end_corner)

        self.end_center.corners.add(self.start_corner)
        self.end_center.corners.add(self.end_corner)

        self.start_corner.corners.add(self.end_corner)
        self.end_corner.corners.add(self.start_corner)

        self.start_corner.centers.add(self.start_center)
        self.start_corner.centers.add(self.end_center)

        self.end_corner.centers.add(self.start_center)
        self.end_corner.centers.add(self.end_center)

    def delete(self, edge_set):
        self.start_center.edges.remove(self)
        self.end_center.edges.remove(self)
        self.start_corner.edges.remove(self)
        self.end_corner.edges.remove(self)
        edge_set.remove(self)

    def draw_centers_edge(self, surface, color=(255, 0, 0)):
        if self.has_center_edge:
            draw.line(surface, color, self.start_center.location.tuple(), self.end_center.location.tuple(), 1)

    def draw_corners_edge(self, surface, color=(0, 0, 0)):
        draw.line(surface, color, self.start_corner.location.tuple(), self.end_corner.location.tuple(), 1)


class Center:
    def __init__(self, location, index):
        self.location = location
        self.index = index

        self.centers = set()
        self.edges = set()
        self.corners = set()

    def delete(self, center_set):
        for center in self.centers:
            center.centers.remove(self)
        for corner in self.corners:
            corner.centers.remove(self)
        for edge in self.edges:
            edge.has_region_edge = False
        center_set.remove(self)

    def draw(self, surface, color=(0, 0, 0)):
        self.location.draw(surface, color)


class Corner:
    def __init__(self, location, index):
        self.location = location
        self.index = index

        self.out_of_bounds = False
        self.is_border = False

        self.centers = set()
        self.edges = set()
        self.corners = set()

        self.infer_out_of_bounds()

    def infer_out_of_bounds(self):
        if self.location.x < 0 or self.location.y < 0 or self.location.x > MAP_SIZE or self.location.y > MAP_SIZE:
            self.out_of_bounds = True

    def delete(self, corner_set):
        for center in self.centers:
            center.corners.remove(self)
        for corner in self.corners:
            corner.corners.remove(self)
        corner_set.remove(self)

    def draw(self, surface, color=(0, 0, 0)):
        self.location.draw(surface, color)


class Graph:
    def __init__(self):
        self.surface = Surface((MAP_SIZE, MAP_SIZE))
        self.surface.fill((255, 255, 255))

        self.centers = {}
        self.edges = {}
        self.corners = {}

        self.initialize_centers()
        self.draw()

    def initialize_centers(self):
        centers = []
        edges = []
        corners = []

        print('Creating Initial Diagram.')
        voronoi = Voronoi(np.random.rand(GRAPH_MAX_POINTS, 2))
        for i in range(GRAPH_RELAXATIONS):
            print('Performing Relaxation #', i + 1, '.', sep='')
            centroids = []
            for region in voronoi.regions:
                if len(region) > 0:
                    centroids.append((sum([voronoi.vertices[v][0] for v in region]) / len(region),
                                      sum([voronoi.vertices[v][1] for v in region]) / len(region)))
            voronoi = Voronoi(centroids)

        print('Converting to Internal Representation.')
        for point in voronoi.points:
            centers.append(Center(Point(point[0] * MAP_SIZE, point[1] * MAP_SIZE), len(centers)))

        for vertex in voronoi.vertices:
            corners.append(Corner(Point(vertex[0] * MAP_SIZE, vertex[1] * MAP_SIZE), len(corners)))

        for i in range(len(voronoi.ridge_points)):
            if -1 not in voronoi.ridge_points[i] and -1 not in voronoi.ridge_vertices[i]:
                center_start = centers[voronoi.ridge_points[i][0]]
                center_end = centers[voronoi.ridge_points[i][1]]
                corner_start = corners[voronoi.ridge_vertices[i][0]]
                corner_end = corners[voronoi.ridge_vertices[i][1]]
                edges.append(Edge(len(edges), center_start, center_end, corner_start, corner_end))

        centers = set(centers)
        edges = set(edges)
        corners = set(corners)

        print('Removing Out Of Bounds Regions.')
        centers_to_remove = []
        for center in centers:
            out_of_bounds = False
            for corner in center.corners:
                if corner.out_of_bounds:
                    out_of_bounds = True
                    break
            if out_of_bounds or len(center.edges) < 3:
                centers_to_remove.append(center)

        for center in centers_to_remove:
            for corner in center.corners:
                corner.is_border = True
            center.delete(centers)

        print('Removing Out Of Bounds Edges.')
        edges_to_remove = []
        for edge in edges:
            if edge.start_corner.out_of_bounds or edge.end_corner.out_of_bounds or \
                    (edge.start_center not in centers and edge.end_center not in centers):
                edges_to_remove.append(edge)

        for edge in edges_to_remove:
            edge.delete(edges)

        print('Removing Out Of Bounds Corners.')
        corners_to_remove = []
        for corner in corners:
            if corner.out_of_bounds:
                has_in_bounds_region = False
                for center in corner.centers:
                    if center in centers:
                        has_in_bounds_region = True
                        break
                if not has_in_bounds_region:
                    corners_to_remove.append(corner)
            else:
                has_connected_edge = False
                for edge in corner.edges:
                    if edge in edges:
                        has_connected_edge = True
                        break
                if not has_connected_edge:
                    corners_to_remove.append(corner)

        for corner in corners_to_remove:
            corner.delete(corners)

        self.centers = {c.index: c for c in centers}
        self.edges = {e.index: e for e in edges}
        self.corners = {c.index: c for c in corners}

        print('Graph Creation Successful!\n')

    def draw(self):
        for edge in self.edges.values():
            edge.draw_corners_edge(self.surface)
        for center in self.centers.values():
            center.draw(self.surface)
        for corner in self.corners.values():
            corner.draw(self.surface)
