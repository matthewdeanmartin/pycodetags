"""
A simple terminal-based fish tank "game" with ASCII art.
Includes various TODO,  FIXME tags demonstrating Folk and PEP-350 styles,
and now also @TODO decorators from the code_tags library.
"""

import os
import random
import time

# --- Import Actual Code Tag System ---
# Assuming code_tags library is available in the environment
from pycodetags import DOCUMENT  # Added for a decorator example
from pycodetags import ALERT, BUG, FIXME, HACK, TODO, TodoException

# Constants
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 24
FRAME_RATE = 0.1  # seconds per frame

# Character sets
FISH_CHARS = ["<><", "><>", ")-<", ">-(", "=^..^="]
PLANT_CHARS = ["Y", "|", "!", "/", "\\"]
WAVE_CHARS = ["~", "-", "_", "^"]


@TODO(
    assignee="Alice",
    due="09/15/2025",
    release_due="2.0.0",
    category="Fish Movement",
    status="Development",
    tracker="https://example.com/FSH-20",
    comment="Refactor Fish class for better extensibility and maintainability.",
)
class Fish:
    # DONE: Basic fish movement implemented. <Carl closed_date=2024-06-19 release=1.0.0>
    def __init__(self, x: int, y: int, char: str, speed: int = 1):
        self.x = x
        self.y = y
        self.char = char
        self.speed = speed
        self.dx = random.choice([-1, 1])  # Initial horizontal direction
        self.dy = 0  # Fish mostly move horizontally, vertical movement will be slight

        # TODO: Add fish health and hunger stats. <Kstar>
        # TODO: Implement fish personality (e.g., aggressive, timid). <Kstar category=Flavor Text status=Planning iteration=1 tracker=https://example.com/FSH-5>

    @HACK(assignee="Bob", due="07/30/2025", comment="Simplified bounce logic, consider more realistic physics.")
    def move(self, screen_width: int, screen_height: int):
        """
        Updates the fish's position.
        FIXME: Fish can get stuck at the edges. <Bob due=07/15/2025 release_due=1.5.0 category='Fish Movement' status=Development tracker=https://example.com/FSH-6>
        """
        self.x += self.dx * self.speed

        # Simple bounce off walls
        if self.x <= 0 or self.x >= screen_width - len(self.char):
            self.dx *= -1
            # Flip character if it's a directional one
            if self.char == "<><":
                self.char = "><>"
            elif self.char == "><>":
                self.char = "<><"
            elif self.char == ")-<":
                self.char = ">-("
            elif self.char == ">-(":
                self.char = ")-<"

        # Slight vertical drift
        if random.random() < 0.1:  # 10% chance to change vertical direction
            self.dy = random.choice([-1, 0, 1])

        self.y += self.dy
        # Keep fish within the "water" area (below waves, above plants)
        self.y = max(2, min(self.y, screen_height - 3))  # Avoid waves and very bottom

    @BUG(
        assignee="Alice",
        due="08/01/2025",
        comment="Chase algorithm causes fish to get stuck on edges. This needs a significant fix.",
        category="Chase Algorithm",
        status="Testing",
        tracker="https://example.com/FSH-7",
    )
    def chase(self, target_fish: "Fish", screen_width: int, screen_height: int):
        """
        Logic for chasing another fish.
        FIXME: Chase algorithm causes fish to get stuck on edges. <Alice due=08/01/2025 category=Chase Algorithm status=Testing tracker=https://example.com/FSH-7>
        """
        # TODO: Improve chase logic to avoid obstacles (plants). <Bob due=09/01/2025 release_due=2.0.0 category=Chase Algorithm status=Development iteration=3 tracker=https://example.com/FSH-8>
        if target_fish:
            if target_fish.x < self.x:
                self.dx = -1
                if self.char == "<><":
                    self.char = "><>"
                elif self.char == ")-<":
                    self.char = ">-("
            elif target_fish.x > self.x:
                self.dx = 1
                if self.char == "><>":
                    self.char = "<><"
                elif self.char == ">-(":
                    self.char = ")-<"

            if target_fish.y < self.y:
                self.y -= self.speed
            elif target_fish.y > self.y:
                self.y += self.speed
        self.move(screen_width, screen_height)  # Apply movement based on chase or bounce


