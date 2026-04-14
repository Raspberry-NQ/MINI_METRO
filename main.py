# main.py - 游戏入口

from world import GameWorld

if __name__ == '__main__':
    stationTypeList = {1: "square", 2: "triangle", 3: "circle"}
    print(stationTypeList)

    world = GameWorld()
    world.worldInit(trainNm=1, carriageNm=1, stationNm=2)
    for i in range(1, 20):
        world.updateOneTick()
