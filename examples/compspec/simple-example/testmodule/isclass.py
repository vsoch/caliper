class Car:
    """
    Beep beep I have a motor!
    """

    def __init__(self, wheels=4, doors=4):
        self.wheels = wheels
        self.doors = doors
        self.speed = 0

    def honk(self):
        print("Honk honk!")

    def slow_down(self, speed: int):
        self.speed -= speed
        self.speed = max(self.speed, 0)

    def accelerate(self, speed):
        self.speed += speed
