from enum import Enum

from pygame import Surface, transform, font

from config import BUTTON_BUFFER, BUTTON_WIDTH, BUTTON_HEIGHT, BUTTON_FONT, BUTTON_FONT_SIZE, BUTTON_RESET_TIME, \
    VIEWPORT_MOVING_SPEED, VIEWPORT_MAX_ZOOM, VIEWPORT_SIZE


class ButtonState(Enum):
    ACTIVE = (255, 255, 255)
    HOVER = (255, 0, 0)
    INACTIVE = (0, 0, 150)


class Button:
    def __init__(self, location, text, action, action_args):
        self.location = (location[0] + BUTTON_BUFFER, location[1] + BUTTON_BUFFER)

        self.font = font.SysFont(BUTTON_FONT, BUTTON_FONT_SIZE)
        self.font_surface = self.font.render(text, 1, (0, 0, 0))

        self.state = ButtonState.ACTIVE

        self.action = action
        self.action_args = action_args

        self.reset_timer = 0

        self.surface = Surface((BUTTON_WIDTH - BUTTON_BUFFER * 2, BUTTON_HEIGHT - BUTTON_BUFFER * 2))

    def update(self, elapsed, mouse_pos, mouse_clicked):
        if self.state is not ButtonState.INACTIVE:
            if self.location[0] <= mouse_pos[0] <= self.location[0] + BUTTON_WIDTH and \
                                    self.location[1] <= mouse_pos[1] <= self.location[1] + BUTTON_HEIGHT:
                if mouse_clicked:
                    self.action(*self.action_args)
                    self.state = ButtonState.INACTIVE
                else:
                    self.state = ButtonState.HOVER
            else:
                self.state = ButtonState.ACTIVE
        else:
            self.reset_timer += elapsed
            if self.reset_timer >= BUTTON_RESET_TIME:
                self.reset_timer = 0
                self.state = ButtonState.ACTIVE

    def draw(self, surface):
        self.surface.fill(self.state.value)
        self.surface.blit(self.font_surface, (((BUTTON_WIDTH - self.font_surface.get_width()) / 2) - BUTTON_BUFFER,
                                              ((BUTTON_HEIGHT - self.font_surface.get_height()) / 2) - BUTTON_BUFFER))

        surface.blit(self.surface, self.location)


class Viewport:
    def __init__(self, subject, location):
        self.location = location

        self.subject = subject
        self.draw_subject = self.subject
        self.center = ((self.draw_subject.get_width() - VIEWPORT_SIZE) / 2,
                       (self.draw_subject.get_height() - VIEWPORT_SIZE) / 2)
        self.subject_location = [self.center[0], self.center[1]]
        self.initial_subject_size = (self.draw_subject.get_width(), self.draw_subject.get_height())

        self.moving_towards_center = False
        self.zoom_factor = 1

        self.surface = Surface((VIEWPORT_SIZE, VIEWPORT_SIZE))

        self.fit()

    def move(self, elapsed, dx, dy):
        if dx < 0 < self.subject_location[0] or \
                (dx > 0 and self.draw_subject.get_width() - self.subject_location[0] > VIEWPORT_SIZE):
            self.subject_location[0] += dx * VIEWPORT_MOVING_SPEED * elapsed
        if dy < 0 < self.subject_location[1] or \
                (dy > 0 and self.draw_subject.get_height() - self.subject_location[1] > VIEWPORT_SIZE):
            self.subject_location[1] += dy * VIEWPORT_MOVING_SPEED * elapsed

    def move_towards_center(self, elapsed):
        if self.at_center():
            self.moving_towards_center = False
        else:
            magnitude = ((self.center[0] - self.subject_location[0]) ** 2 +
                         (self.center[1] - self.subject_location[1]) ** 2) ** 0.5
            vector_to_center = ((self.center[0] - self.subject_location[0]) / magnitude,
                                (self.center[1] - self.subject_location[1]) / magnitude)
            self.move(elapsed, vector_to_center[0] * 5, vector_to_center[1] * 5)

    def at_center(self):
        if abs(self.subject_location[0] - self.center[0]) < 5 and abs(self.subject_location[1] - self.center[1]) < 5:
            self.subject_location[0] = self.center[0]
            self.subject_location[1] = self.center[1]
            return True
        return False

    def fit(self, zoom_factor=1):
        self.zoom_factor = zoom_factor
        self.draw_subject = transform.scale(self.subject, (int(VIEWPORT_SIZE * self.zoom_factor),
                                                           int(VIEWPORT_SIZE * self.zoom_factor)))
        self.center = ((self.draw_subject.get_width() - VIEWPORT_SIZE) / 2,
                       (self.draw_subject.get_height() - VIEWPORT_SIZE) / 2)
        self.subject_location[0] = self.center[0]
        self.subject_location[1] = self.center[1]

    def zoom(self, zoom_factor):
        self.fit(max(1, min(self.zoom_factor * zoom_factor, VIEWPORT_MAX_ZOOM)))

    def mouse_in_viewport(self, mouse_pos):
        return self.location[0] <= mouse_pos[0] <= self.location[0] + VIEWPORT_SIZE and \
               self.location[1] <= mouse_pos[1] <= self.location[1] + VIEWPORT_SIZE

    def convert_mouse_pos(self, mouse_pos):
        mouse_pos = (mouse_pos[0] - self.location[0], mouse_pos[1] - self.location[1])
        mouse_pos = (((mouse_pos[0] + self.subject_location[0]) / self.draw_subject.get_width())
                     * self.initial_subject_size[0],
                     ((mouse_pos[1] + self.subject_location[1]) / self.draw_subject.get_height())
                     * self.initial_subject_size[1])

        return mouse_pos

    def deconvert_mouse_pos(self, coordinates):
        x_pos = coordinates[0] / self.initial_subject_size[0]
        x_pos *= self.draw_subject.get_width()
        x_pos -= self.subject_location[0]
        x_pos += self.location[0]

        y_pos = coordinates[1] / self.initial_subject_size[1]
        y_pos *= self.draw_subject.get_height()
        y_pos -= self.subject_location[1]
        y_pos += self.location[1]

        return int(x_pos), int(y_pos)

    def update(self, elapsed, dx, dy):
        self.move(elapsed, dx, dy)

        if self.moving_towards_center:
            self.move_towards_center(elapsed)

    def update_subject(self, updated_subject):
        self.subject = updated_subject
        self.draw_subject = self.subject
        self.center = ((self.draw_subject.get_width() - VIEWPORT_SIZE) / 2,
                       (self.draw_subject.get_height() - VIEWPORT_SIZE) / 2)
        self.subject_location[0] = self.center[0]
        self.subject_location[1] = self.center[1]

    def draw(self, surface):
        self.surface.blit(self.draw_subject, (0, 0), (self.subject_location[0], self.subject_location[1],
                                                      self.surface.get_width(), self.surface.get_height()))
        surface.blit(self.surface, self.location)
