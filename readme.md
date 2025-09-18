按游戏刻来更新.

每一刻需要更新的有:

- 地图:随机产生新的站点
- 已有站点:随机更换站点类型,随机增加乘客
- 车辆状态:行驶或上客落客

---

# 思考:

## 20250913

可以安排一个全局更新机,内置一个定时器,每个车头等在其中注册一条定时计划,然后每个tick更新机检查定时器,将到时间的注册者更新状态
或者,每个状态的定时由车头自己计算,然后每次更新所有车头的状态

感觉第一种会好一点.
可以用**最小堆**,剩余时间最少的在上面.由于等待时间只会按顺序变小(除了调车),
因此可以每次从顶端检查是否到时间.若没有则进入下一个循环,如果有就删除堆顶,安排新的堆顶后再立即检查堆顶是否到时间(
因为有可能和旧堆顶时间相等)

所有可以先不考虑调车,即列车和线路不能更改已安排的部分,只能延长.

## 20250914

列车的状态转移的具体操作可以写在train类,但是判断是否要转移,以及转移前的操作等等,可以写在trainInventory或者gameWorld里.
也就是, *举例*: 在train里做一个setBoarding函数,只把状态改到boarding.然后在(比如)trainInventory里写一个setTrainStatus(
train,status), 里面判断冷却时间等等

另外timeschedule的更新可以放到world的update函数里,每个tick运行一次

应该是,每次在inventory调用改变列车状态的函数时,注册一个新的倒计时

还有,列车在终点站自动掉头,应当是先落客完,然后掉头,再上客.
因此一列车的完整周期是:
*boarding->running->alighting->(boarding->running->alighting)... ->(destination)alighting-> change direction ->boarding->...*
如果有调车,则是*(boarding->)running->**get shunting command**->alighting->shunting->boarding->...like upon*

~~所以换向判断应该写在boarding里面,因为调车和终点站都要操作行驶方向,这俩也都是从boarding开始~~

**不太行,由于换向啥的是在line里面息息相关的,放在line类里面更合适**

可以在line里面用一个字典记录每个列车的方向

## 20250915

调动列车时也可以包括同线路换向这一操作

ALIGHTING   -<  (running)
BOARDING    -<  (alighting,shunting,idle)
RUNNING     -<  (BOARDING)
SHUNTING    -<  (ALIGHTING)
也就是,只有running->alighting/shunting->borading/idle->boarding
这三种情况才需要修改stationNow

## 20250918
在train添加了一个waitshunting的flag，以及targetline，来记录是否处于侯调车状态