@TODO(
    assignee="Carl",
    due="10/01/2025",
    release_due="2.0.0",
    category="Plant Generator",
    status="Planning",
    comment="Enhance Plant class to support different types and interactions.",
)
class Plant:
    def __init__(self, x: int, y: int, char: str):
        self.x = x
        self.y = y
        self.char = char
        # TODO: Implement plant growth over time. <Carl>

    @DOCUMENT(
        originator="Kstar",
        comment="Add detailed documentation for Plant.update and explain why NotImplementedError is raised.",
    )
    def update(self):
        """
        Updates the plant's state (e.g., growth animation).
        """
        # NOT IMPLEMENTED: Plant animation logic for swaying or growing.
        raise NotImplementedError(
            "Plant animation is not yet implemented. This feature will add dynamic plant swaying."
        )


@TODO(
    assignee="Kstar",
    due="08/15/2025",
    release_due="1.5.0",
    category="Wave Generator",
    status="Development",
    comment="Make wave generation more realistic and less static.",
)
class Wave:
    # DONE: Static wave character setup completed. <Bob due=05/01/2024 release=1.0.0 category=Wave Generator>
    def __init__(self, width: int, char_set: list[str]):
        self.width = width
        self.char_set = char_set
        self.wave_pattern_index = 0
        self.wave_pattern = ""
        self._generate_pattern()

    @TODO(
        originator="Bob",
        comment="Refine wave pattern generation for more organic look.",
        category="Wave Generator",
        status="Planning",
        iteration="2",
    )
    def _generate_pattern(self):
        """Generates a random wave pattern."""
        self.wave_pattern = "".join(random.choice(self.char_set) for _ in range(self.width))

    @FIXME(
        assignee="Carl",
        tracker="https://example.com/FSH-4",
        comment="Wave animation is choppy, needs smoother transitions.",
    )
    @TODO(
        assignee="Kstar",
        tracker="https://example.com/FSH-3",
        comment="Make wave pattern more dynamic and fluid (e.g., gentle oscillation).",
    )
    def update(self):
        """
        Updates the wave pattern for animation.
        TODO: Make wave pattern more dynamic and fluid (e.g., gentle oscillation). <Kstar tracker=https://example.com/FSH-3>
        FIXME: Wave animation is choppy, needs smoother transitions. <Carl tracker=https://example.com/FSH-4>
        """
        # Simple scrolling wave animation
        self.wave_pattern_index = (self.wave_pattern_index + 1) % len(self.wave_pattern)
        self.wave_pattern = self.wave_pattern[1:] + self.wave_pattern[0]


