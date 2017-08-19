from pygame import display, event, transform, mouse, time, font, draw
import pygame

from gui import Viewport, Button
from Geography import Geography
from config import SCREEN_HEIGHT, SCREEN_WIDTH, MAP_SIZE

display.init()
font.init()
screen = display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = time.Clock()

geo = Geography()
viewport = Viewport(transform.scale(geo.surface, (MAP_SIZE, MAP_SIZE)), (200, 0))

is_creating_landmass = False
land_mass_origin = (0, 0)
is_setting_landmass_distance = False


def finalize(v, g):
    g.finalize()
    g.draw()

    v.update_subject(g.surface)
    v.fit()


def unfinalize(v, g):
    g.unfinalize()
    g.draw()

    v.update_subject(g.surface)
    v.fit()


def create_surface(v, g):
    global is_creating_landmass

    unfinalize(v, g)
    is_creating_landmass = True


def reset_land(v, g):
    g.reset()
    g.draw()

    v.update_subject(g.surface)
    v.fit()

create_landmass_button = Button((0, 0), 'Create Landmass', create_surface, [viewport, geo])
finalize_button = Button((0, 50), 'Finalize Landmass', finalize, [viewport, geo])
unfinalize_button = Button((0, 100), 'Unfinalize Landmass', unfinalize, [viewport, geo])
reset_land_button = Button((0, 150), 'Reset Landmass', reset_land, [viewport, geo])

keys = set()
game_over = False
while not game_over:
    elapsed = clock.tick() / 1000
    events = event.get()
    for curr_event in events:
        if curr_event.type == pygame.QUIT:
            game_over = True
        elif curr_event.type == pygame.KEYDOWN:
            if curr_event.key == pygame.K_ESCAPE:
                if is_setting_landmass_distance or is_creating_landmass:
                    is_setting_landmass_distance = False
                    is_creating_landmass = False
                else:
                    game_over = True
            if curr_event.key == pygame.K_z:
                viewport.zoom(0.5)
            if curr_event.key == pygame.K_x:
                viewport.zoom(2)
            if curr_event.key == pygame.K_SPACE:
                viewport.moving_towards_center = True
            keys.add(curr_event.key)
        elif curr_event.type == pygame.KEYUP:
            keys.remove(curr_event.key)
        elif curr_event.type == pygame.MOUSEBUTTONDOWN:
            if is_creating_landmass:
                if viewport.mouse_in_viewport(mouse.get_pos()):
                    is_creating_landmass = False
                    land_mass_origin = viewport.convert_mouse_pos(mouse.get_pos())
                    is_setting_landmass_distance = True
            elif is_setting_landmass_distance:
                mouse_pos = viewport.convert_mouse_pos(mouse.get_pos())
                is_setting_landmass_distance = False
                distance = ((mouse_pos[0] - land_mass_origin[0]) ** 2 +
                            (mouse_pos[1] - land_mass_origin[1]) ** 2) ** 0.5
                geo.create_land(land_mass_origin, distance)
                geo.draw()
                viewport.update_subject(geo.surface)
                viewport.fit()

    dx = dy = 0
    if pygame.K_LEFT in keys:
        dx = -1
    if pygame.K_RIGHT in keys:
        dx = 1
    if pygame.K_DOWN in keys:
        dy = 1
    if pygame.K_UP in keys:
        dy = -1

    viewport.update(elapsed, dx, dy)
    create_landmass_button.update(elapsed, mouse.get_pos(), any(mouse.get_pressed()))
    finalize_button.update(elapsed, mouse.get_pos(), any(mouse.get_pressed()))
    unfinalize_button.update(elapsed, mouse.get_pos(), any(mouse.get_pressed()))
    reset_land_button.update(elapsed, mouse.get_pos(), any(mouse.get_pressed()))

    screen.fill((0, 0, 0))

    viewport.draw(screen)

    create_landmass_button.draw(screen)
    finalize_button.draw(screen)
    unfinalize_button.draw(screen)
    reset_land_button.draw(screen)

    if is_creating_landmass:
        draw.circle(screen, (255, 0, 0), mouse.get_pos(), 5)
    elif is_setting_landmass_distance:
        converted_origin = viewport.deconvert_mouse_pos(land_mass_origin)
        mouse_pos = mouse.get_pos()
        distance = ((mouse_pos[0] - converted_origin[0]) ** 2 +
                    (mouse_pos[1] - converted_origin[1]) ** 2) ** 0.5
        draw.circle(screen, (255, 0, 0), converted_origin, 5)
        draw.circle(screen, (255, 0, 0), converted_origin, max(5, int(distance)), 2)

    display.flip()

display.quit()
font.quit()