@TODO(
    assignee="Alice",
    due="09/01/2025",
    iteration="3",
    release_due="2.0.0",
    category="Flavor Text",
    status="Planning",
    comment="Add dynamic environment elements like bubbles, currents, and lighting effects.",
)
class FishTank:
    def __init__(self, width: int, height: int, num_fish: int = 5, num_plants: int = 3):
        self.width = width
        self.height = height
        self.screen_buffer = [[" " for _ in range(width)] for _ in range(height)]
        self.fishes: list[Fish] = []
        self.plants: list[Plant] = []
        self.wave = Wave(width, WAVE_CHARS)

        # TODO: Initial screen setup and sizing for responsiveness. <Alice originator=Alice tracker=https://example.com/FSH-1>
        # DONE: Basic screen buffer initialization completed. <Alice due=06/15/2024 release=1.0.0 category=Flavor Text status=Done tracker=https://example.com/FSH-2>

        self._initialize_elements(num_fish, num_plants)

    @TODO(
        assignee="Carl",
        category="Fish Movement",
        status="Planning",
        iteration="1",
        comment="Consider different fish types with unique behaviors, beyond just character.",
    )
    def _initialize_elements(self, num_fish: int, num_plants: int):
        """
        Initializes fish and plant objects.
        TODO: Consider different fish types with unique behaviors. <Carl category='Fish Movement' status=Planning iteration=1>
        """
        for _ in range(num_fish):
            x = random.randint(5, self.width - 5)
            y = random.randint(3, self.height - 4)  # Avoid wave and bottom plant line
            char = random.choice(FISH_CHARS)
            self.fishes.append(Fish(x, y, char))

        for _ in range(num_plants):
            x = random.randint(5, self.width - 5)
            y = self.height - 1  # Place plants at the very bottom
            char = random.choice(PLANT_CHARS)
            self.plants.append(Plant(x, y, char))

    @BUG(
        status="NOBUG",
        originator="Kstar",
        closed_date="2024-06-20",
        release="1.5.0",
        comment="Screen clearing works sufficiently for a terminal app.",
    )
    def _clear_screen(self):
        """Clears the terminal screen."""
        os.system("cls" if os.name == "nt" else "clear")

    @TODO(
        assignee="Bob",
        due="07/01/2025",
        release_due="1.5.0",
        category="Flavor Text",
        status="Planning",
        iteration="1",
        tracker="https://example.com/FSH-10",
        comment="Add background details and rocks at the bottom.",
    )
    @TODO(
        assignee="Alice",
        release_due="2.0.0",
        iteration="2",
        category="Fish Movement",
        status="Planning",
        tracker="https://example.com/FSH-11",
        comment="Implement a 'hero' fish that the player controls.",
    )
    @TODO(
        assignee="Bob",
        category="Flavor Text",
        status="Development",
        comment="Display debug information (e.g., FPS, fish count).",
    )
    @FIXME(
        originator="Bob",
        tracker="https://example.com/FSH-9",
        comment="Screen flickering due to re-drawing. Needs optimization (e.g., diff rendering).",
    )
    def render(self):
        """
        Renders the current state of the tank to the terminal.
        FIXME: Screen flickering due to re-drawing. Needs optimization (e.g., diff rendering). <Bob originator=Bob tracker=https://example.com/FSH-9>
        """
        self._clear_screen()
        self.screen_buffer = [[" " for _ in range(self.width)] for _ in range(self.height)]

        # Draw waves
        self._draw_element(0, 0, self.wave.wave_pattern)
        self._draw_element(0, 1, self.wave.wave_pattern)  # Second row of waves for thickness

        # Draw plants (at the very bottom)
        for plant in self.plants:
            self._draw_element(plant.x, plant.y, plant.char)

        # Draw fish
        for fish in self.fishes:
            self._draw_element(fish.x, fish.y, fish.char)

        # TODO: Add background details and rocks at the bottom. <Bob due=07/01/2025 category='Flavor Text' status=Planning iteration=1 release_due=1.5.0 tracker=https://example.com/FSH-10>
        # TODO: Implement a "hero" fish that the player controls. <Alice category='Fish Movement' status=Planning release_due=2.0.0 iteration=2 tracker=https://example.com/FSH-11>

        # Print the buffer
        for row in self.screen_buffer:
            print("".join(row))

        # TODO: Display debug information (e.g., FPS, fish count). <Bob category=Flavor Text status=Development>

    @TODO(
        assignee="Alice",
        iteration="2",
        release_due="1.5.0",
        category="Fish Movement",
        status="Development",
        tracker="https://example.com/FSH-13",
        comment="Implement collision detection for fish and tank walls.",
    )
    @TODO(
        assignee="Carl",
        category="Flavor Text",
        status="Planning",
        iteration="2",
        tracker="https://example.com/FSH-14",
        comment="Add food pellets for fish to eat.",
    )
    def update(self):
        """
        Updates the positions and states of all elements in the tank.
        """
        self.wave.update()

        # Update fish movement, potentially chasing others
        for i, fish in enumerate(self.fishes):
            # Simple chase logic: each fish chases a random other fish
            if len(self.fishes) > 1 and random.random() < 0.3:  # 30% chance to chase
                target_fish = random.choice([f for j, f in enumerate(self.fishes) if j != i])
                fish.chase(target_fish, self.width, self.height)
            else:
                fish.move(self.width, self.height)

        # Try to update plants, but it will raise NotImplementedError
        for plant in self.plants:
            try:
                plant.update()
            except NotImplementedError:
                # WONTFIX: Plant animation is not critical for MVP. <Kstar tracker=https://example.com/FSH-12>
                # Log or handle the fact that plant animation is not implemented.
                pass

        # TODO: Implement collision detection for fish and tank walls. <Alice iteration=2 release_due=1.5.0 category='Fish Movement' status=Development tracker=https://example.com/FSH-13>
        # TODO: Add food pellets for fish to eat. <Carl category=Flavor Text status=Planning iteration=2 tracker=https://example.com/FSH-14>

    @TODO(
        assignee="Alice",
        due="10/01/2025",
        tracker="https://example.com/FSH-15",
        comment="Implement fish spawning logic to replenish tank population.",
    )
    def _spawn_new_fish_if_needed(self):
        """
        This function would handle spawning new fish based on certain conditions.
        """
        # TODO: Implement fish spawning logic. <Alice assignee=Alice due=10/01/2025 tracker=https://example.com/FSH-15>
        # This feature is not implemented yet.
        raise TodoException("Fish spawning logic is a future enhancement. Assignee: Alice, Due: 10/01/2025")

    @ALERT(
        assignee="Bob",
        due="07/15/2025",
        comment="User input is critical for interactivity, needs immediate implementation.",
    )
    def _handle_user_input(self):
        """
        NOT IMPLEMENTED: Handle keyboard input for interacting with the tank.
        """
        raise NotImplementedError("User input handling for the fish tank is not implemented.")


@TODO(
    status="Done", originator="Bob", closed_date="2024-06-20", comment="Hero screen display implemented and functional."
)
def hero_screen():
    # DONE: Hero screen display implemented. <Bob originator=Bob>
    """Displays the hero/start screen."""
    hero_text = [
        "################################################################################",
        "################################################################################",
        "##                                                                            ##",
        "##                        WELCOME TO THE ASCII FISH TANK                      ##",
        "##                                                                            ##",
        "##                            Press ENTER to Start                            ##",
        "##                                                                            ##",
        "##                           Press 'q' to Quit Early                          ##",
        "##                                                                            ##",
        "################################################################################",
        "################################################################################",
    ]
    for _ in range((SCREEN_HEIGHT - len(hero_text)) // 2):
        print()
    for line in hero_text:
        print(line.center(SCREEN_WIDTH))
    for _ in range((SCREEN_HEIGHT - len(hero_text)) // 2):
        print()

    input()  # Wait for user to press Enter


@TODO(
    assignee="Alice",
    iteration="3",
    status="Planning",
    release_due="2.0.0",
    tracker="https://example.com/FSH-16",
    comment="Add proper game over screen and restart option for enhanced gameplay loop.",
)
def main():
    tank = FishTank(SCREEN_WIDTH, SCREEN_HEIGHT)

    # TODO: Add proper game over screen and restart option. <Alice iteration=3 status=Planning release_due=2.0.0 tracker=https://example.com/FSH-16>
    hero_screen()

    running = True
    try:
        while running:
            # Example of how a TodoException could be triggered and handled if the feature was attempted
            # try:
            #     tank._spawn_new_fish_if_needed()
            # except TodoException as e:
            #     print(f"\n[INFO] {e.message}")
            #     # In a real game, this might be handled more gracefully, or simply not called yet.

            tank.update()
            tank.render()
            time.sleep(FRAME_RATE)

            # Check for immediate quit (requires non-blocking input, which is complex in standard Python terminal)
            # This is a placeholder for demonstration. In a real game, you'd use libraries like curses or keyboard.
            # print("Press 'q' to quit...", end='\r')
            # For simplicity, we just run until interrupted or a specific condition.

    except KeyboardInterrupt:
        print("\nExiting Fish Tank. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        # NOBUG: Ensure terminal state is reset correctly on exit. <Kstar release=1.5.0 closed_date=2024-06-20>
        # WONTFIX: Add complex terminal cleanup for all OS types. <Carl tracker=https://example.com/FSH-17>
        pass


if __name__ == "__main__":
    main()
